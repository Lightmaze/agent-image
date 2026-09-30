from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agent_image.adapter_contract import AdapterExport
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.continuation import build_continuation_binding, verify_continuation_binding
from agent_image.errors import AgentImageError
from agent_image.evidence_verifier import (
    ContinuationEvidenceClaims,
    ContinuationEvidenceRequest,
    verify_with_receiver_evidence,
)
from agent_image.image_archive import layer_root_digest, publish_image


def _layer(*, layer_id: str, kind: str, path: str, payload: bytes, origin: str) -> dict[str, object]:
    return {
        "id": layer_id,
        "kind": kind,
        "media_type": "text/plain",
        "path": path,
        "digest": sha256_bytes(payload),
        "size": len(payload),
        "privacy": "private",
        "portability": "portable",
        "source": {"path": path.split("/", 2)[-1], "origin": origin, "reason": "synthetic continuation binding"},
    }


def _write_image(
    path: Path,
    *,
    name: str,
    origin: str,
    identity_payload: bytes = b"stable identity\n",
    memory_payload: bytes = b"parent memory\n",
) -> None:
    payloads = {
        "layers/identity/SOUL.md": identity_payload,
        "layers/memory/MEMORY.md": memory_payload,
    }
    layers = [
        _layer(
            layer_id="identity-main",
            kind="identity",
            path="layers/identity/SOUL.md",
            payload=identity_payload,
            origin=origin,
        ),
        _layer(
            layer_id="memory-main",
            kind="memory",
            path="layers/memory/MEMORY.md",
            payload=memory_payload,
            origin=origin,
        ),
    ]
    layers.sort(key=lambda item: str(item["path"]))
    manifest = {
        "spec": "agent-image/v0.1",
        "image": {
            "name": name,
            "version": "1",
            "created_at": "2026-09-21T16:30:00Z",
            "digest": layer_root_digest(layers),
        },
        "runtime": {
            "harness": {"id": "synthetic", "version": "1"},
            "adapter": {"id": "synthetic", "version": "1"},
        },
        "layers": layers,
        "privacy": {"default": "private", "public_build": False, "unresolved_items": 0},
        "provenance": {
            "source_harness": "synthetic",
            "source_adapter": "synthetic",
            "export_tool_version": "test",
        },
    }
    report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "build",
        "inventory_count": len(layers),
        "outcomes": [
            {"id": layer["id"], "action": "preserved", "reason": "synthetic continuation binding"}
            for layer in layers
        ],
    }
    publish_image(AdapterExport(manifest=manifest, payloads=payloads, source_report=report), path)


def _images(tmp_path: Path) -> tuple[Path, Path, bytes]:
    parent = tmp_path / "parent.aimg"
    child = tmp_path / "child.aimg"
    _write_image(parent, name="parent", origin="synthetic:parent")
    _write_image(
        child,
        name="child",
        origin="synthetic:child",
        memory_payload=b"parent memory\nchild memory\n",
    )
    evidence = canonical_json_bytes(
        {
            "schema": "synthetic-continuation-observation/v0.1",
            "steps": ["restore-parent", "mutate-state", "build-child", "restore-child"],
        }
    )
    return parent, child, evidence


def test_binding_separates_state_delta_from_descriptor_metadata(tmp_path: Path) -> None:
    parent, child, evidence = _images(tmp_path)

    binding = build_continuation_binding(
        parent,
        child,
        transition_evidence=evidence,
        evidence_kind="synthetic-runtime-observation",
        evidence_media_type="application/json",
    )
    verified = verify_continuation_binding(binding, parent, child, transition_evidence=evidence)

    assert binding["state_delta"]["state_changed"] == ["memory-main"]
    assert binding["descriptor_metadata_changed"] == ["identity-main"]
    assert binding["state_delta"]["added"] == []
    assert binding["state_delta"]["removed"] == []
    assert verified["valid"] is True
    assert verified["binding_valid"] is True
    assert verified["evidence_semantics_verified"] is False
    assert verified["continuation_relation_verified"] is False
    assert verified["causal_transition_verified"] is False
    assert verified["behavioral_retention_verified"] is False


