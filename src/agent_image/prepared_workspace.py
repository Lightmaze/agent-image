from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from agent_image.adapter_contract import ProductionAdapter
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import load_image
from agent_image.prepared_build import (
    mint_prepared_build_receipt,
    prepare_build_candidate,
    publish_prepared_candidate,
    save_prepared_build_receipt,
)


PREPARED_WORKSPACE_SPEC = "agent-image-prepared-workspace/v0.1"
SEAL_NAME = "seal.json"
CANDIDATE_NAME = "candidate.aimg"
RECEIPT_NAME = "receipt.json"


class _DuplicateJsonKey(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _DuplicateJsonKey(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def _fail(code: str, message: str, *, details: Any | None = None) -> AgentImageError:
    return AgentImageError(code, message, details=details)


def _paths(workspace: Path) -> tuple[Path, Path, Path]:
    return workspace / SEAL_NAME, workspace / CANDIDATE_NAME, workspace / RECEIPT_NAME


def _seal_body(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "spec": PREPARED_WORKSPACE_SPEC,
        "adapter": dict(receipt["adapter"]),
        "source_locator_digest": receipt["source_locator_digest"],
        "intent": dict(receipt["intent"]),
        "pre_capture_plan_digest": receipt["pre_capture_plan_digest"],
        "prepared_subject": dict(receipt["prepared_subject"]),
    }


def _mint_seal(receipt: Mapping[str, Any]) -> dict[str, Any]:
    body = _seal_body(receipt)
    seal = dict(body)
    seal["seal_digest"] = sha256_bytes(canonical_json_bytes(body))
    return seal


def _verify_seal(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("spec") != PREPARED_WORKSPACE_SPEC:
        raise _fail("E_SPEC_INVALID", f"Prepared workspace seal must use {PREPARED_WORKSPACE_SPEC}.")
    expected_fields = {
        "spec",
        "adapter",
        "source_locator_digest",
        "intent",
        "pre_capture_plan_digest",
        "prepared_subject",
        "seal_digest",
    }
    if set(value) != expected_fields:
        raise _fail("E_SPEC_INVALID", "Prepared workspace seal fields do not match v0.1.")
    body = {key: value[key] for key in value if key != "seal_digest"}
    expected = sha256_bytes(canonical_json_bytes(body))
    if value["seal_digest"] != expected:
        raise _fail("E_PREPARED_STALE", "Prepared workspace seal digest does not match its contents.")
    return dict(value)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as error:
        raise _fail("E_SPEC_INVALID", f"Could not load prepared workspace control file {path.name}: {error}") from error
    if not isinstance(value, Mapping):
        raise _fail("E_SPEC_INVALID", f"Prepared workspace control file {path.name} must be an object.")
    return dict(value)


def inspect_prepared_workspace(workspace: Path) -> dict[str, Any]:
    seal, candidate, receipt = _paths(workspace)
    if not workspace.exists():
        state = "absent"
    elif not workspace.is_dir():
        state = "inconsistent"
    elif not any(workspace.iterdir()):
        state = "empty"
    elif seal.exists() and candidate.exists() and receipt.exists():
        state = "complete"
    elif seal.exists() and candidate.exists() and not receipt.exists():
        state = "recoverable-receipt"
    elif candidate.exists() and not seal.exists():
        state = "orphan-candidate"
    elif seal.exists() and not candidate.exists():
        state = "sealed-no-candidate"
    else:
        state = "inconsistent"
    return {
        "operation": "inspect-prepared-workspace",
        "workspace": str(workspace.resolve()),
        "state": state,
        "has_seal": seal.exists(),
        "has_candidate": candidate.exists(),
        "has_receipt": receipt.exists(),
    }


def prepare_build_workspace(
    adapter: ProductionAdapter,
    *,
    source: str,
    workspace: Path,
    policy: str = "private",
    include_experience: bool = False,
    include_workspace: bool = False,
    approved_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if workspace.exists():
        if not workspace.is_dir() or any(workspace.iterdir()):
            raise _fail("E_TARGET_EXISTS", f"Prepared workspace is not empty: {workspace}")
    else:
        workspace.mkdir(parents=True)

    seal_path, candidate_path, receipt_path = _paths(workspace)
    receipt = prepare_build_candidate(
        adapter,
        source=source,
        prepared_path=candidate_path,
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
        approved_plan=approved_plan,
    )
    seal = _mint_seal(receipt)
    seal_path.write_bytes(canonical_json_bytes(seal) + b"\n")
    save_prepared_build_receipt(receipt, receipt_path)
    return {
        "operation": "prepare-build-workspace",
        "workspace": str(workspace.resolve()),
        "candidate": str(candidate_path.resolve()),
        "receipt": str(receipt_path.resolve()),
        "prepared_subject": receipt["prepared_subject"],
        "receipt_digest": receipt["receipt_digest"],
        "recoverable": True,
        "final_published": False,
    }


def recover_prepared_workspace(workspace: Path) -> dict[str, Any]:
    seal_path, candidate_path, receipt_path = _paths(workspace)
    state = inspect_prepared_workspace(workspace)
    if state["state"] == "complete":
        from agent_image.prepared_build import load_prepared_build_receipt
        receipt = load_prepared_build_receipt(receipt_path)
        return {
            "operation": "recover-prepared-workspace",
            "workspace": str(workspace.resolve()),
            "state": "complete",
            "receipt_digest": receipt["receipt_digest"],
            "recovered": False,
            "source_reopened": False,
        }
    if state["state"] != "recoverable-receipt":
        raise _fail(
            "E_PREPARED_STALE",
            f"Prepared workspace is not recoverable without recapture: {state['state']}.",
        )

    seal = _verify_seal(_load_json(seal_path))
    try:
        candidate_bytes = candidate_path.read_bytes()
    except OSError as error:
        raise _fail("E_PREPARED_STALE", f"Could not read prepared candidate: {error}") from error

    subject = seal["prepared_subject"]
    if len(candidate_bytes) != subject["archive_size"] or sha256_bytes(candidate_bytes) != subject["archive_digest"]:
        raise _fail("E_PREPARED_STALE", "Prepared candidate bytes do not match the workspace seal.")

    with tempfile.TemporaryDirectory(prefix=".agent-image-workspace-recover-", dir=workspace) as temporary:
        snapshot = Path(temporary) / CANDIDATE_NAME
        snapshot.write_bytes(candidate_bytes)
        document = load_image(snapshot)
        if document.manifest["image"]["digest"] != subject["image_digest"]:
            raise _fail("E_PREPARED_STALE", "Prepared candidate semantic image digest does not match the workspace seal.")
        if len(document.manifest["layers"]) != subject["layer_count"]:
            raise _fail("E_PREPARED_STALE", "Prepared candidate layer count does not match the workspace seal.")
        receipt = mint_prepared_build_receipt(
            adapter_subject=seal["adapter"],
            source_locator_digest=seal["source_locator_digest"],
            intent=seal["intent"],
            pre_capture_plan_digest=seal["pre_capture_plan_digest"],
            candidate_bytes=candidate_bytes,
            manifest=document.manifest,
        )

    save_prepared_build_receipt(receipt, receipt_path)
    return {
        "operation": "recover-prepared-workspace",
        "workspace": str(workspace.resolve()),
        "state": "complete",
        "receipt_digest": receipt["receipt_digest"],
        "recovered": True,
        "source_reopened": False,
    }


def publish_prepared_workspace(workspace: Path, *, output: Path) -> dict[str, Any]:
    from agent_image.prepared_build import load_prepared_build_receipt

    seal_path, candidate_path, receipt_path = _paths(workspace)
    state = inspect_prepared_workspace(workspace)
    if state["state"] != "complete":
        raise _fail("E_PREPARED_STALE", f"Prepared workspace is not complete: {state['state']}.")
    _verify_seal(_load_json(seal_path))
    receipt = load_prepared_build_receipt(receipt_path)
    result = publish_prepared_candidate(candidate_path, receipt=receipt, output=output)
    result["workspace"] = str(workspace.resolve())
    return result
