from __future__ import annotations

import json
from typing import Any, Mapping

NATIVE_REALIZATION_SPEC = "agent-image-native-realization/v0.1"
NATIVE_REALIZATION_MEDIA_TYPE = "application/vnd.agent-image.native-realization+json"
REALIZATION_KINDS = {"embedding", "retrieval", "index", "ranking", "runtime", "other"}


class NativeRealizationError(ValueError):
    pass


class _DuplicateJsonKey(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _nonempty(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeRealizationError(f"{where} must be a non-empty string")
    return value


def parse_native_realization_bytes(data: bytes) -> dict[str, Any]:
    """Validate the generic envelope for a profile-owned realization identity."""
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as error:
        raise NativeRealizationError(f"invalid native realization JSON: {error}") from error
    if not isinstance(value, dict):
        raise NativeRealizationError("native realization document must be an object")
    allowed = {"spec", "kind", "profile", "identity"}
    extra = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    if missing:
        raise NativeRealizationError(f"native realization missing fields: {', '.join(missing)}")
    if extra:
        raise NativeRealizationError(f"native realization has unsupported fields: {', '.join(extra)}")
    if value["spec"] != NATIVE_REALIZATION_SPEC:
        raise NativeRealizationError(f"unsupported native realization spec: {value['spec']!r}")
    kind = _nonempty(value["kind"], "kind")
    if kind not in REALIZATION_KINDS:
        raise NativeRealizationError(f"unsupported native realization kind: {kind}")
    profile = value["profile"]
    if not isinstance(profile, dict) or set(profile) != {"id", "version"}:
        raise NativeRealizationError("profile must contain exactly id and version")
    _nonempty(profile["id"], "profile.id")
    _nonempty(profile["version"], "profile.version")
    identity = value["identity"]
    if not isinstance(identity, dict) or not identity:
        raise NativeRealizationError("identity must be a non-empty object")
    return value


def validate_realization_references(derived_items: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Resolve rebuild.realization_ref to preserved terminal realization sidecars."""
    by_id = {str(item["id"]): item for item in derived_items}
    referenced: dict[str, Mapping[str, Any]] = {}
    for item in derived_items:
        rebuild = item["rebuild"]
        ref = rebuild.get("realization_ref")
        if ref is None:
            continue
        target = by_id.get(ref)
        if target is None:
            raise NativeRealizationError(
                f"derived object {item['id']!r} has dangling realization_ref {ref!r}"
            )
        if target is item:
            raise NativeRealizationError(f"derived object {item['id']!r} cannot realize itself")
        if target.get("media_type") != NATIVE_REALIZATION_MEDIA_TYPE:
            raise NativeRealizationError(
                f"realization_ref {ref!r} must target media type {NATIVE_REALIZATION_MEDIA_TYPE}"
            )
        target_rebuild = target.get("rebuild", {})
        if target_rebuild.get("policy") != "not-rebuildable":
            raise NativeRealizationError(
                f"realization sidecar {ref!r} must use rebuild.policy=not-rebuildable"
            )
        if "path" not in target:
            raise NativeRealizationError(f"realization sidecar {ref!r} must carry preserved bytes")
        if target_rebuild.get("realization_ref") is not None:
            raise NativeRealizationError(f"realization sidecar {ref!r} cannot reference another realization")
        referenced[ref] = target
    return referenced
