from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from agent_image.errors import AgentImageError
from agent_image.continuation import verify_continuation_binding


@dataclass(frozen=True)
class ContinuationEvidenceRequest:
    """Immutable, byte-bound inputs exposed to a receiver-selected verifier."""

    binding_schema: str
    binding_scope: str
    binding_digest: str
    parent_image_digest: str
    parent_entry_set_digest: str
    child_image_digest: str
    child_entry_set_digest: str
    state_delta_digest: str
    evidence_kind: str
    evidence_media_type: str
    evidence_digest: str
    evidence_bytes: bytes


@dataclass(frozen=True)
class ContinuationEvidenceClaims:
    """Claims a verifier may make; authority issuance is intentionally absent."""

    evidence_semantics_verified: bool
    continuation_relation_verified: bool
    causal_transition_verified: bool = False
    behavioral_retention_verified: bool = False


class ContinuationEvidenceVerifier(Protocol):
    """A verifier supplied by receiver policy, never discovered from Image data."""

    verifier_id: str
    verifier_version: str

    def verify(self, request: ContinuationEvidenceRequest) -> ContinuationEvidenceClaims:
        ...


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentImageError("E_SPEC_INVALID", f"Continuation binding {label} must be an object.")
    return value


def _text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AgentImageError("E_SPEC_INVALID", f"{label} must be a non-empty string.")
    return value


def _claims(value: Any) -> ContinuationEvidenceClaims:
    if type(value) is not ContinuationEvidenceClaims:
        raise AgentImageError(
            "E_SPEC_INVALID",
            "Continuation evidence verifier must return ContinuationEvidenceClaims.",
        )
    fields = (
        value.evidence_semantics_verified,
        value.continuation_relation_verified,
        value.causal_transition_verified,
        value.behavioral_retention_verified,
    )
    if any(type(item) is not bool for item in fields):
        raise AgentImageError("E_SPEC_INVALID", "Continuation evidence claims must be booleans.")
    if (
        value.continuation_relation_verified
        or value.causal_transition_verified
        or value.behavioral_retention_verified
    ) and not value.evidence_semantics_verified:
        raise AgentImageError(
            "E_SPEC_INVALID",
            "Continuation, causal, or behavioral claims require verified evidence semantics.",
        )
    if (
        value.causal_transition_verified or value.behavioral_retention_verified
    ) and not value.continuation_relation_verified:
        raise AgentImageError(
            "E_SPEC_INVALID",
            "Causal or behavioral claims require a verified continuation relation.",
        )
    return value


def verify_with_receiver_evidence(
    binding: Mapping[str, Any],
    parent: Path,
    child: Path,
    *,
    transition_evidence: bytes,
    verifier: ContinuationEvidenceVerifier,
) -> dict[str, Any]:
    """Apply an explicitly receiver-supplied verifier after structural verification.

    The binding's evidence kind is data, not an executable locator. This function
    performs no registry lookup, dynamic import, or authority issuance.
    """
    structural = verify_continuation_binding(
        binding,
        parent,
        child,
        transition_evidence=transition_evidence,
    )

    verifier_id = _text(getattr(verifier, "verifier_id", None), label="Verifier id")
    verifier_version = _text(
        getattr(verifier, "verifier_version", None), label="Verifier version"
    )
    parent_subject = _mapping(binding.get("parent"), label="parent")
    child_subject = _mapping(binding.get("child"), label="child")
    parent_entries = _mapping(
        parent_subject.get("verified_entry_set"), label="parent verified entry set"
    )
    child_entries = _mapping(
        child_subject.get("verified_entry_set"), label="child verified entry set"
    )
    evidence = _mapping(binding.get("transition_evidence"), label="transition evidence")

    request = ContinuationEvidenceRequest(
        binding_schema=_text(binding.get("schema"), label="Binding schema"),
        binding_scope=_text(binding.get("scope"), label="Binding scope"),
        binding_digest=_text(structural.get("binding_digest"), label="Binding digest"),
        parent_image_digest=_text(
            parent_subject.get("image_digest"), label="Parent image digest"
        ),
        parent_entry_set_digest=_text(
            parent_entries.get("digest"), label="Parent entry-set digest"
        ),
        child_image_digest=_text(
            child_subject.get("image_digest"), label="Child image digest"
        ),
        child_entry_set_digest=_text(
            child_entries.get("digest"), label="Child entry-set digest"
        ),
        state_delta_digest=_text(
            structural.get("state_delta_digest"), label="State-delta digest"
        ),
        evidence_kind=_text(evidence.get("kind"), label="Evidence kind"),
        evidence_media_type=_text(
            evidence.get("media_type"), label="Evidence media type"
        ),
        evidence_digest=_text(
            structural.get("transition_evidence_digest"), label="Evidence digest"
        ),
        evidence_bytes=bytes(transition_evidence),
    )
    try:
        verified_claims = _claims(verifier.verify(request))
    except AgentImageError:
        raise
    except Exception as error:
        raise AgentImageError(
            "E_VERIFIER_FAILED",
            "Receiver-selected continuation evidence verifier failed.",
            details={"verifier_id": verifier_id, "verifier_version": verifier_version},
        ) from error

    return {
        **structural,
        "evidence_verifier": {
            "id": verifier_id,
            "version": verifier_version,
            "selection": "receiver-supplied",
        },
        "evidence_semantics_verified": verified_claims.evidence_semantics_verified,
        "continuation_relation_verified": verified_claims.continuation_relation_verified,
        "causal_transition_verified": verified_claims.causal_transition_verified,
        "behavioral_retention_verified": verified_claims.behavioral_retention_verified,
        "activation_binding_issued": False,
        "receiver_authority_transferred": False,
    }
