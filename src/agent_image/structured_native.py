from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from agent_image.errors import AgentImageError
from agent_image.native_capsule import NativeCapsuleDocument, inspect_native_capsule_bytes
from agent_image.native_classification import (
    NativeClassificationError,
    require_finalized_privacy_homogeneity,
    require_structured_native_portability,
)
from agent_image.scanner import secret_filename_reason, structured_secret_findings


NATIVE_CAPSULE_MEDIA_TYPE = "application/vnd.agent-image.native-capsule+tar"


def _fail(message: str, *, details: Any | None = None, code: str = "E_IMAGE_CORRUPT") -> None:
    raise AgentImageError(code, message, details=details)


def _payload_items(document: NativeCapsuleDocument) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    items.extend(document.index["authoritative"])
    items.extend(item for item in document.index["derived"] if "path" in item)
    return items


def _privacy_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(item["privacy"] for item in items)
    return dict(sorted(counts.items()))


def _scan_inner_secret_material(document: NativeCapsuleDocument, *, layer_id: str) -> None:
    capsule_keys = structured_secret_findings(
        "capsule.json", "application/json", document.entries["capsule.json"]
    )
    if capsule_keys:
        _fail(
            f"Secret-like structured keys detected in native capsule control state for layer {layer_id}.",
            code="E_SECRET_DETECTED",
            details={"inner_path": "capsule.json", "structured_keys": capsule_keys},
        )

    for item in _payload_items(document):
        path = item["path"]
        data = document.entries[path]
        reason = secret_filename_reason(path)
        findings = structured_secret_findings(path, item["media_type"], data)
        if item["privacy"] == "secret" or reason or findings:
            _fail(
                f"Secret material detected inside structured native layer {layer_id}.",
                code="E_SECRET_DETECTED",
                details={
                    "inner_object_id": item["id"],
                    "inner_path": path,
                    "declared_privacy": item["privacy"],
                    "filename": reason,
                    "structured_keys": findings,
                },
            )


def verify_structured_native_layer(layer: Mapping[str, Any], data: bytes) -> dict[str, Any] | None:
    if layer.get("media_type") != NATIVE_CAPSULE_MEDIA_TYPE:
        return None
    layer_id = str(layer.get("id", "<unknown>"))
    if layer.get("kind") != "native":
        _fail(f"Structured native capsule layer {layer_id} must use kind=native.")
    try:
        require_structured_native_portability(layer.get("portability"))
    except NativeClassificationError as error:
        _fail(f"Structured native capsule layer {layer_id}: {error}")
    outer_privacy = layer.get("privacy")

    document = inspect_native_capsule_bytes(data)
    items = _payload_items(document)
    embedded_classes = {item["privacy"] for item in items}
    try:
        require_finalized_privacy_homogeneity(outer_privacy, embedded_classes)
    except NativeClassificationError as error:
        _fail(
            f"Structured native capsule layer {layer_id} has invalid final classification: {error}",
            details={
                "outer_privacy": outer_privacy,
                "embedded_privacy": sorted(embedded_classes),
            },
        )

    _scan_inner_secret_material(document, layer_id=layer_id)

    authoritative = document.index["authoritative"]
    derived = document.index["derived"]
    preserved_derived = [item for item in derived if "path" in item]
    omitted_derived = [item for item in derived if "path" not in item]
    requirements = document.index["receiver"]["requirements"]

    return {
        "layer_id": layer_id,
        "profile": dict(document.index["profile"]),
        "capture": {
            key: document.index["capture"][key]
            for key in (
                "consistency",
                "write_barrier",
                "flushed",
                "history_fidelity",
                "source_mutation",
            )
        },
        "objects": {
            "authoritative": len(authoritative),
            "derived_preserved": len(preserved_derived),
            "derived_rebuild_only": len(omitted_derived),
            "embedded_bytes": sum(item["size"] for item in items),
            "privacy": _privacy_summary(items),
        },
        "closure": {
            "policy": document.index["closure"]["policy"],
            "check_count": len(document.index["closure"]["checks"]),
        },
        "receiver": {
            "authority_rebind_required": document.index["receiver"]["authority_rebind_required"],
            "requirement_count": len(requirements),
            "requirements": [
                {
                    "id": item["id"],
                    "kind": item["kind"],
                    "required_for": list(item["required_for"]),
                }
                for item in requirements
            ],
        },
        "compatibility": dict(document.index["compatibility"]),
        "profile_validation": "not-run",
        "public_review_required": outer_privacy == "public",
    }


def verify_structured_native_layers(
    manifest: Mapping[str, Any], entries: Mapping[str, bytes]
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for layer in manifest.get("layers", []):
        summary = verify_structured_native_layer(layer, entries[layer["path"]])
        if summary is not None:
            summaries.append(summary)
    return summaries


def _by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items}


def _object_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    projection = {
        "media_type": item.get("media_type"),
        "digest": item.get("digest"),
        "size": item.get("size"),
        "privacy": item.get("privacy"),
    }
    if "rebuild" in item:
        projection["rebuild"] = item["rebuild"]
    return projection


def _object_delta(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, list[str]]:
    left = _by_id(before)
    right = _by_id(after)
    shared = set(left) & set(right)
    return {
        "added": sorted(set(right) - set(left)),
        "removed": sorted(set(left) - set(right)),
        "changed": sorted(
            object_id
            for object_id in shared
            if _object_projection(left[object_id]) != _object_projection(right[object_id])
        ),
    }


def diff_structured_native_payloads(before: bytes, after: bytes) -> dict[str, Any]:
    left = inspect_native_capsule_bytes(before).index
    right = inspect_native_capsule_bytes(after).index
    return {
        "profile": {
            "before": left["profile"],
            "after": right["profile"],
            "changed": left["profile"] != right["profile"],
        },
        "capture_changed": left["capture"] != right["capture"],
        "authoritative": _object_delta(left["authoritative"], right["authoritative"]),
        "derived": _object_delta(left["derived"], right["derived"]),
        "receiver_changed": left["receiver"] != right["receiver"],
        "closure_changed": left["closure"] != right["closure"],
        "compatibility_changed": left["compatibility"] != right["compatibility"],
    }