def test_binding_validity_does_not_validate_relation_or_direction(tmp_path: Path) -> None:
    parent, child, evidence = _images(tmp_path)

    # The structural primitive can truthfully bind the same artifacts in reverse.
    # That makes the byte-level binding valid, not the claimed continuation.
    reversed_binding = build_continuation_binding(
        child,
        parent,
        transition_evidence=evidence,
        evidence_kind="synthetic-runtime-observation",
        evidence_media_type="application/json",
    )
    verified = verify_continuation_binding(
        reversed_binding, child, parent, transition_evidence=evidence
    )

    assert verified["valid"] is True
    assert verified["binding_valid"] is True
    assert verified["evidence_semantics_verified"] is False
    assert verified["continuation_relation_verified"] is False
    assert verified["causal_transition_verified"] is False
    assert verified["behavioral_retention_verified"] is False


def test_exact_entry_set_binding_rejects_wrong_parent_with_same_v01_image_digest(tmp_path: Path) -> None:
    parent, child, evidence = _images(tmp_path)
    wrong_parent = tmp_path / "wrong-parent.aimg"
    _write_image(wrong_parent, name="other-parent", origin="synthetic:other-parent")

    binding = build_continuation_binding(
        parent,
        child,
        transition_evidence=evidence,
        evidence_kind="synthetic-runtime-observation",
        evidence_media_type="application/json",
    )
    wrong_binding = build_continuation_binding(
        wrong_parent,
        child,
        transition_evidence=evidence,
        evidence_kind="synthetic-runtime-observation",
        evidence_media_type="application/json",
    )

    assert binding["parent"]["image_digest"] == wrong_binding["parent"]["image_digest"]
    assert (
        binding["parent"]["verified_entry_set"]["digest"]
        != wrong_binding["parent"]["verified_entry_set"]["digest"]
    )
    with pytest.raises(AgentImageError) as error:
        verify_continuation_binding(binding, wrong_parent, child, transition_evidence=evidence)
    assert error.value.code == "E_DIGEST_MISMATCH"


def test_binding_rejects_changed_transition_evidence_bytes(tmp_path: Path) -> None:
    parent, child, evidence = _images(tmp_path)
    binding = build_continuation_binding(
        parent,
        child,
        transition_evidence=evidence,
        evidence_kind="synthetic-runtime-observation",
        evidence_media_type="application/json",
    )

    with pytest.raises(AgentImageError) as error:
        verify_continuation_binding(binding, parent, child, transition_evidence=evidence + b"\n")
    assert error.value.code == "E_DIGEST_MISMATCH"


def test_binding_rejects_self_consistent_forged_state_delta(tmp_path: Path) -> None:
    parent, child, evidence = _images(tmp_path)
    binding = build_continuation_binding(
        parent,
        child,
        transition_evidence=evidence,
        evidence_kind="synthetic-runtime-observation",
        evidence_media_type="application/json",
    )
    forged = copy.deepcopy(binding)
    forged_delta = {
        "projection": forged["state_delta"]["projection"],
        "added": [],
        "removed": [],
        "state_changed": [],
    }
    forged["state_delta"] = {
        **forged_delta,
        "digest": sha256_bytes(canonical_json_bytes(forged_delta)),
    }

    with pytest.raises(AgentImageError) as error:
        verify_continuation_binding(forged, parent, child, transition_evidence=evidence)
    assert error.value.code == "E_DIGEST_MISMATCH"


def test_binding_requires_real_evidence_bytes(tmp_path: Path) -> None:
    parent, child, _ = _images(tmp_path)
    with pytest.raises(AgentImageError) as error:
        build_continuation_binding(
            parent,
            child,
            transition_evidence=b"",
            evidence_kind="synthetic-runtime-observation",
            evidence_media_type="application/json",
        )
    assert error.value.code == "E_SPEC_INVALID"



class _DigestReceiptVerifier:
    verifier_id = "test.receiver.digest-receipt"
    verifier_version = "0.1"

    def verify(self, request: ContinuationEvidenceRequest) -> ContinuationEvidenceClaims:
        receipt = json.loads(request.evidence_bytes)
        expected = {
            "schema": "synthetic-digest-receipt/v0.1",
            "parent_entry_set_digest": request.parent_entry_set_digest,
            "child_entry_set_digest": request.child_entry_set_digest,
            "state_delta_digest": request.state_delta_digest,
        }
        if receipt != expected:
            raise AgentImageError(
                "E_DIGEST_MISMATCH",
                "Synthetic receipt does not match the receiver-verified transition inputs.",
            )
        return ContinuationEvidenceClaims(
            evidence_semantics_verified=True,
            continuation_relation_verified=True,
        )


class _OverclaimingVerifier:
    verifier_id = "test.receiver.overclaim"
    verifier_version = "0.1"

    def verify(self, request: ContinuationEvidenceRequest) -> ContinuationEvidenceClaims:
        del request
        return ContinuationEvidenceClaims(
            evidence_semantics_verified=False,
            continuation_relation_verified=False,
            causal_transition_verified=True,
        )


