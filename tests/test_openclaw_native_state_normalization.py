from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path

from agent_image.adapter_contract import AdapterExport
from agent_image.adapters.openclaw import (
    OPENCLAW_NATIVE_MEDIA_TYPE,
    OPENCLAW_PIN,
    OpenClawAdapter,
    OpenClawAgent,
    _native_archive,
    _read_native_archive,
)
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.formal_service import restore_image
from agent_image.image_archive import layer_root_digest, publish_image


class _FakeOpenClawCLI:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.agents: dict[str, OpenClawAgent] = {}

    def version(self) -> str:
        return OPENCLAW_PIN.version

    def list_agents(self) -> list[OpenClawAgent]:
        return list(self.agents.values())

    def show_agent(self, name: str) -> OpenClawAgent:
        if name not in self.agents:
            from agent_image.errors import AgentImageError

            raise AgentImageError("E_SOURCE_NOT_FOUND", f"OpenClaw agent does not exist: {name}")
        return self.agents[name]

    def target_workspace(self, name: str) -> Path:
        return self.root / "workspaces" / name

    def add_agent(self, name: str, workspace: Path) -> OpenClawAgent:
        from agent_image.errors import AgentImageError

        if name in self.agents:
            raise AgentImageError("E_TARGET_EXISTS", f"OpenClaw target already exists: {name}")
        workspace.mkdir(parents=True, exist_ok=False)
        agent_dir = self.root / "state" / "agents" / name / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        agent = OpenClawAgent(id=name, workspace=workspace, agent_dir=agent_dir)
        self.agents[name] = agent
        return agent

    def delete_agent(self, name: str) -> None:
        self.agents.pop(name, None)


def _legacy_native_archive(source_agent: str, entries: dict[str, bytes]) -> bytes:
    values = dict(entries)
    values["meta/agent.json"] = canonical_json_bytes(
        {"source_agent": source_agent, "contract": OPENCLAW_PIN.tag}
    )
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(values):
                data = values[path]
                info = tarfile.TarInfo(name=path)
                info.size = len(data)
                info.mtime = 0
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


def test_new_openclaw_native_writer_contains_only_restorable_state() -> None:
    entries = {
        "workspace/MEMORY.md": b"Synthetic memory.\n",
        "agent/runtime.json": b'{"mode":"synthetic"}\n',
    }

    native = _native_archive(entries)
    decoded = _read_native_archive(native)

    assert decoded == entries
    assert "meta/agent.json" not in decoded


def test_legacy_openclaw_native_metadata_remains_restorable(tmp_path: Path) -> None:
    native_entries = {
        "workspace/MEMORY.md": b"Legacy synthetic memory.\n",
        "agent/runtime.json": b'{"mode":"legacy"}\n',
    }
    native = _legacy_native_archive("legacy-source", native_entries)
    assert "meta/agent.json" in _read_native_archive(native)

    native_path = "layers/native/openclaw-agent.tar.gz"
    layer = {
        "id": "openclaw-native-agent",
        "kind": "native",
        "media_type": OPENCLAW_NATIVE_MEDIA_TYPE,
        "path": native_path,
        "digest": sha256_bytes(native),
        "size": len(native),
        "privacy": "private",
        "portability": "opaque",
        "source": {
            "origin": "openclaw:legacy-source",
            "reason": "legacy OpenClaw native fixture with producer metadata",
        },
    }
    manifest = {
        "spec": "agent-image/v0.1",
        "image": {
            "name": "legacy-source",
            "version": "0.1.0",
            "created_at": "2026-09-22T00:00:00Z",
            "digest": layer_root_digest([layer]),
        },
        "runtime": {
            "harness": {"id": "openclaw", "version": OPENCLAW_PIN.version},
            "adapter": {"id": "org.agentimage.openclaw", "version": "0.1.0"},
        },
        "layers": [layer],
        "privacy": {"default": "private", "public_build": False, "unresolved_items": 0},
        "provenance": {
            "source_harness": "openclaw",
            "source_adapter": "org.agentimage.openclaw",
            "export_tool_version": "0.1.0-alpha.2",
            "source_uri": "openclaw:legacy-source",
        },
    }
    source_report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "build",
        "adapter": {"id": "org.agentimage.openclaw", "version": "0.1.0"},
        "inventory_count": 3,
        "outcomes": [
            {
                "id": "registration",
                "source": "registration/legacy-source",
                "action": "transformed",
                "reason": "registration recreated through CLI",
            },
            {
                "id": "memory",
                "source": "workspace/MEMORY.md",
                "action": "preserved",
                "reason": "legacy native state",
            },
            {
                "id": "runtime",
                "source": "agent/runtime.json",
                "action": "preserved",
                "reason": "legacy native state",
            },
        ],
    }
    image = tmp_path / "legacy.aimg"
    publish_image(AdapterExport(manifest=manifest, payloads={native_path: native}, source_report=source_report), image)

    cli = _FakeOpenClawCLI(tmp_path / "host")
    report = restore_image(OpenClawAdapter(cli), image=image, target="restored")

    assert report["validated"] is True
    assert report["portability"] == "P1"
    restored = cli.show_agent("restored")
    assert (restored.workspace / "MEMORY.md").read_bytes() == native_entries["workspace/MEMORY.md"]
    assert (restored.agent_dir / "runtime.json").read_bytes() == native_entries["agent/runtime.json"]
    assert not (restored.workspace / "meta" / "agent.json").exists()
