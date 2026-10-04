from __future__ import annotations

import io
import json
import tarfile

import pytest

from agent_image.canonical import sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.native_capsule import inspect_native_capsule_bytes
from agent_image.native_realization import (
    NATIVE_REALIZATION_MEDIA_TYPE,
    NATIVE_REALIZATION_SPEC,
    NativeRealizationError,
    parse_native_realization_bytes,
)


def _realization(*, profile=None, identity=None, kind="retrieval") -> bytes:
    value = {
        "spec": NATIVE_REALIZATION_SPEC,
        "kind": kind,
        "profile": profile or {"id": "test.backend", "version": "1"},
        "identity": identity or {
            "implementation": "test.retrieval",
            "vector_dim": 64,
            "metric": "cosine",
            "query_encoder": "hashing/v1",
        },
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _authoritative(object_id: str, data: bytes) -> tuple[dict, tuple[str, bytes]]:
    path = f"authoritative/{object_id}.jsonl"
    return ({
        "id": object_id,
        "path": path,
        "media_type": "application/jsonl",
        "digest": sha256_bytes(data),
        "size": len(data),
        "privacy": "private",
    }, (path, data))


def _derived_payload(
    object_id: str,
    path: str,
    media_type: str,
    data: bytes,
    *,
    policy="not-rebuildable",
    source_ids=None,
    realization_ref=None,
) -> tuple[dict, tuple[str, bytes]]:
    rebuild = {"policy": policy, "source_ids": list(source_ids or [])}
    if realization_ref is not None:
        rebuild["realization_ref"] = realization_ref
    return ({
        "id": object_id,
        "path": path,
        "media_type": media_type,
        "digest": sha256_bytes(data),
        "size": len(data),
        "privacy": "private",
        "rebuild": rebuild,
    }, (path, data))


def _omitted_derived(object_id: str, *, source_ids, realization_ref=None) -> dict:
    rebuild = {"policy": "omit-and-rebuild", "source_ids": list(source_ids)}
    if realization_ref is not None:
        rebuild["realization_ref"] = realization_ref
    return {"id": object_id, "rebuild": rebuild}


def _index(authoritative, derived):
    return {
        "spec": "agent-image-native-capsule/v0.1",
        "profile": {"id": "test.backend", "version": "1"},
        "capture": {
            "captured_at": "2026-10-03T19:00:00Z",
            "consistency": "quiesced",
            "write_barrier": True,
            "flushed": True,
            "history_fidelity": "snapshot-current-state",
            "source_mutation": "none",
        },
        "authoritative": authoritative,
        "derived": derived,
        "external_references": [],
        "receiver": {
            "authority_rebind_required": True,
            "secrets_embedded": False,
            "requirements": [],
        },
        "closure": {"policy": "whole-store", "checks": []},
        "compatibility": {
            "native_restore": "exact-authoritative",
            "retrieval": "retrieval-compatible",
            "history": "current-state-only",
            "loss_report_required": True,
        },
    }


def _capsule(index: dict, payloads: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    entries = {
        "capsule.json": json.dumps(
            index, sort_keys=True, separators=(",", ":")
        ).encode() + b"\n"
    }
    entries.update(dict(payloads))
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for path, data in sorted(entries.items()):
            info = tarfile.TarInfo(path)
            info.size = len(data)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _valid_fixture():
    auth, auth_payload = _authoritative(
        "nodes", b'{"node_id":"n1","embedding":null}\n'
    )
    realization_bytes = _realization()
    realization, realization_payload = _derived_payload(
        "retrieval-realization",
        "derived/retrieval-realization.json",
        NATIVE_REALIZATION_MEDIA_TYPE,
        realization_bytes,
        policy="not-rebuildable",
    )
    index_obj = _omitted_derived(
        "retrieval-index",
        source_ids=["nodes"],
        realization_ref="retrieval-realization",
    )
    return _index([auth], [realization, index_obj]), [
        auth_payload,
        realization_payload,
    ]


def test_valid_omitted_index_binds_preserved_realization_sidecar():
    index, payloads = _valid_fixture()
    doc = inspect_native_capsule_bytes(_capsule(index, payloads))
    assert (
        doc.index["derived"][1]["rebuild"]["realization_ref"]
        == "retrieval-realization"
    )
    parsed = parse_native_realization_bytes(
        doc.derived["retrieval-realization"]
    )
    assert parsed["identity"]["vector_dim"] == 64


def test_dangling_realization_ref_is_rejected():
    index, payloads = _valid_fixture()
    index["derived"][1]["rebuild"]["realization_ref"] = "missing"
    with pytest.raises(AgentImageError) as error:
        inspect_native_capsule_bytes(_capsule(index, payloads))
    assert error.value.code == "E_SPEC_INVALID"
    assert "dangling realization_ref" in error.value.message


def test_realization_ref_must_target_realization_media_type():
    index, payloads = _valid_fixture()
    index["derived"][0]["media_type"] = "application/json"
    with pytest.raises(AgentImageError) as error:
        inspect_native_capsule_bytes(_capsule(index, payloads))
    assert "must target media type" in error.value.message


def test_realization_sidecar_must_be_terminal_not_rebuildable():
    index, payloads = _valid_fixture()
    index["derived"][0]["rebuild"]["policy"] = "preserve-sidecar"
    with pytest.raises(AgentImageError) as error:
        inspect_native_capsule_bytes(_capsule(index, payloads))
    assert "must use rebuild.policy=not-rebuildable" in error.value.message


def test_realization_profile_must_match_capsule_profile():
    index, payloads = _valid_fixture()
    bad = _realization(profile={"id": "other.backend", "version": "1"})
    target = index["derived"][0]
    target["digest"] = sha256_bytes(bad)
    target["size"] = len(bad)
    payloads = [
        (p, bad if p == target["path"] else d)
        for p, d in payloads
    ]
    with pytest.raises(AgentImageError) as error:
        inspect_native_capsule_bytes(_capsule(index, payloads))
    assert error.value.code == "E_SPEC_INVALID"
    assert "profile mismatch" in error.value.message


def test_realization_payload_tamper_is_digest_failure():
    index, payloads = _valid_fixture()
    target_path = index["derived"][0]["path"]
    payloads = [
        (p, d + b"x" if p == target_path else d)
        for p, d in payloads
    ]
    with pytest.raises(AgentImageError) as error:
        inspect_native_capsule_bytes(_capsule(index, payloads))
    assert error.value.code == "E_DIGEST_MISMATCH"


def test_realization_duplicate_json_key_is_rejected_after_digest_validation():
    index, payloads = _valid_fixture()
    bad = b'{"spec":"agent-image-native-realization/v0.1","kind":"retrieval","kind":"index","profile":{"id":"test.backend","version":"1"},"identity":{"x":1}}\n'
    target = index["derived"][0]
    target["digest"] = sha256_bytes(bad)
    target["size"] = len(bad)
    payloads = [
        (p, bad if p == target["path"] else d)
        for p, d in payloads
    ]
    with pytest.raises(AgentImageError) as error:
        inspect_native_capsule_bytes(_capsule(index, payloads))
    assert error.value.code == "E_SPEC_INVALID"
    assert "duplicate JSON object key" in error.value.message


def test_legacy_derived_object_without_realization_ref_remains_valid():
    index, payloads = _valid_fixture()
    index["derived"] = [
        index["derived"][0],
        _omitted_derived("cheap-cache", source_ids=["nodes"]),
    ]
    doc = inspect_native_capsule_bytes(_capsule(index, payloads))
    assert doc.index["derived"][1]["id"] == "cheap-cache"


def test_realization_envelope_rejects_unknown_top_level_fields():
    value = json.loads(_realization())
    value["token"] = "nope"
    with pytest.raises(NativeRealizationError):
        parse_native_realization_bytes(json.dumps(value).encode())
