from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_image.adapter_contract import AdapterExport
from agent_image.adapters.openclaw import (
    OPENCLAW_PIN,
    OpenClawAdapter,
    OpenClawAgent,
    SubprocessOpenClawCLI,
)
from agent_image.canonical import sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import layer_root_digest, load_image, publish_image, verify_image


# MOCK_POINT {"id":"MOCK-OPENCLAW-CLI-TEST-001","type":"test_fixture","target":"SubprocessOpenClawCLI against openclaw@2026.7.1-2","replace_by":"before_openclaw_p1_or_p2_capability_claim","owner":"openclaw-adapter","status":"accepted_test_only","production_allowed":false,"reason":"Unit tests need deterministic CLI failure injection; capability evidence is generated separately with the real pinned CLI."}
class FakeOpenClawCLI:
    def __init__(self, root: Path, source: OpenClawAgent | None = None) -> None:
        self.root = root
        self.agents: dict[str, OpenClawAgent] = {}
        if source is not None:
            self.agents[source.id] = source

    def version(self) -> str:
        return OPENCLAW_PIN.version

    def list_agents(self) -> list[OpenClawAgent]:
        return list(self.agents.values())

    def show_agent(self, name: str) -> OpenClawAgent:
        try:
            return self.agents[name]
        except KeyError as error:
            raise AgentImageError("E_SOURCE_NOT_FOUND", f"OpenClaw agent does not exist: {name}") from error

    def target_workspace(self, name: str) -> Path:
        return self.root / "target-workspaces" / name

    def add_agent(self, name: str, workspace: Path) -> OpenClawAgent:
        if name in self.agents:
            raise AgentImageError("E_TARGET_EXISTS", f"OpenClaw target already exists: {name}")
        workspace.mkdir(parents=True, exist_ok=True)
        for filename in ("AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md", "TOOLS.md"):
            path = workspace / filename
            if not path.exists():
                path.write_text(f"seeded {filename}\n", encoding="utf-8")
        agent_dir = self.root / "state" / "agents" / name / "agent"
        agent = OpenClawAgent(id=name, workspace=workspace, agent_dir=agent_dir)
        self.agents[name] = agent
        return agent

    def delete_agent(self, name: str) -> None:
        self.agents.pop(name, None)


class MismatchedTargetOpenClawCLI(FakeOpenClawCLI):
    def show_agent(self, name: str) -> OpenClawAgent:
        agent = super().show_agent(name)
        if name == "broken":
            return OpenClawAgent(id=name, workspace=self.root / "wrong-workspace", agent_dir=agent.agent_dir)
        return agent


@pytest.fixture
def openclaw_source(tmp_path: Path) -> tuple[OpenClawAgent, FakeOpenClawCLI]:
    workspace = tmp_path / "source-workspace"
    (workspace / "skills" / "procurement").mkdir(parents=True)
    (workspace / "memory").mkdir()
    (workspace / ".git").mkdir()
    (workspace / "AGENTS.md").write_text("Protect the principal.\n", encoding="utf-8")
    (workspace / "TOOLS.md").write_text("Use only synthetic tools.\n", encoding="utf-8")
    (workspace / "SOUL.md").write_text("A disciplined procurement agent.\n", encoding="utf-8")
    (workspace / "IDENTITY.md").write_text("# Identity\nName: Source\n", encoding="utf-8")
    (workspace / "USER.md").write_text("Synthetic principal.\n", encoding="utf-8")
    (workspace / "MEMORY.md").write_text("Learned concession discipline.\n", encoding="utf-8")
    (workspace / "memory" / "2026-08-25.md").write_text("Synthetic daily memory.\n", encoding="utf-8")
    (workspace / "skills" / "procurement" / "SKILL.md").write_text("Never disclose limits.\n", encoding="utf-8")
    (workspace / "openclaw-workspace-state.json").write_text('{"version":1}\n', encoding="utf-8")
    (workspace / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    agent_dir = tmp_path / "state" / "agents" / "source" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "runtime.json").write_text('{"mode":"synthetic"}\n', encoding="utf-8")
    sessions = agent_dir.parent / "sessions"
    sessions.mkdir()
    (sessions / "practice.jsonl").write_text('{"event":"practice"}\n', encoding="utf-8")
    source = OpenClawAgent(id="source", workspace=workspace, agent_dir=agent_dir)
    return source, FakeOpenClawCLI(tmp_path, source)


