from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from agent_image.adapter_contract import ProductionAdapter
from agent_image.build_plan import preflight_approved_plan, require_export_matches_plan
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import load_image, publish_image
from agent_image.native_export_planner import finalize_structured_native_export


PREPARED_BUILD_SPEC = "agent-image-prepared-build/v0.1"


class _DuplicateJsonKey(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _fail(code: str, message: str, *, details: Any | None = None) -> AgentImageError:
    return AgentImageError(code, message, details=details)


def mint_prepared_build_receipt(
    *,
    adapter_subject: Mapping[str, Any],
    source_locator_digest: str,
    intent: Mapping[str, Any],
    pre_capture_plan_digest: str | None,
    candidate_bytes: bytes,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "spec": PREPARED_BUILD_SPEC,
        "adapter": dict(adapter_subject),
        "source_locator_digest": source_locator_digest,
        "intent": dict(intent),
        "pre_capture_plan_digest": pre_capture_plan_digest,
        "prepared_subject": {
            "archive_digest": sha256_bytes(candidate_bytes),
            "archive_size": len(candidate_bytes),
            "image_digest": manifest["image"]["digest"],
            "layer_count": len(manifest["layers"]),
            "public_build": bool(manifest["privacy"]["public_build"]),
            "unresolved_items": int(manifest["privacy"]["unresolved_items"]),
        },
        "approval": {
            "stage": "post-capture-publication",
            "subject": "exact-agent-image-archive-bytes",
            "requires_confirmation": True,
            "replay_policy": "same-subject-may-be-copied-more-than-once",
        },
        "storage": {
            "sensitivity": "inherits-image-privacy",
            "is_protocol_artifact": False,
        },
    }
    receipt = dict(body)
    receipt["receipt_digest"] = sha256_bytes(canonical_json_bytes(body))
    return verify_prepared_build_receipt(receipt)


def _receipt_body(
    *,
    adapter: ProductionAdapter,
    source: str,
    policy: str,
    include_experience: bool,
    include_workspace: bool,
    approved_plan: Mapping[str, Any] | None,
    candidate_bytes: bytes,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = mint_prepared_build_receipt(
        adapter_subject={"id": str(adapter.id), "version": str(adapter.version)},
        source_locator_digest=sha256_bytes(source.encode("utf-8")),
        intent={
            "policy": policy,
            "include_experience": bool(include_experience),
            "include_workspace": bool(include_workspace),
        },
        pre_capture_plan_digest=None if approved_plan is None else approved_plan["plan_digest"],
        candidate_bytes=candidate_bytes,
        manifest=manifest,
    )
    return {key: receipt[key] for key in receipt if key != "receipt_digest"}


def verify_prepared_build_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping) or receipt.get("spec") != PREPARED_BUILD_SPEC:
        raise _fail("E_SPEC_INVALID", f"Prepared build receipt must use {PREPARED_BUILD_SPEC}.")
    required = {
        "spec",
        "adapter",
        "source_locator_digest",
        "intent",
        "pre_capture_plan_digest",
        "prepared_subject",
        "approval",
        "storage",
        "receipt_digest",
    }
    missing = sorted(required - set(receipt))
    extra = sorted(set(receipt) - required)
    if missing or extra:
        raise _fail("E_SPEC_INVALID", "Prepared build receipt fields do not match v0.1.", details={"missing": missing, "extra": extra})

    subject = receipt.get("prepared_subject")
    if not isinstance(subject, Mapping):
        raise _fail("E_SPEC_INVALID", "prepared_subject must be an object.")
    if not isinstance(subject.get("archive_size"), int) or isinstance(subject.get("archive_size"), bool) or subject["archive_size"] < 0:
        raise _fail("E_SPEC_INVALID", "prepared_subject.archive_size must be a non-negative integer.")
    for field in ("archive_digest", "image_digest"):
        value = subject.get(field)
        if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
            raise _fail("E_SPEC_INVALID", f"prepared_subject.{field} must be a sha256 digest.")
    approval = receipt.get("approval")
    if not isinstance(approval, Mapping) or approval.get("requires_confirmation") is not True:
        raise _fail("E_SPEC_INVALID", "Prepared build approval must require confirmation.")
    if approval.get("stage") != "post-capture-publication":
        raise _fail("E_SPEC_INVALID", "Prepared build approval stage is invalid.")
    if approval.get("subject") != "exact-agent-image-archive-bytes":
        raise _fail("E_SPEC_INVALID", "Prepared build approval subject is invalid.")

    body = {key: receipt[key] for key in receipt if key != "receipt_digest"}
    expected = sha256_bytes(canonical_json_bytes(body))
    if receipt["receipt_digest"] != expected:
        raise _fail("E_PREPARED_STALE", "Prepared build receipt self digest does not match its contents.", details={"expected": expected, "actual": receipt.get("receipt_digest")})
    return dict(receipt)


def load_prepared_build_receipt(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_unique_json_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as error:
        raise _fail("E_SPEC_INVALID", f"Could not load prepared build receipt: {error}") from error
    if not isinstance(value, Mapping):
        raise _fail("E_SPEC_INVALID", "Prepared build receipt root must be an object.")
    return verify_prepared_build_receipt(value)


def prepare_build_candidate(
    adapter: ProductionAdapter,
    *,
    source: str,
    prepared_path: Path,
    policy: str = "private",
    include_experience: bool = False,
    include_workspace: bool = False,
    approved_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if prepared_path.exists():
        raise _fail("E_TARGET_EXISTS", f"Prepared candidate already exists: {prepared_path}")

    verified_plan: dict[str, Any] | None = None
    if approved_plan is not None:
        verified_plan = preflight_approved_plan(
            approved_plan,
            adapter,
            source=source,
            policy=policy,
            include_experience=include_experience,
            include_workspace=include_workspace,
        )["plan"]
    else:
        inspection = adapter.inspect_source(source)
        if inspection.get("structured_native") is not None:
            raise _fail("E_PLAN_REQUIRED", "Structured-native capture requires a reviewed pre-capture build plan.")

    exported = adapter.export(
        source,
        policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
    )
    require_export_matches_plan(verified_plan, exported)
    finalized = finalize_structured_native_export(exported, policy=policy)
    publish_image(finalized, prepared_path)

    candidate_bytes = prepared_path.read_bytes()
    document = load_image(prepared_path)
    body = _receipt_body(
        adapter=adapter,
        source=source,
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
        approved_plan=verified_plan,
        candidate_bytes=candidate_bytes,
        manifest=document.manifest,
    )
    receipt = dict(body)
    receipt["receipt_digest"] = sha256_bytes(canonical_json_bytes(body))
    return receipt


def save_prepared_build_receipt(receipt: Mapping[str, Any], path: Path) -> dict[str, Any]:
    verified = verify_prepared_build_receipt(receipt)
    if path.exists():
        raise _fail("E_TARGET_EXISTS", f"Prepared build receipt already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(canonical_json_bytes(verified) + b"\n")
    except OSError as error:
        raise _fail("E_IMAGE_CORRUPT", f"Could not persist prepared build receipt: {error}") from error
    return verified


def publish_prepared_candidate(
    prepared_path: Path,
    *,
    receipt: Mapping[str, Any],
    output: Path,
) -> dict[str, Any]:
    verified_receipt = verify_prepared_build_receipt(receipt)
    if output.exists():
        raise _fail("E_TARGET_EXISTS", f"Output already exists: {output}")

    try:
        candidate_bytes = prepared_path.read_bytes()
    except OSError as error:
        raise _fail("E_PREPARED_STALE", f"Could not read prepared candidate: {error}") from error
    subject = verified_receipt["prepared_subject"]
    actual_digest = sha256_bytes(candidate_bytes)
    if len(candidate_bytes) != subject["archive_size"] or actual_digest != subject["archive_digest"]:
        raise _fail(
            "E_PREPARED_STALE",
            "Prepared candidate bytes no longer match the reviewed receipt.",
            details={
                "expected_digest": subject["archive_digest"],
                "actual_digest": actual_digest,
                "expected_size": subject["archive_size"],
                "actual_size": len(candidate_bytes),
            },
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".agent-image-prepared-publish-", dir=output.parent) as temporary:
        staged = Path(temporary) / "candidate.aimg"
        staged.write_bytes(candidate_bytes)
        document = load_image(staged)
        if document.manifest["image"]["digest"] != subject["image_digest"]:
            raise _fail("E_PREPARED_STALE", "Prepared candidate image digest changed from reviewed receipt.")
        if len(document.manifest["layers"]) != subject["layer_count"]:
            raise _fail("E_PREPARED_STALE", "Prepared candidate layer count changed from reviewed receipt.")
        if bool(document.manifest["privacy"]["public_build"]) != subject["public_build"]:
            raise _fail("E_PREPARED_STALE", "Prepared candidate public/private mode changed from reviewed receipt.")
        if int(document.manifest["privacy"]["unresolved_items"]) != subject["unresolved_items"]:
            raise _fail("E_PREPARED_STALE", "Prepared candidate unresolved privacy count changed from reviewed receipt.")
        staged_digest = sha256_bytes(staged.read_bytes())
        if staged_digest != subject["archive_digest"]:
            raise _fail("E_PREPARED_STALE", "Staged publish bytes changed after verification.")
        try:
            os.replace(staged, output)
        except OSError as error:
            raise _fail("E_IMAGE_CORRUPT", f"Could not publish prepared candidate atomically: {error}") from error

    return {
        "operation": "publish-prepared-build",
        "output": str(output.resolve()),
        "prepared_receipt_digest": verified_receipt["receipt_digest"],
        "archive_digest": subject["archive_digest"],
        "image_digest": subject["image_digest"],
        "layers": subject["layer_count"],
        "verified": True,
        "source_reopened": False,
        "adapter_reinvoked": False,
    }
