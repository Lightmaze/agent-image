from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from agent_image.adapter_contract import AdapterExport, ProductionAdapter
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.native_capsule import inspect_native_capsule_bytes


BUILD_PLAN_SPEC = "agent-image-build-plan/v0.1"
NATIVE_CAPSULE_MEDIA_TYPE = "application/vnd.agent-image.native-capsule+tar"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class _DuplicateJsonKey(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJsonKey(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _error(code: str, message: str, *, details: Any | None = None) -> AgentImageError:
    return AgentImageError(code, message, details=details)


def _digest(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise _error("E_SPEC_INVALID", f"{where} must be a sha256:<hex> digest.")
    return value


def _source_digest_from_inspection(inspection: Mapping[str, Any]) -> str:
    source = inspection.get("source")
    if not isinstance(source, Mapping):
        raise _error("E_SPEC_INVALID", "Adapter inspection must contain an object source field.")
    return _digest(source.get("digest"), "inspection.source.digest")


def _adapter_subject(adapter: ProductionAdapter, inspection: Mapping[str, Any]) -> dict[str, str]:
    declared = inspection.get("adapter")
    if not isinstance(declared, Mapping):
        raise _error("E_SPEC_INVALID", "Adapter inspection must contain adapter identity.")
    actual = {"id": str(adapter.id), "version": str(adapter.version)}
    if dict(declared) != actual:
        raise _error(
            "E_SPEC_INVALID",
            "Adapter inspection identity does not match the executing adapter.",
            details={"inspection": dict(declared), "actual": actual},
        )
    return actual


def _native_object_projection(index: Mapping[str, Any]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for role in ("authoritative", "derived"):
        values = index.get(role)
        if not isinstance(values, list):
            raise _error("E_SPEC_INVALID", f"Native capsule {role} must be a list.")
        for item in values:
            if not isinstance(item, Mapping) or "path" not in item:
                continue
            objects.append(
                {
                    "role": role,
                    "id": item["id"],
                    "path": item["path"],
                    "media_type": item["media_type"],
                    "digest": item["digest"],
                    "size": item["size"],
                    "source_privacy": item["privacy"],
                }
            )
    return sorted(objects, key=lambda item: (item["role"], item["id"], item["path"]))


def native_unit_subject(*, layer_id: str, index: Mapping[str, Any]) -> dict[str, Any]:
    profile = index.get("profile")
    if not isinstance(profile, Mapping) or not isinstance(profile.get("id"), str) or not isinstance(profile.get("version"), str):
        raise _error("E_SPEC_INVALID", "Native capsule profile is invalid for build-plan binding.")
    subject = {
        "layer_id": layer_id,
        "profile": {"id": profile["id"], "version": profile["version"]},
        "objects": _native_object_projection(index),
    }
    subject["subject_digest"] = sha256_bytes(canonical_json_bytes(subject))
    return subject


def structured_native_subject_from_export(export: AdapterExport) -> dict[str, Any] | None:
    units: list[dict[str, Any]] = []
    for layer in export.manifest.get("layers", []):
        if layer.get("media_type") != NATIVE_CAPSULE_MEDIA_TYPE:
            continue
        path = layer.get("path")
        if not isinstance(path, str) or path not in export.payloads:
            raise _error("E_SPEC_INVALID", f"Structured native layer {layer.get('id')} has no payload bytes.")
        document = inspect_native_capsule_bytes(export.payloads[path])
        units.append(native_unit_subject(layer_id=str(layer["id"]), index=document.index))
    if not units:
        return None
    units = sorted(units, key=lambda item: item["layer_id"])
    body = {
        "schema": "agent-image-structured-native-build-subject/v0.1",
        "units": units,
    }
    body["subject_digest"] = sha256_bytes(canonical_json_bytes(body))
    return body


def structured_native_subject_from_inspection(inspection: Mapping[str, Any]) -> dict[str, Any] | None:
    candidate = inspection.get("structured_native")
    if candidate is None:
        return None
    if not isinstance(candidate, Mapping):
        raise _error("E_SPEC_INVALID", "inspection.structured_native must be an object.")
    units = candidate.get("units")
    if not isinstance(units, list) or not units:
        raise _error("E_SPEC_INVALID", "inspection.structured_native.units must be a non-empty list.")
    normalized: list[dict[str, Any]] = []
    for position, unit in enumerate(units):
        if not isinstance(unit, Mapping):
            raise _error("E_SPEC_INVALID", f"inspection.structured_native.units[{position}] must be an object.")
        layer_id = unit.get("layer_id")
        index = unit.get("capsule_index")
        if not isinstance(layer_id, str) or not layer_id or not isinstance(index, Mapping):
            raise _error("E_SPEC_INVALID", f"inspection structured-native unit {position} is incomplete.")
        normalized.append(native_unit_subject(layer_id=layer_id, index=index))
    normalized = sorted(normalized, key=lambda item: item["layer_id"])
    body = {
        "schema": "agent-image-structured-native-build-subject/v0.1",
        "units": normalized,
    }
    body["subject_digest"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _plan_body(
    adapter: ProductionAdapter,
    inspection: Mapping[str, Any],
    *,
    source: str,
    policy: str,
    include_experience: bool,
    include_workspace: bool,
) -> dict[str, Any]:
    if policy not in {"private", "public"}:
        raise _error("E_SPEC_INVALID", f"Unsupported build policy: {policy}")
    adapter_identity = _adapter_subject(adapter, inspection)
    source_harness = inspection.get("source_harness")
    if not isinstance(source_harness, Mapping):
        raise _error("E_SPEC_INVALID", "Adapter inspection must contain source_harness.")
    inventory_count = inspection.get("inventory_count")
    if not isinstance(inventory_count, int) or isinstance(inventory_count, bool) or inventory_count < 0:
        raise _error("E_SPEC_INVALID", "Adapter inspection inventory_count must be non-negative integer.")
    native_subject = structured_native_subject_from_inspection(inspection)
    return {
        "spec": BUILD_PLAN_SPEC,
        "adapter": adapter_identity,
        "source_harness": dict(source_harness),
        "source_locator_digest": sha256_bytes(source.encode("utf-8")),
        "source_state_digest": _source_digest_from_inspection(inspection),
        "inventory_count": inventory_count,
        "intent": {
            "policy": policy,
            "include_experience": bool(include_experience),
            "include_workspace": bool(include_workspace),
        },
        "structured_native_subject": native_subject,
        "requires_confirmation": True,
    }


def create_build_plan(
    adapter: ProductionAdapter,
    *,
    source: str,
    policy: str,
    include_experience: bool = False,
    include_workspace: bool = False,
) -> dict[str, Any]:
    inspection = adapter.inspect_source(source)
    body = _plan_body(
        adapter,
        inspection,
        source=source,
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
    )
    plan = dict(body)
    plan["plan_digest"] = sha256_bytes(canonical_json_bytes(body))
    return plan


def verify_build_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or plan.get("spec") != BUILD_PLAN_SPEC:
        raise _error("E_SPEC_INVALID", f"Build plan must use {BUILD_PLAN_SPEC}.")
    required = {
        "spec",
        "adapter",
        "source_harness",
        "source_locator_digest",
        "source_state_digest",
        "inventory_count",
        "intent",
        "structured_native_subject",
        "requires_confirmation",
        "plan_digest",
    }
    extras = sorted(set(plan) - required)
    missing = sorted(required - set(plan))
    if extras or missing:
        raise _error("E_SPEC_INVALID", "Build plan fields do not match v0.1.", details={"missing": missing, "extra": extras})
    _digest(plan["source_locator_digest"], "plan.source_locator_digest")
    _digest(plan["source_state_digest"], "plan.source_state_digest")
    _digest(plan["plan_digest"], "plan.plan_digest")
    if plan.get("requires_confirmation") is not True:
        raise _error("E_SPEC_INVALID", "Build plan requires_confirmation must be true.")
    body = {key: plan[key] for key in plan if key != "plan_digest"}
    expected = sha256_bytes(canonical_json_bytes(body))
    if plan["plan_digest"] != expected:
        raise _error("E_PLAN_STALE", "Build plan self digest does not match its contents.", details={"expected": expected, "actual": plan["plan_digest"]})
    return dict(plan)


def load_build_plan(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_unique_json_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as error:
        raise _error("E_SPEC_INVALID", f"Could not load build plan: {error}") from error
    if not isinstance(value, Mapping):
        raise _error("E_SPEC_INVALID", "Build plan root must be an object.")
    return verify_build_plan(value)


def preflight_approved_plan(
    plan: Mapping[str, Any],
    adapter: ProductionAdapter,
    *,
    source: str,
    policy: str,
    include_experience: bool = False,
    include_workspace: bool = False,
) -> dict[str, Any]:
    verified = verify_build_plan(plan)
    expected_adapter = {"id": str(adapter.id), "version": str(adapter.version)}
    if verified["adapter"] != expected_adapter:
        raise _error("E_PLAN_STALE", "Build plan adapter identity drifted.", details={"planned": verified["adapter"], "actual": expected_adapter})
    locator_digest = sha256_bytes(source.encode("utf-8"))
    if verified["source_locator_digest"] != locator_digest:
        raise _error("E_PLAN_STALE", "Build plan source locator drifted.")
    actual_intent = {
        "policy": policy,
        "include_experience": bool(include_experience),
        "include_workspace": bool(include_workspace),
    }
    if verified["intent"] != actual_intent:
        raise _error("E_PLAN_STALE", "Build intent drifted from the approved plan.", details={"planned": verified["intent"], "actual": actual_intent})
    inspection = adapter.inspect_source(source)
    _adapter_subject(adapter, inspection)
    current_source_digest = _source_digest_from_inspection(inspection)
    if verified["source_state_digest"] != current_source_digest:
        raise _error("E_PLAN_STALE", "Source state changed after plan review.", details={"planned": verified["source_state_digest"], "actual": current_source_digest})
    current_preview = structured_native_subject_from_inspection(inspection)
    if verified["structured_native_subject"] != current_preview:
        raise _error("E_PLAN_STALE", "Structured-native preview drifted after plan review.")
    return {"plan": verified, "inspection": dict(inspection)}


def require_export_matches_plan(plan: Mapping[str, Any] | None, export: AdapterExport) -> dict[str, Any] | None:
    actual_subject = structured_native_subject_from_export(export)
    if actual_subject is None:
        return None
    if plan is None:
        raise _error("E_PLAN_REQUIRED", "Structured-native publication requires an approved build plan.")
    verified = verify_build_plan(plan)
    planned_subject = verified.get("structured_native_subject")
    if planned_subject is None:
        raise _error("E_PLAN_STALE", "Approved plan did not bind a structured-native atomic-unit subject.")
    if planned_subject != actual_subject:
        raise _error(
            "E_PLAN_STALE",
            "Structured-native export drifted from the approved atomic-unit subject.",
            details={
                "planned": planned_subject.get("subject_digest"),
                "actual": actual_subject.get("subject_digest"),
            },
        )
    return actual_subject