def test_openclaw_private_export_and_native_restore_account_for_all_items(
    openclaw_source: tuple[OpenClawAgent, FakeOpenClawCLI], tmp_path: Path
) -> None:
    source, cli = openclaw_source
    adapter = OpenClawAdapter(cli)
    image = tmp_path / "source.aimg"
    before = adapter.agent_digest(source.id)

    build_image(
        adapter,
        source=source.id,
        output=image,
        policy="private",
        include_experience=True,
        include_workspace=True,
    )

    assert verify_image(image)["valid"] is True
    assert adapter.agent_digest(source.id) == before
    document = load_image(image)
    assert document.manifest["runtime"]["harness"] == {
        "id": "openclaw",
        "version": OPENCLAW_PIN.version,
    }
    assert {layer["kind"] for layer in document.manifest["layers"]} >= {
        "identity",
        "memory",
        "skills",
        "workspace",
        "experience",
        "native",
    }
    source_report = document.json_entry("meta/source-report.json")
    assert source_report["inventory_count"] == len(source_report["outcomes"])
    git_outcome = next(item for item in source_report["outcomes"] if item.get("source") == "workspace/.git/")
    assert git_outcome["action"] == "unsupported"

    restored = restore_image(adapter, image=image, target="restored")

    assert restored["validated"] is True
    assert restored["portability"] == "P1"
    assert restored["inventory_count"] == source_report["inventory_count"]
    assert restored["loss_summary"] == {
        "preserved": source_report["inventory_count"] - 2,
        "transformed": 1,
        "redacted": 0,
        "unsupported": 1,
        "dropped_by_user": 0,
    }
    assert restored["layer_inventory_count"] == len(restored["layer_outcomes"])
    assert restored["layer_loss_summary"]["unsupported"] == 0
    target = cli.show_agent("restored")
    assert (target.workspace / "SOUL.md").read_bytes() == (source.workspace / "SOUL.md").read_bytes()
    assert (target.workspace / "MEMORY.md").read_bytes() == (source.workspace / "MEMORY.md").read_bytes()
    assert (target.workspace / "skills" / "procurement" / "SKILL.md").read_bytes() == (
        source.workspace / "skills" / "procurement" / "SKILL.md"
    ).read_bytes()
    assert (target.agent_dir / "runtime.json").read_bytes() == (source.agent_dir / "runtime.json").read_bytes()
    assert (target.agent_dir.parent / "sessions" / "practice.jsonl").is_file()

    with pytest.raises(AgentImageError) as caught:
        restore_image(adapter, image=image, target="restored")
    assert caught.value.code == "E_TARGET_EXISTS"


def test_openclaw_sessions_are_opt_in_and_secret_state_fails_closed(
    openclaw_source: tuple[OpenClawAgent, FakeOpenClawCLI], tmp_path: Path
) -> None:
    source, cli = openclaw_source
    adapter = OpenClawAdapter(cli)
    image = tmp_path / "default.aimg"
    build_image(adapter, source=source.id, output=image, policy="private")
    document = load_image(image)
    assert all(layer["kind"] != "experience" for layer in document.manifest["layers"])
    session_outcome = next(
        item
        for item in document.json_entry("meta/source-report.json")["outcomes"]
        if item.get("source") == "sessions/practice.jsonl"
    )
    assert session_outcome["action"] == "dropped_by_user"

    (source.agent_dir / "auth-profiles.json").write_text(
        '{"profiles":{"deepseek":{"api_key":"forbidden"}}}\n',
        encoding="utf-8",
    )
    with pytest.raises(AgentImageError) as caught:
        build_image(adapter, source=source.id, output=tmp_path / "secret.aimg", policy="private")
    assert caught.value.code == "E_SECRET_DETECTED"


def test_openclaw_restore_rolls_back_host_registration_and_workspace_on_validation_failure(
    openclaw_source: tuple[OpenClawAgent, FakeOpenClawCLI], tmp_path: Path
) -> None:
    source, _ = openclaw_source
    source_cli = FakeOpenClawCLI(tmp_path / "source-host", source)
    image = tmp_path / "source.aimg"
    build_image(
        OpenClawAdapter(source_cli),
        source=source.id,
        output=image,
        policy="private",
        include_experience=True,
        include_workspace=True,
    )
    target_cli = MismatchedTargetOpenClawCLI(tmp_path / "target-host")

    with pytest.raises(AgentImageError) as caught:
        restore_image(OpenClawAdapter(target_cli), image=image, target="broken")

    assert caught.value.code == "E_NATIVE_INCOMPATIBLE"
    assert "broken" not in target_cli.agents
    assert not target_cli.target_workspace("broken").exists()


def test_subprocess_openclaw_cli_uses_explicit_node_for_windows_npm_shim(tmp_path: Path) -> None:
    shim = tmp_path / "node_modules" / ".bin" / "openclaw.cmd"
    script = tmp_path / "node_modules" / "openclaw" / "openclaw.mjs"
    shim.parent.mkdir(parents=True)
    script.parent.mkdir(parents=True)
    shim.write_text("@echo off\n", encoding="utf-8")
    script.write_text("// official package entry placeholder\n", encoding="utf-8")
    cli = SubprocessOpenClawCLI(binary=str(shim), node_binary="C:/runtime/node.exe")

    assert cli._command(["--version"]) == ["C:/runtime/node.exe", str(script), "--version"]