class _NoClaimsVerifier:
    verifier_id = "test.receiver.explicit"
    verifier_version = "0.1"

    def __init__(self) -> None:
        self.seen_kind: str | None = None

    def verify(self, request: ContinuationEvidenceRequest) -> ContinuationEvidenceClaims:
        self.seen_kind = request.evidence_kind
        return ContinuationEvidenceClaims(
            evidence_semantics_verified=False,
            continuation_relation_verified=False,
        )


def _digest_receipt_case(
    tmp_path: Path,
    *,
    forged_child: bool = False,
) -> tuple[Path, Path, bytes, dict[str, object]]:
    parent, child, _ = _images(tmp_path)
    provisional = build_continuation_binding(
        parent,
        child,
        transition_evidence=b"provisional",
        evidence_kind="synthetic-digest-receipt",
        evidence_media_type="application/json",
    )
    child_digest = str(provisional["child"]["verified_entry_set"]["digest"])
    if forged_child:
        child_digest = "sha256:" + ("0" * 64)
    evidence = canonical_json_bytes(
        {
            "schema": "synthetic-digest-receipt/v0.1",
            "parent_entry_set_digest": provisional["parent"]["verified_entry_set"]["digest"],
            "child_entry_set_digest": child_digest,
            "state_delta_digest": provisional["state_delta"]["digest"],
        }
    )
    binding = build_continuation_binding(
        parent,
        child,
        transition_evidence=evidence,
        evidence_kind="synthetic-digest-receipt",
        evidence_media_type="application/json",
    )
    return parent, child, evidence, binding


def test_receiver_verifier_can_raise_only_evidence_backed_claims(tmp_path: Path) -> None:
    parent, child, evidence, binding = _digest_receipt_case(tmp_path)

    verified = verify_with_receiver_evidence(
        binding,
        parent,
        child,
        transition_evidence=evidence,
        verifier=_DigestReceiptVerifier(),
    )

    assert verified["binding_valid"] is True
    assert verified["evidence_semantics_verified"] is True
    assert verified["continuation_relation_verified"] is True
    assert verified["causal_transition_verified"] is False
    assert verified["behavioral_retention_verified"] is False
    assert verified["evidence_verifier"] == {
        "id": "test.receiver.digest-receipt",
        "version": "0.1",
        "selection": "receiver-supplied",
    }
    assert verified["activation_binding_issued"] is False
    assert verified["receiver_authority_transferred"] is False


def test_receiver_verifier_rejects_forged_receipt_after_structural_binding_passes(
    tmp_path: Path,
) -> None:
    parent, child, evidence, binding = _digest_receipt_case(tmp_path, forged_child=True)

    assert verify_continuation_binding(
        binding,
        parent,
        child,
        transition_evidence=evidence,
    )["binding_valid"] is True
    with pytest.raises(AgentImageError) as error:
        verify_with_receiver_evidence(
            binding,
            parent,
            child,
            transition_evidence=evidence,
            verifier=_DigestReceiptVerifier(),
        )
    assert error.value.code == "E_DIGEST_MISMATCH"


def test_receiver_verifier_rejects_claims_that_skip_prerequisites(tmp_path: Path) -> None:
    parent, child, evidence, binding = _digest_receipt_case(tmp_path)

    with pytest.raises(AgentImageError) as error:
        verify_with_receiver_evidence(
            binding,
            parent,
            child,
            transition_evidence=evidence,
            verifier=_OverclaimingVerifier(),
        )
    assert error.value.code == "E_SPEC_INVALID"


def test_evidence_kind_cannot_select_executable_verifier(tmp_path: Path) -> None:
    parent, child, _ = _images(tmp_path)
    evidence = b'{"opaque":true}'
    binding = build_continuation_binding(
        parent,
        child,
        transition_evidence=evidence,
        evidence_kind="python:os.system",
        evidence_media_type="application/json",
    )
    verifier = _NoClaimsVerifier()

    verified = verify_with_receiver_evidence(
        binding,
        parent,
        child,
        transition_evidence=evidence,
        verifier=verifier,
    )

    assert verifier.seen_kind == "python:os.system"
    assert verified["evidence_verifier"]["id"] == "test.receiver.explicit"
    assert verified["evidence_verifier"]["selection"] == "receiver-supplied"
    assert verified["evidence_semantics_verified"] is False
    assert verified["activation_binding_issued"] is False
