from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_image import __version__
from agent_image.adapters.base import ExportedImage
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.manifest import LAYER_KINDS, PORTABILITY_CLASSES, PRIVACY_CLASSES, load_yaml, validate_manifest
from agent_image.paths import validate_archive_path
from agent_image.scanner import secret_filename_reason, structured_secret_findings


INVENTORY_VERSION = "agent-image-inventory/v0.1"
# MOCK_POINT {"id":"MOCK-CORE-FIXTURE-ADAPTER-001","type":"test_fixture","target":"Production Hermes, OpenClaw, DSH, and vHarness adapters implementing AgentImageAdapter","replace_by":"before any production adapter capability claim","owner":"core-adapters","status":"accepted_test_only","production_allowed":false,"reason":"Core archive and privacy gates need a deterministic explicit inventory without reading a real user home."}


def _required_object(parent: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise AgentImageError("E_SPEC_INVALID", f"{path}/{key} must be an object.")
    return value


def _required_string(parent: dict[str, Any], key: str, path: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value:
        raise AgentImageError("E_SPEC_INVALID", f"{path}/{key} must be a non-empty string.")
    return value


def _load_inventory(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"Fixture source directory does not exist: {root}")
    inventory = load_yaml(root / "inventory.yaml")
    if inventory.get("api_version") != INVENTORY_VERSION:
        raise AgentImageError("E_SPEC_INVALID", f"Fixture inventory must declare {INVENTORY_VERSION}.")
    if not isinstance(inventory.get("items"), list):
        raise AgentImageError("E_SPEC_INVALID", "Fixture inventory /items must be an array.")
    _required_object(inventory, "adapter", "")
    _required_object(inventory, "source_harness", "")
    _required_object(inventory, "image", "")
    return inventory


def inspect_fixture(root: Path) -> dict[str, Any]:
    inventory = _load_inventory(root)
    return {
        "adapter": inventory["adapter"],
        "source_harness": inventory["source_harness"],
        "image": inventory["image"],
        "items": inventory["items"],
        "capabilities": {
            "archive": True,
            "native_restore": False,
            "semantic_migration": False,
            "test_only": True,
        },
    }


def export_fixture(root: Path, policy: str) -> ExportedImage:
    if policy not in {"private", "public"}:
        raise AgentImageError("E_SPEC_INVALID", f"Unsupported export policy: {policy}")
    inventory = _load_inventory(root)
    root_real = root.resolve()
    payloads: dict[str, bytes] = {}
    layers: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()

    for index, raw_item in enumerate(inventory["items"]):
        if not isinstance(raw_item, dict):
            raise AgentImageError("E_SPEC_INVALID", f"Inventory item {index} must be an object.")
        item_id = _required_string(raw_item, "id", f"/items/{index}")
        source_name = _required_string(raw_item, "source", f"/items/{index}")
        target = validate_archive_path(_required_string(raw_item, "path", f"/items/{index}"))
        kind = _required_string(raw_item, "kind", f"/items/{index}")
        media_type = _required_string(raw_item, "media_type", f"/items/{index}")
        privacy = _required_string(raw_item, "privacy", f"/items/{index}")
        portability = _required_string(raw_item, "portability", f"/items/{index}")
        if item_id in seen_ids or target in seen_paths:
            raise AgentImageError("E_SPEC_INVALID", f"Duplicate inventory id or target at item {index}.")
        seen_ids.add(item_id)
        seen_paths.add(target)
        if kind not in LAYER_KINDS or not target.startswith(f"layers/{kind}/"):
            raise AgentImageError("E_SPEC_INVALID", f"Inventory item {item_id} has an invalid kind/path mapping.")
        if privacy not in PRIVACY_CLASSES or portability not in PORTABILITY_CLASSES:
            raise AgentImageError("E_SPEC_INVALID", f"Inventory item {item_id} has invalid classification metadata.")

        source_relative = validate_archive_path(source_name)
        source_path = root / Path(*source_relative.split("/"))
        try:
            source_real = source_path.resolve(strict=True)
            source_real.relative_to(root_real)
        except (OSError, ValueError) as error:
            raise AgentImageError("E_UNSAFE_PATH", f"Fixture source escapes or is missing: {source_name}") from error
        if source_path.is_symlink() or not source_real.is_file():
            raise AgentImageError("E_UNSAFE_PATH", f"Fixture source must be a regular non-symlink file: {source_name}")
        data = source_real.read_bytes()

        filename_reason = secret_filename_reason(source_name) or secret_filename_reason(target)
        key_findings = structured_secret_findings(source_name, media_type, data)
        if privacy == "secret" or filename_reason or key_findings:
            raise AgentImageError(
                "E_SECRET_DETECTED",
                f"Secret material detected in inventory item {item_id}.",
                details={"filename": filename_reason, "structured_keys": key_findings},
            )

        include = policy == "private" or privacy == "public"
        if not include:
            outcomes.append({"id": item_id, "source": source_relative, "action": "redacted", "reason": f"{privacy} item excluded by public policy"})
            continue
        payloads[target] = data
        layer = {
            "id": item_id,
            "kind": kind,
            "media_type": media_type,
            "path": target,
            "digest": sha256_bytes(data),
            "size": len(data),
            "privacy": privacy,
            "portability": portability,
            "source": {"path": source_relative, "reason": "explicit fixture inventory"},
        }
        layers.append(layer)
        outcomes.append({"id": item_id, "source": source_relative, "action": "preserved", "reason": "explicit fixture inventory"})

    layers.sort(key=lambda item: item["path"])
    adapter = inventory["adapter"]
    harness = inventory["source_harness"]
    image = dict(inventory["image"])
    image["digest"] = layer_root_digest(layers)
    runtime = {
        "harness": {
            "id": _required_string(harness, "id", "/source_harness"),
            "version": _required_string(harness, "version", "/source_harness"),
        },
        "adapter": {
            "id": _required_string(adapter, "id", "/adapter"),
            "version": _required_string(adapter, "version", "/adapter"),
        },
    }
    if "runtime" in inventory:
        supplied_runtime = inventory["runtime"]
        if not isinstance(supplied_runtime, dict):
            raise AgentImageError("E_SPEC_INVALID", "/runtime must be an object.")
        runtime.update(supplied_runtime)
    manifest: dict[str, Any] = {
        "spec": "agent-image/v0.1",
        "image": image,
        "runtime": runtime,
        "layers": layers,
        "privacy": {
            "default": "private",
            "public_build": policy == "public",
            "unresolved_items": sum(1 for layer in layers if layer["privacy"] == "unknown"),
        },
        "provenance": {
            "source_harness": runtime["harness"]["id"],
            "source_adapter": runtime["adapter"]["id"],
            "export_tool_version": __version__,
        },
    }
    for optional in ("development", "evaluations", "lineage"):
        if optional in inventory:
            manifest[optional] = inventory[optional]
    validate_manifest(manifest)
    report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "build",
        "adapter": runtime["adapter"],
        "inventory_count": len(inventory["items"]),
        "outcomes": outcomes,
    }
    return ExportedImage(manifest=manifest, payloads=payloads, source_report=report)


def layer_root_digest(layers: list[dict[str, Any]]) -> str:
    content = [
        {
            "path": layer["path"],
            "digest": layer["digest"],
            "size": layer["size"],
            "media_type": layer["media_type"],
        }
        for layer in sorted(layers, key=lambda item: item["path"])
    ]
    return sha256_bytes(canonical_json_bytes(content))