def _hermes_semantic_image(path: Path) -> Path:
    payloads = {
        "layers/identity/SOUL.md": b"A migrated negotiator.\n",
        "layers/skills/procurement/SKILL.md": b"Protect the reservation price.\n",
        "layers/memory/memories/MEMORY.md": b"Synthetic learned precedent.\n",
        "layers/native/hermes-profile.tar.gz": b"opaque-hermes-state",
    }
    layers = [
        {
            "id": "hermes-identity-soul",
            "kind": "identity",
            "media_type": "text/markdown",
            "path": "layers/identity/SOUL.md",
            "digest": sha256_bytes(payloads["layers/identity/SOUL.md"]),
            "size": len(payloads["layers/identity/SOUL.md"]),
            "privacy": "private",
            "portability": "portable",
            "source": {"path": "SOUL.md", "origin": "hermes:source"},
        },
        {
            "id": "hermes-skills-procurement",
            "kind": "skills",
            "media_type": "text/markdown",
            "path": "layers/skills/procurement/SKILL.md",
            "digest": sha256_bytes(payloads["layers/skills/procurement/SKILL.md"]),
            "size": len(payloads["layers/skills/procurement/SKILL.md"]),
            "privacy": "private",
            "portability": "portable",
            "source": {"path": "skills/procurement/SKILL.md", "origin": "hermes:source"},
        },
        {
            "id": "hermes-memory-main",
            "kind": "memory",
            "media_type": "text/markdown",
            "path": "layers/memory/memories/MEMORY.md",
            "digest": sha256_bytes(payloads["layers/memory/memories/MEMORY.md"]),
            "size": len(payloads["layers/memory/memories/MEMORY.md"]),
            "privacy": "private",
            "portability": "portable",
            "source": {"path": "memories/MEMORY.md", "origin": "hermes:source"},
        },
        {
            "id": "hermes-native",
            "kind": "native",
            "media_type": "application/vnd.hermes-agent.profile.v2026.8.19+tar+gzip",
            "path": "layers/native/hermes-profile.tar.gz",
            "digest": sha256_bytes(payloads["layers/native/hermes-profile.tar.gz"]),
            "size": len(payloads["layers/native/hermes-profile.tar.gz"]),
            "privacy": "private",
            "portability": "opaque",
            "source": {"origin": "hermes:source"},
        },
    ]
    manifest = {
        "spec": "agent-image/v0.1",
        "image": {
            "name": "source",
            "version": "0.1.0",
            "created_at": "2026-08-25T00:00:00Z",
            "digest": layer_root_digest(layers),
        },
        "runtime": {
            "harness": {"id": "hermes", "version": "0.20.5"},
            "adapter": {"id": "org.agentimage.hermes", "version": "0.1.0"},
        },
        "layers": layers,
        "privacy": {"default": "private", "public_build": False, "unresolved_items": 0},
        "provenance": {
            "source_harness": "hermes",
            "source_adapter": "org.agentimage.hermes",
            "export_tool_version": "0.1.0",
            "source_uri": "hermes:source",
        },
    }
    source_report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "build",
        "adapter": {"id": "org.agentimage.hermes", "version": "0.1.0"},
        "inventory_count": 5,
        "outcomes": [
            {"id": "soul", "source": "SOUL.md", "action": "preserved", "reason": "logical layer"},
            {"id": "skill", "source": "skills/procurement/SKILL.md", "action": "preserved", "reason": "logical layer"},
            {"id": "memory", "source": "memories/MEMORY.md", "action": "preserved", "reason": "logical layer"},
            {"id": "state", "source": "state.db", "action": "preserved", "reason": "native layer"},
            {"id": "env", "source": ".env", "action": "redacted", "reason": "secret filename"},
        ],
    }
    publish_image(AdapterExport(manifest, payloads, source_report), path)
    return path


def test_hermes_to_openclaw_migration_is_dry_run_first_and_reports_native_loss(tmp_path: Path) -> None:
    image_path = _hermes_semantic_image(tmp_path / "hermes.aimg")
    document = load_image(image_path)
    cli = FakeOpenClawCLI(tmp_path)
    adapter = OpenClawAdapter(cli)

    plan = adapter.migration_plan(document, "migrated")

    assert plan["operation"] == "migrate-plan"
    assert plan["requires_confirmation"] is True
    assert len(plan["outcomes"]) == plan["inventory_count"] == 5
    state = next(item for item in plan["outcomes"] if item["source"] == "state.db")
    assert state["action"] == "unsupported"
    assert "preserved in the source image" in state["reason"]
    assert "migrated" not in cli.agents

    report = adapter.semantic_migrate(document, "migrated")

    assert report["validated"] is True
    assert report["portability"] == "P2"
    target = cli.show_agent("migrated")
    assert (target.workspace / "SOUL.md").read_text(encoding="utf-8") == "A migrated negotiator.\n"
    assert (target.workspace / "skills" / "procurement" / "SKILL.md").is_file()
    assert (target.workspace / "MEMORY.md").is_file()
    provenance = json.loads((target.workspace / ".agent-image" / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["source_image_digest"] == document.manifest["image"]["digest"]

    with pytest.raises(AgentImageError) as caught:
        adapter.semantic_migrate(document, "migrated")
    assert caught.value.code == "E_TARGET_EXISTS"
