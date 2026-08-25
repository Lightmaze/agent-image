from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_image.errors import AgentImageError
from agent_image.registry import validate_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "v0.1" / "index.json"


def test_checked_in_registry_reconciles_evidence_digests() -> None:
    result = validate_registry(REGISTRY)

    assert result == {
        "valid": True,
        "registry_version": "agent-image-registry/v0.1",
        "entries": 5,
        "evidence_status": {"negative": 1, "unverified": 0, "verified": 4},
        "privacy": {"public": 0, "private": 5, "unknown": 0},
        "source_harnesses": {"dsh": 1, "hermes": 2, "openclaw": 1, "vharness": 1},
        "artifact_digests_unique": True,
        "evidence_digests_verified": True,
    }


def test_registry_evidence_digest_drift_fails(tmp_path: Path) -> None:
    value = json.loads(REGISTRY.read_text(encoding="utf-8"))
    value["entries"][0]["evidence"]["digest"] = "sha256:" + "0" * 64
    candidate = tmp_path / "registry.json"
    candidate.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(AgentImageError) as caught:
        validate_registry(candidate, repository_root=ROOT)

    assert caught.value.code == "E_REGISTRY_INVALID"
    assert "digest mismatch" in caught.value.message


def test_registry_portability_cannot_exceed_evidence(tmp_path: Path) -> None:
    value = json.loads(REGISTRY.read_text(encoding="utf-8"))
    value["entries"][0]["portability"]["level"] = "P3"
    candidate = tmp_path / "registry.json"
    candidate.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(AgentImageError) as caught:
        validate_registry(candidate, repository_root=ROOT)

    assert caught.value.code == "E_REGISTRY_INVALID"
    assert "exceeds verified evidence" in caught.value.message


def test_registry_rejects_non_public_publishable_entry(tmp_path: Path) -> None:
    value = json.loads(REGISTRY.read_text(encoding="utf-8"))
    value["entries"][0]["privacy"]["distribution"] = "publishable"
    candidate = tmp_path / "registry.json"
    candidate.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(AgentImageError) as caught:
        validate_registry(candidate, repository_root=ROOT)

    assert caught.value.code == "E_REGISTRY_INVALID"
    assert "cannot publish" in caught.value.message
