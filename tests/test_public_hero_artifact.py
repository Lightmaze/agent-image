from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_image.adapter_contract import AdapterExport
from agent_image.adapters.hermes import HERMES_NATIVE_MEDIA_TYPE, HERMES_PIN, HermesAdapter, HermesProfile, _normalized_snapshot, _safe_snapshot
from agent_image.canonical import sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import layer_root_digest, load_image, publish_image
from experiments.situated_negotiation_ground.public_artifact import (
    PUBLIC_NATIVE_PATHS,
    build_public_hero_image,
)


class RestoreOnlyHermesCLI:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.profiles: dict[str, Path] = {}

    def version(self) -> str:
        return HERMES_PIN.version

    def show_profile(self, name: str) -> HermesProfile:
        if name not in self.profiles:
            raise AgentImageError("E_SOURCE_NOT_FOUND", f"Missing profile: {name}")
        return HermesProfile(name=name, path=self.profiles[name])

    def import_profile(self, archive: Path, name: str) -> HermesProfile:
        if name in self.profiles:
            raise AgentImageError("E_TARGET_EXISTS", f"Existing profile: {name}")
        _, entries = _safe_snapshot(archive.read_bytes())
        target = self.root / name
        for relative, data in entries.items():
            path = target / Path(*relative.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.profiles[name] = target
        return HermesProfile(name=name, path=target)

    def delete_profile(self, name: str) -> None:
        self.profiles.pop(name, None)


def _layer(path: str, kind: str, data: bytes, *, layer_id: str) -> dict[str, object]:
    relative_source = path.split(f"/{kind}/", 1)[1]
    return {
        "id": layer_id,
        "kind": kind,
        "media_type": "application/x-ndjson" if path.endswith(".jsonl") else "application/json" if path.endswith(".json") else "text/markdown",
        "path": path,
        "digest": sha256_bytes(data),
        "size": len(data),
        "privacy": "private",
        "portability": "portable",
        "source": {"path": relative_source, "origin": "hermes:trained", "reason": "synthetic fixture"},
    }


def _private_source(tmp_path: Path) -> tuple[Path, str]:
    payloads = {
        "layers/identity/SOUL.md": b"# Synthetic procurement agent\n",
        "layers/memory/memories/MEMORY.md": b"# Learned playbook\nUse cohort evidence.\n",
        "layers/experience/sessions/situated-training-ground.jsonl": b'{"episode":1,"synthetic":true}\n',
        "layers/experience/sessions/situated-consolidations.jsonl": b'{"block":1,"synthetic":true}\n',
        "layers/development/situated-development-index.json": b'{"privacy":"private","entries":[]}\n',
        "layers/evaluation/situated-evidence-index.json": b'{"privacy":"private","entries":[]}\n',
    }
    layers = [
        _layer(path, "identity" if "/identity/" in path else "memory" if "/memory/" in path else "experience" if "/experience/" in path else "development" if "/development/" in path else "evaluation", data, layer_id=f"layer-{index}")
        for index, (path, data) in enumerate(sorted(payloads.items()), start=1)
    ]
    native_entries = {
        ".no-bundled-skills": b"\n",
        "SOUL.md": payloads["layers/identity/SOUL.md"],
        "config.yaml": b"model:\n  provider: deepseek\n  default: deepseek-v4-flash\n",
        "memories/MEMORY.md": payloads["layers/memory/memories/MEMORY.md"],
        "sessions/situated-training-ground.jsonl": payloads["layers/experience/sessions/situated-training-ground.jsonl"],
        "sessions/situated-consolidations.jsonl": payloads["layers/experience/sessions/situated-consolidations.jsonl"],
        "cache/model.json": b'{"models":[]}\n',
        "logs/agent.log": b"synthetic log\n",
        "state.db": b"opaque runtime state",
        "auth.lock": b"\n",
    }
    native = _normalized_snapshot("trained", native_entries)
    native_path = "layers/native/hermes-profile.tar.gz"
    payloads[native_path] = native
    layers.append(
        {
            "id": "hermes-native-profile",
            "kind": "native",
            "media_type": HERMES_NATIVE_MEDIA_TYPE,
            "path": native_path,
            "digest": sha256_bytes(native),
            "size": len(native),
            "privacy": "private",
            "portability": "opaque",
        }
    )
    manifest = {
        "spec": "agent-image/v0.1",
        "image": {
            "name": "trained",
            "version": "0.1.0",
            "created_at": "2026-08-25T19:12:54Z",
            "digest": layer_root_digest(layers),
        },
        "runtime": {
            "harness": {"id": "hermes", "version": HERMES_PIN.version},
            "adapter": {"id": "org.agentimage.hermes", "version": "0.1.0"},
            "model": {"provider": "deepseek", "id": "deepseek-v4-flash"},
        },
        "layers": sorted(layers, key=lambda item: str(item["path"])),
        "lineage": {"parent": {"digest": f"sha256:{'1' * 64}"}},
        "privacy": {"default": "private", "public_build": False, "unresolved_items": 0},
        "provenance": {
            "source_harness": "hermes",
            "source_adapter": "org.agentimage.hermes",
            "export_tool_version": "0.1.0-beta.1",
        },
    }
    report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "build",
        "inventory_count": 1,
        "outcomes": [{"id": "source", "action": "preserved", "reason": "synthetic fixture"}],
    }
    source = tmp_path / "trained.aimg"
    publish_image(AdapterExport(manifest=manifest, payloads=payloads, source_report=report), source)
    return source, str(manifest["image"]["digest"])


