from __future__ import annotations

import copy
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from agent_image.adapters.fixture import export_fixture, inspect_fixture, layer_root_digest
from agent_image.canonical import pretty_json_bytes, sha256_bytes
from agent_image.container import pack_entries, read_entries
from agent_image.errors import AgentImageError
from agent_image.manifest import dump_yaml, load_yaml_bytes, validate_manifest
from agent_image.paths import validate_archive_path
from agent_image.scanner import secret_filename_reason, structured_secret_findings


REQUIRED_CONTROL_PATHS = {
    "manifest.yaml",
    "index.json",
    "meta/checksums.txt",
    "meta/source-report.json",
}
OPTIONAL_CONTROL_PATHS = {
    "meta/redaction-report.json",
    "meta/migration-report.json",
}
OUTCOMES = {"preserved", "transformed", "redacted", "unsupported", "dropped_by_user"}


def _index_for(layers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "spec": "agent-image-index/v0.1",
        "entries": [
            {
                "path": layer["path"],
                "digest": layer["digest"],
                "size": layer["size"],
                "media_type": layer["media_type"],
            }
            for layer in sorted(layers, key=lambda item: item["path"])
        ],
    }


def _checksums(entries: Mapping[str, bytes]) -> bytes:
    lines = [f"{sha256_bytes(entries[path])[7:]}  {path}" for path in sorted(entries)]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _image_entries(
    manifest: dict[str, Any],
    payloads: Mapping[str, bytes],
    source_report: dict[str, Any],
    *,
    redaction_report: dict[str, Any] | None = None,
    migration_report: dict[str, Any] | None = None,
) -> dict[str, bytes]:
    entries = dict(payloads)
    entries["manifest.yaml"] = dump_yaml(manifest)
    entries["index.json"] = pretty_json_bytes(_index_for(manifest["layers"]))
    entries["meta/source-report.json"] = pretty_json_bytes(source_report)
    if redaction_report is not None:
        entries["meta/redaction-report.json"] = pretty_json_bytes(redaction_report)
    if migration_report is not None:
        entries["meta/migration-report.json"] = pretty_json_bytes(migration_report)
    entries["meta/checksums.txt"] = _checksums(entries)
    return entries


def _publish(entries: Mapping[str, bytes], output: Path) -> None:
    if output.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".agent-image-", dir=output.parent) as temporary:
        candidate = Path(temporary) / "candidate.aimg"
        pack_entries(entries, candidate)
        verify_image(candidate)
        try:
            os.replace(candidate, output)
        except OSError as error:
            raise AgentImageError("E_IMAGE_CORRUPT", f"Could not publish image atomically: {error}") from error


def plan_fixture_build(source: Path, *, policy: str) -> dict[str, Any]:
    plan = inspect_fixture(source)
    outcomes = []
    for item in plan["items"]:
        privacy = item.get("privacy", "unknown")
        action = "preserved" if policy == "private" or privacy == "public" else "redacted"
        outcomes.append({"id": item.get("id", "unknown"), "privacy": privacy, "action": action})
    return {
        "operation": "build-plan",
        "adapter": plan["adapter"],
        "source_harness": plan["source_harness"],
        "policy": policy,
        "outcomes": outcomes,
        "requires_confirmation": True,
    }


def build_fixture_image(source: Path, output: Path, *, policy: str = "private") -> dict[str, Any]:
    exported = export_fixture(source, policy)
    entries = _image_entries(exported.manifest, exported.payloads, exported.source_report)
    _publish(entries, output)
    return {
        "operation": "build",
        "output": str(output.resolve()),
        "image_digest": exported.manifest["image"]["digest"],
        "layers": len(exported.manifest["layers"]),
        "verified": True,
    }


