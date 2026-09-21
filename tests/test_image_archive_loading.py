"""Synthetic archive I/O regressions; no real harness, home, or credentials."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_image.adapter_contract import AdapterExport
from agent_image.canonical import pretty_json_bytes, sha256_bytes
from agent_image.container import pack_entries, read_entries
from agent_image.errors import AgentImageError
from agent_image import image_archive
from agent_image.manifest import dump_yaml, load_yaml_bytes


PAYLOAD = "layers/memory/learned.txt"


def _write_image(path: Path, *, name: str = "original", data: bytes = b"learned-state\n") -> Path:
    layer = {
        "id": "memory-main", "kind": "memory", "media_type": "text/plain",
        "path": PAYLOAD, "digest": sha256_bytes(data), "size": len(data),
        "privacy": "public", "portability": "portable",
    }
    manifest = {
        "spec": "agent-image/v0.1",
        "image": {
            "name": name, "version": "1", "created_at": "2026-09-21T00:00:00Z",
            "digest": image_archive.layer_root_digest([layer]),
        },
        "layers": [layer],
        "privacy": {"default": "private", "public_build": True, "unresolved_items": 0},
        "provenance": {
            "source_harness": "synthetic-test", "source_adapter": "synthetic-test",
            "export_tool_version": "0.1.0-alpha.2",
        },
    }
    report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "export", "inventory_count": 1,
        "outcomes": [{"id": "memory-main", "action": "preserved", "reason": "synthetic test"}],
    }
    image_archive.publish_image(AdapterExport(manifest, {PAYLOAD: data}, report), path)
    return path


def _refresh_checksums(entries: dict[str, bytes]) -> None:
    entries.pop("meta/checksums.txt", None)
    entries["meta/checksums.txt"] = (
        "\n".join(f"{sha256_bytes(data)[7:]}  {path}" for path, data in sorted(entries.items())) + "\n"
    ).encode("utf-8")


def _swap_after_read(monkeypatch: pytest.MonkeyPatch, source: Path, replacement: Path) -> list[Path]:
    """Replace a real pathname after the first archive has been fully read."""
    calls: list[Path] = []
    original_read = image_archive.read_entries

    def read_then_replace(path: Path) -> dict[str, bytes]:
        entries = original_read(path)
        calls.append(path)
        if path == source and replacement.exists():
            replacement.replace(source)
        return entries

    monkeypatch.setattr(image_archive, "read_entries", read_then_replace)
    return calls


@pytest.mark.parametrize("valid_replacement", [False, True])
def test_load_returns_exactly_the_entries_it_verified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, valid_replacement: bool) -> None:
    source = _write_image(tmp_path / "source.aimg")
    replacement = _write_image(tmp_path / "replacement.aimg", name="replacement", data=b"other-state\n")
    expected = read_entries(source)
    if not valid_replacement:
        entries = read_entries(replacement)
        entries[PAYLOAD] = b"changed-without-updating-digests\n"
        replacement.unlink()
        pack_entries(entries, replacement)
    calls = _swap_after_read(monkeypatch, source, replacement)

    document = image_archive.load_image(source)

    assert document.entries == expected
    assert document.manifest["image"]["name"] == "original"
    assert calls == [source]
    assert read_entries(source)[PAYLOAD] != expected[PAYLOAD]


def test_inspect_keeps_the_verified_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _write_image(tmp_path / "source.aimg")
    replacement = _write_image(tmp_path / "replacement.aimg", name="replacement")
    calls = _swap_after_read(monkeypatch, source, replacement)

    result = image_archive.inspect_image(source)

    assert result["image"]["name"] == "original"
    assert calls == [source]


def test_redact_keeps_the_verified_payloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _write_image(tmp_path / "source.aimg")
    replacement = _write_image(tmp_path / "replacement.aimg", name="replacement", data=b"other-state\n")
    calls = _swap_after_read(monkeypatch, source, replacement)
    output = tmp_path / "public.aimg"

    image_archive.redact_image(source, output)

    assert read_entries(output)[PAYLOAD] == b"learned-state\n"
    assert calls.count(source) == 1


@pytest.mark.parametrize("operation", ["load", "verify"])
@pytest.mark.parametrize(
    ("damage", "expected_code"),
    [
        ("missing_control", "E_IMAGE_CORRUPT"),
        ("undeclared_payload", "E_IMAGE_CORRUPT"),
        ("missing_payload", "E_IMAGE_CORRUPT"),
        ("checksum", "E_DIGEST_MISMATCH"),
        ("spec", "E_SPEC_INVALID"),
        ("index_json", "E_IMAGE_CORRUPT"),
        ("index_entries", "E_IMAGE_CORRUPT"),
        ("payload_digest", "E_DIGEST_MISMATCH"),
        ("image_digest", "E_DIGEST_MISMATCH"),
        ("public_privacy", "E_IMAGE_CORRUPT"),
        ("unresolved_count", "E_IMAGE_CORRUPT"),
        ("secret_privacy", "E_SECRET_DETECTED"),
        ("report_json", "E_IMAGE_CORRUPT"),
        ("report_count", "E_IMAGE_CORRUPT"),
    ],
)
def test_load_and_verify_share_all_validation_gates(tmp_path: Path, operation: str, damage: str, expected_code: str) -> None:
    source = _write_image(tmp_path / "source.aimg")
    entries = read_entries(source)
    manifest = load_yaml_bytes(entries["manifest.yaml"])
    if damage == "missing_control":
        del entries["index.json"]
    elif damage == "undeclared_payload":
        entries["layers/other/undeclared.txt"] = b"extra"
    elif damage == "missing_payload":
        del entries[PAYLOAD]
    elif damage in {"checksum", "payload_digest"}:
        entries[PAYLOAD] = b"tampered"
    elif damage == "spec":
        manifest["spec"] = "agent-image/unsupported"
    elif damage == "index_json":
        entries["index.json"] = b"{"
    elif damage == "index_entries":
        index = json.loads(entries["index.json"])
        index["entries"] = []
        entries["index.json"] = pretty_json_bytes(index)
    elif damage == "image_digest":
        manifest["image"]["digest"] = "sha256:" + "0" * 64
    elif damage == "public_privacy":
        manifest["layers"][0]["privacy"] = "private"
    elif damage == "unresolved_count":
        manifest["privacy"]["unresolved_items"] = 1
    elif damage == "secret_privacy":
        manifest["layers"][0]["privacy"] = "secret"
    elif damage == "report_json":
        entries["meta/source-report.json"] = b"{"
    elif damage == "report_count":
        report = json.loads(entries["meta/source-report.json"])
        report["inventory_count"] = 2
        entries["meta/source-report.json"] = pretty_json_bytes(report)
    entries["manifest.yaml"] = dump_yaml(manifest)
    if damage != "checksum":
        _refresh_checksums(entries)
    damaged = tmp_path / "damaged.aimg"
    pack_entries(entries, damaged)

    reader = image_archive.load_image if operation == "load" else image_archive.verify_image
    with pytest.raises(AgentImageError) as error:
        reader(damaged)
    assert error.value.code == expected_code


def test_verify_receipt_and_published_v01_identity_contract_stay_unchanged(tmp_path: Path) -> None:
    source = _write_image(tmp_path / "source.aimg")
    document = image_archive.load_image(source)
    layers = document.manifest["layers"]
    assert set(document.entries) == {
        "manifest.yaml", "index.json", "meta/checksums.txt", "meta/source-report.json", PAYLOAD,
    }
    assert image_archive.verify_image(source) == {
        "valid": True, "spec": "agent-image/v0.1",
        "image_digest": image_archive.layer_root_digest(layers), "layers": 1,
    }
    # v0.1 intentionally uses a layer root, not full-manifest/JCS identity.
    renamed = _write_image(tmp_path / "renamed.aimg", name="different-metadata")
    assert image_archive.verify_image(renamed)["image_digest"] == document.manifest["image"]["digest"]
    assert renamed.read_bytes() != source.read_bytes()
