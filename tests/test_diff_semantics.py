from __future__ import annotations

from pathlib import Path

from agent_image.adapter_contract import AdapterExport
from agent_image.canonical import sha256_bytes
from agent_image.image_archive import diff_images, layer_root_digest, publish_image


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
        "source": {"path": path.split("/", 2)[-1], "origin": origin, "reason": "synthetic diff regression"},
    }


def _write_image(path: Path, *, origin: str, identity_payload: bytes, memory_payload: bytes) -> None:
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
            "name": "synthetic-diff",
            "version": "1",
            "created_at": "2026-09-21T12:00:00Z",
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
            {"id": layer["id"], "action": "preserved", "reason": "synthetic diff regression"}
            for layer in layers
        ],
    }
    publish_image(AdapterExport(manifest=manifest, payloads=payloads, source_report=report), path)


def test_diff_separates_origin_only_change_from_payload_state_change(tmp_path: Path) -> None:
    before = tmp_path / "before.aimg"
    after = tmp_path / "after.aimg"
    _write_image(
        before,
        origin="synthetic:parent",
        identity_payload=b"stable identity\n",
        memory_payload=b"parent memory\n",
    )
    _write_image(
        after,
        origin="synthetic:child",
        identity_payload=b"stable identity\n",
        memory_payload=b"parent memory\nchild memory\n",
    )

    result = diff_images(before, after)

    assert result["layers"]["added"] == []
    assert result["layers"]["removed"] == []
    assert result["layers"]["changed"] == ["identity-main", "memory-main"]
    assert result["layers"]["state_changed"] == ["memory-main"]
    assert result["layers"]["metadata_changed"] == ["identity-main"]
    assert result["layer_state_projection"] == {
        "version": "agent-image-layer-state-projection/v0.1",
        "fields": ["kind", "media_type", "digest", "size"],
    }


def test_legacy_changed_remains_union_of_state_and_metadata_changes(tmp_path: Path) -> None:
    before = tmp_path / "before.aimg"
    after = tmp_path / "after.aimg"
    _write_image(
        before,
        origin="synthetic:parent",
        identity_payload=b"stable identity\n",
        memory_payload=b"parent memory\n",
    )
    _write_image(
        after,
        origin="synthetic:child",
        identity_payload=b"stable identity\n",
        memory_payload=b"parent memory\nchild memory\n",
    )

    layers = diff_images(before, after)["layers"]

    assert set(layers["state_changed"]).isdisjoint(layers["metadata_changed"])
    assert set(layers["changed"]) == set(layers["state_changed"]) | set(layers["metadata_changed"])