def _load_json_entry(entries: Mapping[str, bytes], path: str) -> Any:
    try:
        return json.loads(entries[path].decode("utf-8", errors="strict"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid JSON control file {path}: {error}") from error


def _validate_operation_report(report: Any, path: str) -> None:
    if not isinstance(report, dict) or report.get("report_version") != "agent-image-operation-report/v0.1":
        raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid operation report: {path}")
    outcomes = report.get("outcomes")
    count = report.get("inventory_count", report.get("input_count"))
    if not isinstance(outcomes, list) or not isinstance(count, int) or count != len(outcomes):
        raise AgentImageError("E_IMAGE_CORRUPT", f"Operation report cannot reconcile item count: {path}")
    ids: set[str] = set()
    for outcome in outcomes:
        if not isinstance(outcome, dict) or outcome.get("action") not in OUTCOMES:
            raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid outcome in operation report: {path}")
        item_id = outcome.get("id")
        if not isinstance(item_id, str) or not item_id or item_id in ids:
            raise AgentImageError("E_IMAGE_CORRUPT", f"Duplicate or invalid outcome id in {path}")
        ids.add(item_id)


def _validate_checksums(entries: Mapping[str, bytes]) -> None:
    try:
        lines = entries["meta/checksums.txt"].decode("utf-8", errors="strict").splitlines()
    except (KeyError, UnicodeDecodeError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid checksum file: {error}") from error
    declared: dict[str, str] = {}
    for line in lines:
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(character not in "0123456789abcdef" for character in parts[0]):
            raise AgentImageError("E_IMAGE_CORRUPT", "Malformed checksum line.")
        path = validate_archive_path(parts[1])
        if path in declared:
            raise AgentImageError("E_IMAGE_CORRUPT", f"Duplicate checksum path: {path}")
        declared[path] = parts[0]
    expected_paths = set(entries) - {"meta/checksums.txt"}
    if set(declared) != expected_paths:
        raise AgentImageError("E_IMAGE_CORRUPT", "Checksum inventory does not match archive entries.")
    for path, expected in declared.items():
        actual = sha256_bytes(entries[path])[7:]
        if actual != expected:
            raise AgentImageError("E_DIGEST_MISMATCH", f"Checksum mismatch for {path}.")


def verify_image(image: Path) -> dict[str, Any]:
    entries = read_entries(image)
    missing_control = sorted(REQUIRED_CONTROL_PATHS - set(entries))
    if missing_control:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Missing control files: {', '.join(missing_control)}")
    manifest = load_yaml_bytes(entries["manifest.yaml"])
    validate_manifest(manifest)
    layer_paths = {layer["path"] for layer in manifest["layers"]}
    allowed = REQUIRED_CONTROL_PATHS | OPTIONAL_CONTROL_PATHS | layer_paths
    undeclared = sorted(set(entries) - allowed)
    missing_layers = sorted(layer_paths - set(entries))
    if undeclared:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Undeclared archive payloads: {', '.join(undeclared)}")
    if missing_layers:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Missing declared payloads: {', '.join(missing_layers)}")
    _validate_checksums(entries)

    actual_index = _load_json_entry(entries, "index.json")
    if actual_index != _index_for(manifest["layers"]):
        raise AgentImageError("E_IMAGE_CORRUPT", "index.json does not match the manifest.")

    for layer in manifest["layers"]:
        data = entries[layer["path"]]
        if len(data) != layer["size"] or sha256_bytes(data) != layer["digest"]:
            raise AgentImageError("E_DIGEST_MISMATCH", f"Layer digest or size mismatch: {layer['path']}")
        filename_reason = secret_filename_reason(layer["path"])
        key_findings = structured_secret_findings(layer["path"], layer["media_type"], data)
        if layer["privacy"] == "secret" or filename_reason or key_findings:
            raise AgentImageError(
                "E_SECRET_DETECTED",
                f"Secret material detected in layer {layer['id']}.",
                details={"filename": filename_reason, "structured_keys": key_findings},
            )
    expected_root = layer_root_digest(manifest["layers"])
    if manifest["image"]["digest"] != expected_root:
        raise AgentImageError("E_DIGEST_MISMATCH", "Image content digest does not match layer descriptors.")
    unknown_count = sum(1 for layer in manifest["layers"] if layer["privacy"] == "unknown")
    if manifest["privacy"]["unresolved_items"] != unknown_count:
        raise AgentImageError("E_IMAGE_CORRUPT", "Privacy unresolved_items does not match unknown layers.")
    if manifest["privacy"]["public_build"] and any(layer["privacy"] != "public" for layer in manifest["layers"]):
        raise AgentImageError("E_IMAGE_CORRUPT", "Public image contains a non-public layer.")

    _validate_operation_report(_load_json_entry(entries, "meta/source-report.json"), "meta/source-report.json")
    for optional_report in ("meta/redaction-report.json", "meta/migration-report.json"):
        if optional_report in entries:
            _validate_operation_report(_load_json_entry(entries, optional_report), optional_report)
    return {
        "valid": True,
        "spec": manifest["spec"],
        "image_digest": expected_root,
        "layers": len(manifest["layers"]),
    }


def inspect_image(image: Path) -> dict[str, Any]:
    verification = verify_image(image)
    entries = read_entries(image)
    manifest = load_yaml_bytes(entries["manifest.yaml"])
    kinds: Counter[str] = Counter()
    privacy: dict[str, dict[str, int]] = {}
    for layer in manifest["layers"]:
        kinds[layer["kind"]] += 1
        bucket = privacy.setdefault(layer["privacy"], {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += layer["size"]
    layer_inventory = [
        {
            key: layer[key]
            for key in ("id", "kind", "media_type", "path", "digest", "size", "privacy", "portability")
        }
        for layer in manifest["layers"]
    ]
    return {
        "spec": manifest["spec"],
        "image": manifest["image"],
        "runtime": manifest.get("runtime"),
        "layers": {
            "total": len(manifest["layers"]),
            "by_kind": dict(sorted(kinds.items())),
            "items": layer_inventory,
        },
        "privacy": {"policy": manifest["privacy"], "summary": dict(sorted(privacy.items()))},
        "development": manifest.get("development"),
        "lineage": manifest.get("lineage"),
        "verification": verification,
    }


def redact_image(source: Path, output: Path, *, policy: str = "public") -> dict[str, Any]:
    if policy != "public":
        raise AgentImageError("E_SPEC_INVALID", "v0.1 redact supports only --policy public.")
    verify_image(source)
    source_entries = read_entries(source)
    manifest = copy.deepcopy(load_yaml_bytes(source_entries["manifest.yaml"]))
    source_layers = manifest["layers"]
    kept_layers = [layer for layer in source_layers if layer["privacy"] == "public"]
    outcomes = []
    for layer in source_layers:
        action = "preserved" if layer["privacy"] == "public" else "redacted"
        outcomes.append({"id": layer["id"], "action": action, "reason": f"public policy for {layer['privacy']} layer"})
    manifest["layers"] = kept_layers
    manifest["image"]["digest"] = layer_root_digest(kept_layers)
    manifest["privacy"] = {"default": "private", "public_build": True, "unresolved_items": 0}
    payloads = {layer["path"]: source_entries[layer["path"]] for layer in kept_layers}
    source_report = _load_json_entry(source_entries, "meta/source-report.json")
    report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "redact",
        "policy": "public",
        "input_count": len(source_layers),
        "outcomes": outcomes,
        "removed": [layer["id"] for layer in source_layers if layer["privacy"] != "public"],
        "transformed": [],
        "unresolved": [],
    }
    entries = _image_entries(manifest, payloads, source_report, redaction_report=report)
    _publish(entries, output)
    return {"operation": "redact", "output": str(output.resolve()), "removed": report["removed"], "verified": True}


def _privacy_summary(manifest: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for layer in manifest["layers"]:
        bucket = summary.setdefault(layer["privacy"], {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += layer["size"]
    return dict(sorted(summary.items()))


def diff_images(before: Path, after: Path) -> dict[str, Any]:
    verify_image(before)
    verify_image(after)
    before_manifest = load_yaml_bytes(read_entries(before)["manifest.yaml"])
    after_manifest = load_yaml_bytes(read_entries(after)["manifest.yaml"])
    left = {layer["id"]: layer for layer in before_manifest["layers"]}
    right = {layer["id"]: layer for layer in after_manifest["layers"]}
    added = sorted(set(right) - set(left))
    removed = sorted(set(left) - set(right))
    modified = sorted(item_id for item_id in set(left) & set(right) if left[item_id] != right[item_id])
    metadata = {
        "runtime_changed": before_manifest.get("runtime") != after_manifest.get("runtime"),
        "development_changed": before_manifest.get("development") != after_manifest.get("development"),
        "evaluations_changed": before_manifest.get("evaluations") != after_manifest.get("evaluations"),
        "lineage_changed": before_manifest.get("lineage") != after_manifest.get("lineage"),
    }
    privacy = {"before": _privacy_summary(before_manifest), "after": _privacy_summary(after_manifest)}
    empty = not (added or removed or modified or any(metadata.values()) or privacy["before"] != privacy["after"])
    return {
        "empty": empty,
        "layers": {"added": added, "removed": removed, "modified": modified},
        "metadata": metadata,
        "privacy": privacy,
    }
