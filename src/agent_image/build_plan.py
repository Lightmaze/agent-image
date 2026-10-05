from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from agent_image.adapter_contract import AdapterExport, ProductionAdapter
from agent_image.canonical import canonical_json_bytes, pretty_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.native_export_planner import structured_native_subject


BUILD_PLAN_SPEC = "agent-image-build-plan/v0.1"


def _intent(*, policy: str, include_experience: bool, include_workspace: bool) -> dict[str, Any]:
    return {
        "policy": policy,
        "include_experience": bool(include_experience),
        "include_workspace": bool(include_workspace),
    }


def _plan_digest(value: Mapping[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "digest"}
    return sha256_bytes(canonical_json_bytes(payload))


def _require_object(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentImageError("E_SPEC_INVALID", f"{where} must be an object.")
    return value


def _require_nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise AgentImageError("E_SPEC_INVALID", f"{where} must be a non-empty string.")
    return value


def _inspection_source_digest(inspection: Mapping[str, Any]) -> str:
    source = _require_object(inspection.get("source"), "inspection.source")
    return _require_nonempty_string(source.get("digest"), "inspection.source.digest")


def create_reviewed_build_plan(
    adapter: ProductionAdapter,
    *,
    source: str,
    policy: str,
    include_experience: bool = False,
    include_workspace: bool = False,
) -> dict[str, Any]:
    inspection = adapter.inspect_source(source)
    export = adapter.export(
        source,
        policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
    )
    intent = _intent(
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
    )
    adapter_info = _require_object(inspection.get("adapter"), "inspection.adapter")
    source_harness = _require_object(inspection.get("source_harness"), "inspection.source_harness")
    plan: dict[str, Any] = {
        "spec": BUILD_PLAN_SPEC,
        "adapter": {
            "id": _require_nonempty_string(adapter_info.get("id"), "inspection.adapter.id"),
            "version": _require_nonempty_string(adapter_info.get("version"), "inspection.adapter.version"),
        },
        "source_harness": {
            "id": _require_nonempty_string(source_harness.get("id"), "inspection.source_harness.id"),
            "version": _require_nonempty_string(source_harness.get("version"), "inspection.source_harness.version"),
        },
        "source": {
            "locator_digest": sha256_bytes(source.encode("utf-8")),
            "state_digest": _inspection_source_digest(inspection),
            "inventory_count": int(inspection.get("inventory_count", 0)),
        },
        "intent": intent,
        "captured_export_image_digest": _require_nonempty_string(
            export.manifest.get("image", {}).get("digest"),
            "export.manifest.image.digest",
        ),
        "structured_native": structured_native_subject(export),
        "requires_confirmation": True,
    }
    plan["digest"] = _plan_digest(plan)
    return plan


def validate_build_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or plan.get("spec") != BUILD_PLAN_SPEC:
        raise AgentImageError("E_SPEC_INVALID", "Unsupported or malformed reviewed build plan.")
    required = {
        "spec",
        "adapter",
        "source_harness",
        "source",
        "intent",
        "captured_export_image_digest",
        "structured_native",
        "requires_confirmation",
        "digest",
    }
    if set(plan) != required:
        raise AgentImageError(
            "E_SPEC_INVALID",
            "Reviewed build plan has unsupported or missing fields.",
            details={"missing": sorted(required - set(plan)), "extra": sorted(set(plan) - required)},
        )
    adapter = _require_object(plan["adapter"], "plan.adapter")
    _require_nonempty_string(adapter.get("id"), "plan.adapter.id")
    _require_nonempty_string(adapter.get("version"), "plan.adapter.version")
    harness = _require_object(plan["source_harness"], "plan.source_harness")
    _require_nonempty_string(harness.get("id"), "plan.source_harness.id")
    _require_nonempty_string(harness.get("version"), "plan.source_harness.version")
    source = _require_object(plan["source"], "plan.source")
    _require_nonempty_string(source.get("locator_digest"), "plan.source.locator_digest")
    _require_nonempty_string(source.get("state_digest"), "plan.source.state_digest")
    if not isinstance(source.get("inventory_count"), int) or isinstance(source.get("inventory_count"), bool):
        raise AgentImageError("E_SPEC_INVALID", "plan.source.inventory_count must be an integer.")
    intent = _require_object(plan["intent"], "plan.intent")
    if set(intent) != {"policy", "include_experience", "include_workspace"}:
        raise AgentImageError("E_SPEC_INVALID", "plan.intent has unsupported or missing fields.")
    if intent.get("policy") not in {"private", "public"}:
        raise AgentImageError("E_SPEC_INVALID", "plan.intent.policy is invalid.")
    for key in ("include_experience", "include_workspace"):
        if not isinstance(intent.get(key), bool):
            raise AgentImageError("E_SPEC_INVALID", f"plan.intent.{key} must be boolean.")
    _require_nonempty_string(plan["captured_export_image_digest"], "plan.captured_export_image_digest")
    if plan["structured_native"] is not None:
        _require_object(plan["structured_native"], "plan.structured_native")
    if plan["requires_confirmation"] is not True:
        raise AgentImageError("E_SPEC_INVALID", "Reviewed build plan must require confirmation.")
    if plan["digest"] != _plan_digest(plan):
        raise AgentImageError("E_DIGEST_MISMATCH", "Reviewed build plan digest mismatch.")
    return dict(plan)


def write_build_plan(plan: Mapping[str, Any], output: Path) -> None:
    validate_build_plan(plan)
    if output.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Build plan already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = pretty_json_bytes(dict(plan))
    try:
        with output.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise AgentImageError("E_TARGET_EXISTS", f"Build plan already exists: {output}") from error


def load_build_plan(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"Reviewed build plan does not exist: {path}") from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_SPEC_INVALID", f"Cannot read reviewed build plan: {error}") from error
    return validate_build_plan(value)


def verify_plan_pre_capture(
    plan: Mapping[str, Any],
    adapter: ProductionAdapter,
    *,
    source: str,
    inspection: Mapping[str, Any],
    policy: str,
    include_experience: bool,
    include_workspace: bool,
) -> None:
    del adapter
    plan = validate_build_plan(plan)
    expected_intent = _intent(
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
    )
    adapter_info = _require_object(inspection.get("adapter"), "inspection.adapter")
    harness = _require_object(inspection.get("source_harness"), "inspection.source_harness")
    actual = {
        "adapter": {
            "id": str(adapter_info.get("id", "")),
            "version": str(adapter_info.get("version", "")),
        },
        "source_harness": {
            "id": str(harness.get("id", "")),
            "version": str(harness.get("version", "")),
        },
        "source": {
            "locator_digest": sha256_bytes(source.encode("utf-8")),
            "state_digest": _inspection_source_digest(inspection),
            "inventory_count": int(inspection.get("inventory_count", 0)),
        },
        "intent": expected_intent,
    }
    expected = {key: plan[key] for key in ("adapter", "source_harness", "source", "intent")}
    if actual != expected:
        raise AgentImageError(
            "E_PLAN_STALE",
            "Reviewed build plan no longer matches the adapter, source, or build intent.",
            details={"expected": expected, "actual": actual},
        )


def verify_plan_post_capture(plan: Mapping[str, Any], export: AdapterExport) -> None:
    plan = validate_build_plan(plan)
    actual_image_digest = _require_nonempty_string(
        export.manifest.get("image", {}).get("digest"),
        "export.manifest.image.digest",
    )
    actual_native = structured_native_subject(export)
    if actual_image_digest != plan["captured_export_image_digest"] or actual_native != plan["structured_native"]:
        raise AgentImageError(
            "E_PLAN_STALE",
            "Reviewed build plan no longer matches the captured export subject.",
            details={
                "expected_image_digest": plan["captured_export_image_digest"],
                "actual_image_digest": actual_image_digest,
                "expected_structured_native": plan["structured_native"],
                "actual_structured_native": actual_native,
            },
        )
