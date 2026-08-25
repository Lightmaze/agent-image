from __future__ import annotations

import copy
import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from agent_image.adapter_contract import AdapterExport
from agent_image.canonical import canonical_json_bytes, pretty_json_bytes, sha256_bytes
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


@dataclass(frozen=True)
class ImageDocument:
    path: Path
    manifest: dict[str, Any]
    entries: dict[str, bytes]

    def json_entry(self, path: str) -> Any:
        try:
            return json.loads(self.entries[path].decode("utf-8", errors="strict"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid JSON control file {path}: {error}") from error


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


def _operation_report(report: Any, path: str) -> None:
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


def _entries_for(
    export: AdapterExport,
    *,
    redaction_report: dict[str, Any] | None = None,
) -> dict[str, bytes]:
    entries = dict(export.payloads)
    entries["manifest.yaml"] = dump_yaml(export.manifest)
    entries["index.json"] = pretty_json_bytes(_index_for(export.manifest["layers"]))
    entries["meta/source-report.json"] = pretty_json_bytes(export.source_report)
    if redaction_report is not None:
        entries["meta/redaction-report.json"] = pretty_json_bytes(redaction_report)
    entries["meta/checksums.txt"] = _checksums(entries)
    return entries


def publish_image(export: AdapterExport, output: Path) -> None:
    if output.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = _entries_for(export)
    with tempfile.TemporaryDirectory(prefix=".agent-image-formal-", dir=output.parent) as temporary:
        candidate = Path(temporary) / "candidate.aimg"
        pack_entries(entries, candidate)
        verify_image(candidate)
        try:
            os.replace(candidate, output)
        except OSError as error:
            raise AgentImageError("E_IMAGE_CORRUPT", f"Could not publish image atomically: {error}") from error


def _validate_checksums(entries: Mapping[str, bytes]) -> None:
    try:
        lines = entries["meta/checksums.txt"].decode("utf-8", errors="strict").splitlines()
    except (KeyError, UnicodeDecodeError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid checksum file: {error}") from error
    declared: dict[str, str] = {}
    for line in lines:
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(char not in "0123456789abcdef" for char in parts[0]):
            raise AgentImageError("E_IMAGE_CORRUPT", "Malformed checksum line.")
        path = validate_archive_path(parts[1])
        if path in declared:
            raise AgentImageError("E_IMAGE_CORRUPT", f"Duplicate checksum path: {path}")
        declared[path] = parts[0]
    expected = set(entries) - {"meta/checksums.txt"}
    if set(declared) != expected:
        raise AgentImageError("E_IMAGE_CORRUPT", "Checksum inventory does not match archive entries.")
    for path, digest in declared.items():
        if sha256_bytes(entries[path])[7:] != digest:
            raise AgentImageError("E_DIGEST_MISMATCH", f"Checksum mismatch for {path}.")


def load_image(image: Path) -> ImageDocument:
    verify_image(image)
    entries = read_entries(image)
    return ImageDocument(path=image, manifest=load_yaml_bytes(entries["manifest.yaml"]), entries=entries)


def verify_image(image: Path) -> dict[str, Any]:
    entries = read_entries(image)
    missing = sorted(REQUIRED_CONTROL_PATHS - set(entries))
    if missing:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Missing control files: {', '.join(missing)}")
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
    try:
        index = json.loads(entries["index.json"].decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid index.json: {error}") from error
    if index != _index_for(manifest["layers"]):
        raise AgentImageError("E_IMAGE_CORRUPT", "index.json does not match the manifest.")
    for layer in manifest["layers"]:
        data = entries[layer["path"]]
        if len(data) != layer["size"] or sha256_bytes(data) != layer["digest"]:
            raise AgentImageError("E_DIGEST_MISMATCH", f"Layer digest or size mismatch: {layer['path']}")
        reason = secret_filename_reason(layer["path"])
        keys = structured_secret_findings(layer["path"], layer["media_type"], data)
        if layer["privacy"] == "secret" or reason or keys:
            raise AgentImageError(
                "E_SECRET_DETECTED",
                f"Secret material detected in layer {layer['id']}.",
                details={"filename": reason, "structured_keys": keys},
            )
    root = layer_root_digest(manifest["layers"])
    if manifest["image"]["digest"] != root:
        raise AgentImageError("E_DIGEST_MISMATCH", "Image content digest does not match layer descriptors.")
    unknown = sum(1 for layer in manifest["layers"] if layer["privacy"] == "unknown")
    if manifest["privacy"]["unresolved_items"] != unknown:
        raise AgentImageError("E_IMAGE_CORRUPT", "Privacy unresolved_items does not match unknown layers.")
    if manifest["privacy"]["public_build"] and any(layer["privacy"] != "public" for layer in manifest["layers"]):
        raise AgentImageError("E_IMAGE_CORRUPT", "Public image contains a non-public layer.")
    for report_path in ("meta/source-report.json", "meta/redaction-report.json", "meta/migration-report.json"):
        if report_path in entries:
            try:
                report = json.loads(entries[report_path].decode("utf-8", errors="strict"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid report {report_path}: {error}") from error
            _operation_report(report, report_path)
    return {"valid": True, "spec": manifest["spec"], "image_digest": root, "layers": len(manifest["layers"])}


def inspect_image(image: Path) -> dict[str, Any]:
    document = load_image(image)
    kinds: Counter[str] = Counter()
    privacy: dict[str, dict[str, int]] = {}
    for layer in document.manifest["layers"]:
        kinds[layer["kind"]] += 1
        bucket = privacy.setdefault(layer["privacy"], {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += layer["size"]
    layer_inventory = [
        {
            key: layer[key]
            for key in ("id", "kind", "media_type", "path", "digest", "size", "privacy", "portability")
        }
        for layer in document.manifest["layers"]
    ]
    return {
        "spec": document.manifest["spec"],
        "image": document.manifest["image"],
        "runtime": document.manifest.get("runtime"),
        "layers": {
            "total": len(document.manifest["layers"]),
            "by_kind": dict(sorted(kinds.items())),
            "items": layer_inventory,
        },
        "privacy": {"policy": document.manifest["privacy"], "summary": privacy},
        "development": document.manifest.get("development"),
        "evaluations": document.manifest.get("evaluations", []),
        "lineage": document.manifest.get("lineage"),
    }


def redact_image(image: Path, output: Path) -> dict[str, Any]:
    document = load_image(image)
    kept = [copy.deepcopy(layer) for layer in document.manifest["layers"] if layer["privacy"] == "public"]
    payloads = {layer["path"]: document.entries[layer["path"]] for layer in kept}
    manifest = copy.deepcopy(document.manifest)
    manifest["layers"] = kept
    manifest["image"]["digest"] = layer_root_digest(kept)
    manifest["privacy"] = {"default": "private", "public_build": True, "unresolved_items": 0}
    outcomes = [
        {
            "id": layer["id"],
            "action": "preserved" if layer["privacy"] == "public" else "redacted",
            "reason": "public layer retained" if layer["privacy"] == "public" else "non-public layer removed",
        }
        for layer in document.manifest["layers"]
    ]
    report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "redact",
        "inventory_count": len(outcomes),
        "outcomes": outcomes,
    }
    export = AdapterExport(manifest=manifest, payloads=payloads, source_report=report)
    if output.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = _entries_for(export, redaction_report=report)
    with tempfile.TemporaryDirectory(prefix=".agent-image-redact-", dir=output.parent) as temporary:
        candidate = Path(temporary) / "candidate.aimg"
        pack_entries(entries, candidate)
        verify_image(candidate)
        os.replace(candidate, output)
    return {"operation": "redact", "output": str(output.resolve()), "layers": len(kept), "verified": True}


def diff_images(before: Path, after: Path) -> dict[str, Any]:
    left = load_image(before).manifest
    right = load_image(after).manifest
    left_layers = {layer["id"]: layer for layer in left["layers"]}
    right_layers = {layer["id"]: layer for layer in right["layers"]}
    added = sorted(set(right_layers) - set(left_layers))
    removed = sorted(set(left_layers) - set(right_layers))
    changed = sorted(
        layer_id
        for layer_id in set(left_layers) & set(right_layers)
        if left_layers[layer_id] != right_layers[layer_id]
    )
    return {
        "spec": {"before": left["spec"], "after": right["spec"]},
        "layers": {"added": added, "removed": removed, "changed": changed},
        "development": {"before": left.get("development"), "after": right.get("development")},
        "evaluations": {"before": left.get("evaluations", []), "after": right.get("evaluations", [])},
        "privacy": {"before": left["privacy"], "after": right["privacy"]},
    }
