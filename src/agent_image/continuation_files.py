from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent_image.continuation import build_continuation_binding, verify_continuation_binding
from agent_image.errors import AgentImageError


def _read_required_bytes(path: Path, *, label: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise AgentImageError(
            "E_SOURCE_NOT_FOUND",
            f"Could not read {label}: {path}",
            details={"path": str(path), "error": str(error)},
        ) from error
    if not data:
        raise AgentImageError("E_SPEC_INVALID", f"{label} must not be empty.")
    return data


def _load_binding(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise AgentImageError(
            "E_SOURCE_NOT_FOUND",
            f"Could not read continuation binding: {path}",
            details={"path": str(path), "error": str(error)},
        ) from error
    except json.JSONDecodeError as error:
        raise AgentImageError(
            "E_SPEC_INVALID",
            "Continuation binding is not valid UTF-8 JSON.",
            details={"path": str(path), "error": str(error)},
        ) from error
    if not isinstance(value, dict):
        raise AgentImageError("E_SPEC_INVALID", "Continuation binding root must be a JSON object.")
    return value


def _write_json_exclusive(value: dict[str, Any], output: Path) -> None:
    """Publish a derived binding without an exists-check/replace race."""
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    try:
        fd = os.open(output, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise AgentImageError("E_TARGET_EXISTS", f"Output already exists: {output}") from error
    except OSError as error:
        raise AgentImageError(
            "E_IMAGE_CORRUPT",
            f"Could not create continuation binding output: {error}",
            details={"path": str(output)},
        ) from error

    published = False
    try:
        with os.fdopen(fd, "w+b", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            handle.seek(0)
            raw = handle.read()
            try:
                round_tripped = json.loads(raw.decode("utf-8", errors="strict"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AgentImageError(
                    "E_IMAGE_CORRUPT",
                    "Continuation binding changed while being written.",
                    details={"path": str(output), "error": str(error)},
                ) from error
            if round_tripped != value:
                raise AgentImageError(
                    "E_IMAGE_CORRUPT",
                    "Continuation binding changed during output round-trip.",
                    details={"path": str(output)},
                )
        published = True
    finally:
        if not published:
            try:
                output.unlink(missing_ok=True)
            except OSError:
                pass


def bind_continuation_files(
    *, parent: Path, child: Path, evidence: Path,
    evidence_kind: str, evidence_media_type: str, output: Path,
) -> dict[str, Any]:
    """Create a structural binding; do not execute a harness or infer causality."""
    evidence_bytes = _read_required_bytes(evidence, label="transition evidence")
    binding = build_continuation_binding(
        parent,
        child,
        transition_evidence=evidence_bytes,
        evidence_kind=evidence_kind,
        evidence_media_type=evidence_media_type,
    )
    _write_json_exclusive(binding, output)
    verified = verify_continuation_binding(
        _load_binding(output), parent, child, transition_evidence=evidence_bytes
    )
    return {
        "operation": "continuation-bind",
        "output": str(output.resolve()),
        "valid": bool(verified.get("valid")),
        "binding_valid": bool(verified.get("binding_valid")),
        "evidence_semantics_verified": False,
        "continuation_relation_verified": False,
        "schema": verified.get("schema"),
        "scope": verified.get("scope"),
        "binding_digest": verified.get("binding_digest"),
        "state_delta_digest": verified.get("state_delta_digest"),
        "transition_evidence_digest": verified.get("transition_evidence_digest"),
        "causal_transition_verified": False,
        "behavioral_retention_verified": False,
    }


def verify_continuation_file(
    *, binding: Path, parent: Path, child: Path, evidence: Path,
) -> dict[str, Any]:
    return verify_continuation_binding(
        _load_binding(binding), parent, child,
        transition_evidence=_read_required_bytes(evidence, label="transition evidence"),
    )
