from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import (
    ImageDocument,
    LAYER_STATE_FIELDS,
    LAYER_STATE_PROJECTION_VERSION,
    load_image,
)


CONTINUATION_BINDING_SCHEMA = "agent-image-continuation-binding/v0.1"
VERIFIED_ENTRY_SET_VERSION = "agent-image-verified-entry-set/v0.1"
BINDING_SCOPE = "artifact-delta-evidence-binding"


def verified_entry_set_digest(document: ImageDocument) -> str:
    """Digest exactly the entry bytes validated by Core, independent of tar/gzip bytes."""
    inventory = [
        {
            "path": path,
            "digest": sha256_bytes(data),
            "size": len(data),
        }
        for path, data in sorted(document.entries.items())
    ]
    return sha256_bytes(canonical_json_bytes(inventory))


def _subject(document: ImageDocument) -> dict[str, Any]:
    return {
        "spec": document.manifest["spec"],
        "image_digest": document.manifest["image"]["digest"],
        "verified_entry_set": {
            "version": VERIFIED_ENTRY_SET_VERSION,
            "digest": verified_entry_set_digest(document),
            "entries": len(document.entries),
        },
    }


def _layer_state_projection(layer: Mapping[str, Any]) -> dict[str, Any]:
    return {field: layer[field] for field in LAYER_STATE_FIELDS}


def _diff_documents(parent: ImageDocument, child: ImageDocument) -> dict[str, Any]:
    left = parent.manifest
    right = child.manifest
    left_layers = {layer["id"]: layer for layer in left["layers"]}
    right_layers = {layer["id"]: layer for layer in right["layers"]}
    added = sorted(set(right_layers) - set(left_layers))
    removed = sorted(set(left_layers) - set(right_layers))
    shared = set(left_layers) & set(right_layers)
    changed = sorted(layer_id for layer_id in shared if left_layers[layer_id] != right_layers[layer_id])
    state_changed = sorted(
        layer_id
        for layer_id in shared
        if _layer_state_projection(left_layers[layer_id]) != _layer_state_projection(right_layers[layer_id])
    )
    state_changed_set = set(state_changed)
    metadata_changed = sorted(layer_id for layer_id in changed if layer_id not in state_changed_set)
    return {
        "projection": {
            "version": LAYER_STATE_PROJECTION_VERSION,
            "fields": list(LAYER_STATE_FIELDS),
        },
        "added": added,
        "removed": removed,
        "state_changed": state_changed,
        "metadata_changed": metadata_changed,
    }


def _state_delta(document_diff: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "projection": document_diff["projection"],
        "added": list(document_diff["added"]),
        "removed": list(document_diff["removed"]),
        "state_changed": list(document_diff["state_changed"]),
    }
    return {
        **value,
        "digest": sha256_bytes(canonical_json_bytes(value)),
    }


def build_continuation_binding(
    parent: Path,
    child: Path,
    *,
    transition_evidence: bytes,
    evidence_kind: str,
    evidence_media_type: str,
) -> dict[str, Any]:
    """Bind exact verified artifacts, their state delta, and opaque transition evidence.

    This does not establish that the evidence is truthful or that the parent caused
    the child. Harness/runtime evidence producers remain responsible for those claims.
    """
    if not transition_evidence:
        raise AgentImageError("E_SPEC_INVALID", "Continuation binding requires non-empty transition evidence bytes.")
    if not isinstance(evidence_kind, str) or not evidence_kind:
        raise AgentImageError("E_SPEC_INVALID", "Continuation evidence kind must be a non-empty string.")
    if not isinstance(evidence_media_type, str) or not evidence_media_type:
        raise AgentImageError("E_SPEC_INVALID", "Continuation evidence media type must be a non-empty string.")

    parent_document = load_image(parent)
    child_document = load_image(child)
    document_diff = _diff_documents(parent_document, child_document)
    return {
        "schema": CONTINUATION_BINDING_SCHEMA,
        "scope": BINDING_SCOPE,
        "parent": _subject(parent_document),
        "child": _subject(child_document),
        "state_delta": _state_delta(document_diff),
        "descriptor_metadata_changed": list(document_diff["metadata_changed"]),
        "transition_evidence": {
            "kind": evidence_kind,
            "media_type": evidence_media_type,
            "digest": sha256_bytes(transition_evidence),
            "size": len(transition_evidence),
        },
    }


def verify_continuation_binding(
    binding: Mapping[str, Any],
    parent: Path,
    child: Path,
    *,
    transition_evidence: bytes,
) -> dict[str, Any]:
    """Verify structural binding only; do not upgrade it into causal or behavioral proof."""
    if not isinstance(binding, Mapping) or binding.get("schema") != CONTINUATION_BINDING_SCHEMA:
        raise AgentImageError("E_SPEC_INVALID", "Unsupported or malformed continuation binding.")
    evidence = binding.get("transition_evidence")
    if not isinstance(evidence, Mapping):
        raise AgentImageError("E_SPEC_INVALID", "Continuation binding is missing transition evidence metadata.")
    evidence_kind = evidence.get("kind")
    evidence_media_type = evidence.get("media_type")
    if not isinstance(evidence_kind, str) or not evidence_kind:
        raise AgentImageError("E_SPEC_INVALID", "Continuation evidence kind must be a non-empty string.")
    if not isinstance(evidence_media_type, str) or not evidence_media_type:
        raise AgentImageError("E_SPEC_INVALID", "Continuation evidence media type must be a non-empty string.")

    expected = build_continuation_binding(
        parent,
        child,
        transition_evidence=transition_evidence,
        evidence_kind=evidence_kind,
        evidence_media_type=evidence_media_type,
    )
    if dict(binding) != expected:
        raise AgentImageError(
            "E_DIGEST_MISMATCH",
            "Continuation binding does not match the verified parent, child, state delta, or evidence bytes.",
        )
    return {
        "valid": True,
        "schema": CONTINUATION_BINDING_SCHEMA,
        "scope": BINDING_SCOPE,
        "binding_digest": sha256_bytes(canonical_json_bytes(expected)),
        "state_delta_digest": expected["state_delta"]["digest"],
        "transition_evidence_digest": expected["transition_evidence"]["digest"],
        "causal_transition_verified": False,
        "behavioral_retention_verified": False,
    }
