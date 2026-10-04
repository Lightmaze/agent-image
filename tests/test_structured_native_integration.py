from __future__ import annotations

import io
import tarfile

import pytest

from agent_image.adapter_contract import AdapterExport
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.native_capsule import inspect_native_capsule_bytes
from agent_image.native_export_planner import (
    NATIVE_CAPSULE_MEDIA_TYPE,
    finalize_structured_native_export,
)
from agent_image.structured_native import verify_structured_native_layer


def _pack(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name in sorted(entries):
            data = entries[name]
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _capsule() -> bytes:
    a = b"public-state\n"
    b = b"private-state\n"
    index = {
        "spec": "agent-image-native-capsule/v0.1",
        "profile": {"id": "test.profile", "version": "1"},
        "capture": {
            "captured_at": "2026-10-04T19:00:00Z",
            "consistency": "flush-only",
            "write_barrier": False,
            "flushed": True,
            "history_fidelity": "raw-append-log",
            "source_mutation": "flush-only",
        },
        "authoritative": [
            {
                "id": "a",
                "path": "authoritative/a.txt",
                "media_type": "text/plain",
                "digest": sha256_bytes(a),
                "size": len(a),
                "privacy": "public",
            },
            {
                "id": "b",
                "path": "authoritative/b.txt",
                "media_type": "text/plain",
                "digest": sha256_bytes(b),
                "size": len(b),
                "privacy": "private",
            },
        ],
        "derived": [],
        "external_references": [],
        "receiver": {
            "authority_rebind_required": True,
            "secrets_embedded": False,
            "requirements": [],
        },
        "closure": {"policy": "whole-store", "checks": []},
        "compatibility": {
            "native_restore": "exact-authoritative",
            "retrieval": "structural-restore-only",
            "history": "audit-complete",
            "loss_report_required": True,
        },
    }
    return _pack(
        {
            "capsule.json": canonical_json_bytes(index) + b"\n",
            "authoritative/a.txt": a,
            "authoritative/b.txt": b,
        }
    )


def _export(payload: bytes, *, portability: str = "adapter-specific") -> AdapterExport:
    layer = {
        "id": "native",
        "kind": "native",
        "media_type": NATIVE_CAPSULE_MEDIA_TYPE,
        "path": "layers/native.tar",
        "digest": sha256_bytes(payload),
        "size": len(payload),
        "privacy": "unknown",
        "portability": portability,
    }
    return AdapterExport(
        manifest={
            "image": {"digest": "sha256:" + "0" * 64},
            "layers": [layer],
            "privacy": {"public_build": False, "unresolved_items": 1},
        },
        payloads={"layers/native.tar": payload},
        source_report={"report_version": "agent-image-operation-report/v0.1"},
    )


def test_private_finalization_promotes_atomic_mixed_privacy_without_rewriting_payload_objects():
    raw = _capsule()
    before = inspect_native_capsule_bytes(raw)
    finalized = finalize_structured_native_export(_export(raw), policy="private")
    layer = finalized.manifest["layers"][0]
    assert layer["privacy"] == "private"
    after = inspect_native_capsule_bytes(finalized.payloads[layer["path"]])
    assert set(item["privacy"] for item in after.index["authoritative"]) == {"private"}
    assert after.authoritative == before.authoritative
    summary = verify_structured_native_layer(layer, finalized.payloads[layer["path"]])
    assert summary is not None
    assert summary["profile"] == {"id": "test.profile", "version": "1"}


def test_public_finalization_removes_nonpublic_atomic_native_unit():
    finalized = finalize_structured_native_export(_export(_capsule()), policy="public")
    assert finalized.manifest["layers"] == []
    assert finalized.payloads == {}
    audit = finalized.source_report["native_privacy_planning"]["units"][0]
    assert audit["action"] == "redact-whole"
    assert audit["public_subset_requires_profile_projection"] is True


def test_structured_native_requires_adapter_specific_portability():
    with pytest.raises(AgentImageError):
        finalize_structured_native_export(_export(_capsule(), portability="portable"), policy="private")