def _evidence(tmp_path: Path, *, secret: bool = False) -> tuple[Path, str]:
    value = {
        "scores": {"before": 0.4, "trained": 0.9, "fresh_restored": 0.9},
        "synthetic": True,
    }
    if secret:
        value["api_key"] = "must-fail"
    path = tmp_path / "evidence.json"
    data = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    return path, sha256_bytes(data)


def test_curator_builds_public_minimal_native_image_and_restores(tmp_path: Path) -> None:
    source, source_digest = _private_source(tmp_path)
    evidence, evidence_digest = _evidence(tmp_path)
    output = tmp_path / "procurement-negotiator-v1.aimg"

    result = build_public_hero_image(
        source,
        evidence,
        output,
        expected_source_digest=source_digest,
        expected_evidence_digest=evidence_digest,
    )

    assert result["verified"] is True
    assert result["native_members"] == sorted(PUBLIC_NATIVE_PATHS)
    document = load_image(output)
    assert document.manifest["privacy"] == {"default": "private", "public_build": True, "unresolved_items": 0}
    assert all(layer["privacy"] == "public" for layer in document.manifest["layers"])
    assert document.manifest["lineage"]["parent"] == {"digest": source_digest}
    assert "parents" not in document.manifest["lineage"]
    assert document.manifest["development"]["evidence"][0]["kind"] == "log"
    assert document.manifest["evaluations"][0]["before"] == {"score": 0.4}
    assert document.manifest["evaluations"][0]["after"] == {"score": 0.9}
    assert "meta/redaction-report.json" in document.entries
    native_layer = next(layer for layer in document.manifest["layers"] if layer["kind"] == "native")
    _, native_entries = _safe_snapshot(document.entries[native_layer["path"]])
    assert set(native_entries) == PUBLIC_NATIVE_PATHS
    assert "state.db" not in native_entries
    assert not any(path.startswith(("cache/", "logs/")) for path in native_entries)

    cli = RestoreOnlyHermesCLI(tmp_path / "profiles")
    restore = HermesAdapter(cli).native_restore(document, "restored")
    assert restore["validated"] is True
    outcomes = {item["id"]: item["action"] for item in restore["outcomes"]}
    assert outcomes["layer-1"] == "unsupported"
    assert outcomes["layer-3"] == "preserved"
    assert outcomes["layer-4"] == "preserved"
    assert outcomes["layer-5"] == "preserved"
    assert outcomes["layer-6"] == "preserved"
    assert outcomes["situated-gate-e-public-evidence"] == "unsupported"
    assert outcomes["hermes-native-profile"] == "preserved"
    assert set(path.relative_to(cli.profiles["restored"]).as_posix() for path in cli.profiles["restored"].rglob("*") if path.is_file()) == PUBLIC_NATIVE_PATHS


def test_curator_rejects_unpinned_source(tmp_path: Path) -> None:
    source, _ = _private_source(tmp_path)
    evidence, evidence_digest = _evidence(tmp_path)
    with pytest.raises(AgentImageError) as caught:
        build_public_hero_image(
            source,
            evidence,
            tmp_path / "out.aimg",
            expected_source_digest=f"sha256:{'f' * 64}",
            expected_evidence_digest=evidence_digest,
        )
    assert caught.value.code == "E_SOURCE_UNSUPPORTED"


def test_curator_fails_closed_on_structured_secret(tmp_path: Path) -> None:
    source, source_digest = _private_source(tmp_path)
    evidence, evidence_digest = _evidence(tmp_path, secret=True)
    output = tmp_path / "out.aimg"
    with pytest.raises(AgentImageError) as caught:
        build_public_hero_image(
            source,
            evidence,
            output,
            expected_source_digest=source_digest,
            expected_evidence_digest=evidence_digest,
        )
    assert caught.value.code == "E_SECRET_DETECTED"
    assert not output.exists()
