from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import io
import tarfile
from pathlib import Path

import pytest

from agent_image.adapters.hermes import HERMES_PIN, HermesAdapter, HermesProfile
from agent_image.errors import AgentImageError
from agent_image.formal_service import (
    build_image,
    plan_build,
    prepare_image_workspace,
    publish_prepared_workspace_image,
    restore_image,
)
from agent_image.image_archive import load_image, verify_image


def _snapshot_bytes(root_name: str, root: Path) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for source in sorted(path for path in root.rglob("*") if path.is_file()):
                relative = source.relative_to(root).as_posix()
                if source.name in {".env", "auth.json"}:
                    continue
                data = source.read_bytes()
                info = tarfile.TarInfo(f"{root_name}/{relative}")
                info.size = len(data)
                info.mtime = 0
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


class FakeHermesCLI:
    def __init__(self, source_name: str, source: Path, *, version: str = HERMES_PIN.version) -> None:
        self.version_value = version
        self.profiles = {source_name: source}
        self.show_calls: list[str] = []

    def version(self) -> str:
        return self.version_value

    def show_profile(self, name: str) -> HermesProfile:
        self.show_calls.append(name)
        try:
            path = self.profiles[name]
        except KeyError as error:
            raise AgentImageError("E_SOURCE_NOT_FOUND", f"Hermes profile does not exist: {name}") from error
        return HermesProfile(name=name, path=path)

    def export_profile(self, name: str, output: Path) -> Path:
        profile = self.show_profile(name)
        output.write_bytes(_snapshot_bytes(name, profile.path))
        return output

    def import_profile(self, archive: Path, name: str) -> HermesProfile:
        if name in self.profiles:
            raise AgentImageError("E_TARGET_EXISTS", f"Hermes target already exists: {name}")
        target = next(iter(self.profiles.values())).parent / name
        target.mkdir()
        with tarfile.open(archive, "r:gz") as source:
            members = [member for member in source.getmembers() if member.isfile()]
            root = members[0].name.split("/", 1)[0]
            for member in members:
                relative = member.name.removeprefix(f"{root}/")
                destination = target / Path(*relative.split("/"))
                destination.parent.mkdir(parents=True, exist_ok=True)
                stream = source.extractfile(member)
                assert stream is not None
                destination.write_bytes(stream.read())
        self.profiles[name] = target
        return HermesProfile(name=name, path=target)

    def delete_profile(self, name: str) -> None:
        profile = self.profiles.pop(name)
        for path in sorted(profile.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        profile.rmdir()


@pytest.fixture
def hermes_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "skills" / "coding").mkdir(parents=True)
    (source / "memories").mkdir()
    (source / "sessions").mkdir()
    (source / "SOUL.md").write_text("A precise research agent.\n", encoding="utf-8")
    (source / "skills" / "coding" / "SKILL.md").write_text("Use evidence.\n", encoding="utf-8")
    (source / "memories" / "MEMORY.md").write_text("Learned convention.\n", encoding="utf-8")
    (source / "memories" / "USER.md").write_text("Private principal context.\n", encoding="utf-8")
    (source / "sessions" / "practice.jsonl").write_text('{"event":"practice"}\n', encoding="utf-8")
    (source / "state.db").write_bytes(b"sqlite-native-state")
    (source / ".env").write_text("API_KEY=never-export\n", encoding="utf-8")
    (source / "auth.json").write_text('{"token":"never-export"}\n', encoding="utf-8")
    return source


def test_real_contract_shape_builds_and_restores_p1_without_silent_loss(
    hermes_source: Path, tmp_path: Path
) -> None:
    cli = FakeHermesCLI("source", hermes_source)
    adapter = HermesAdapter(cli=cli)
    image = tmp_path / "source.aimg"
    source_before = adapter.profile_digest("source")

    result = build_image(
        adapter,
        source="source",
        output=image,
        policy="private",
        include_experience=True,
    )

    assert result["verified"] is True
    assert source_before == adapter.profile_digest("source")
    assert verify_image(image)["valid"] is True
    document = load_image(image)
    assert document.manifest["runtime"]["harness"] == {"id": "hermes", "version": HERMES_PIN.version}
    assert {layer["kind"] for layer in document.manifest["layers"]} >= {
        "identity",
        "skills",
        "memory",
        "experience",
        "native",
    }
    assert all(".env" not in path and "auth.json" not in path for path in document.entries)
    source_report = document.json_entry("meta/source-report.json")
    assert source_report["inventory_count"] == len(source_report["outcomes"])
    assert {item["action"] for item in source_report["outcomes"]} <= {
        "preserved",
        "transformed",
        "redacted",
        "unsupported",
        "dropped_by_user",
    }

    restore = restore_image(adapter, image=image, target="restored")

    assert restore["target"] == "restored"
    assert restore["validated"] is True
    assert restore["inventory_count"] == len(restore["outcomes"])
    assert source_before == adapter.profile_digest("source")
    restored = cli.profiles["restored"]
    assert (restored / "SOUL.md").read_bytes() == (hermes_source / "SOUL.md").read_bytes()
    assert (restored / "skills" / "coding" / "SKILL.md").read_bytes() == (
        hermes_source / "skills" / "coding" / "SKILL.md"
    ).read_bytes()
    assert (restored / "memories" / "MEMORY.md").read_bytes() == (
        hermes_source / "memories" / "MEMORY.md"
    ).read_bytes()
    assert not (restored / ".env").exists()
    assert not (restored / "auth.json").exists()

    with pytest.raises(AgentImageError, match="already exists"):
        restore_image(adapter, image=image, target="restored")


def test_hermes_adapter_rejects_unpinned_runtime(hermes_source: Path, tmp_path: Path) -> None:
    adapter = HermesAdapter(cli=FakeHermesCLI("source", hermes_source, version="0.20.6"))
    with pytest.raises(AgentImageError) as caught:
        build_image(adapter, source="source", output=tmp_path / "bad.aimg", policy="private")
    assert caught.value.code == "E_SOURCE_UNSUPPORTED"


def test_second_secret_pass_rejects_structured_secret_in_official_snapshot(
    hermes_source: Path, tmp_path: Path
) -> None:
    (hermes_source / "config.yaml").write_text("api_key: should-have-been-redacted\n", encoding="utf-8")
    adapter = HermesAdapter(cli=FakeHermesCLI("source", hermes_source))
    output = tmp_path / "secret.aimg"
    with pytest.raises(AgentImageError) as caught:
        build_image(adapter, source="source", output=output, policy="private")
    assert caught.value.code == "E_SECRET_DETECTED"
    assert not output.exists()


def test_public_policy_excludes_private_hermes_state(hermes_source: Path, tmp_path: Path) -> None:
    adapter = HermesAdapter(cli=FakeHermesCLI("source", hermes_source))
    image = tmp_path / "public.aimg"
    build_image(adapter, source="source", output=image, policy="public")
    document = load_image(image)
    assert document.manifest["privacy"]["public_build"] is True
    assert document.manifest["layers"] == []
    assert set(document.entries) == {
        "manifest.yaml",
        "index.json",
        "meta/checksums.txt",
        "meta/source-report.json",
    }
    assert all("source" not in outcome for outcome in document.json_entry("meta/source-report.json")["outcomes"])


def test_experience_opt_in_controls_native_snapshot_too(hermes_source: Path, tmp_path: Path) -> None:
    adapter = HermesAdapter(cli=FakeHermesCLI("source", hermes_source))
    image = tmp_path / "default-private.aimg"
    build_image(adapter, source="source", output=image, policy="private")
    document = load_image(image)
    assert all(layer["kind"] != "experience" for layer in document.manifest["layers"])
    native = next(layer for layer in document.manifest["layers"] if layer["kind"] == "native")
    with tarfile.open(fileobj=io.BytesIO(document.entries[native["path"]]), mode="r:gz") as archive:
        assert all("/sessions/" not in member.name for member in archive.getmembers())
    outcome = next(
        item
        for item in document.json_entry("meta/source-report.json")["outcomes"]
        if item.get("source") == "sessions/practice.jsonl"
    )
    assert outcome["action"] == "dropped_by_user"


def test_prepared_workspace_publishes_exact_candidate_without_reopening_source(
    hermes_source: Path, tmp_path: Path
) -> None:
    cli = FakeHermesCLI("source", hermes_source)
    adapter = HermesAdapter(cli=cli)
    workspace = tmp_path / "prepared"
    output = tmp_path / "published.aimg"

    plan = plan_build(
        adapter,
        source="source",
        policy="private",
        include_experience=True,
        include_workspace=False,
    )
    prepared = prepare_image_workspace(
        adapter,
        source="source",
        workspace=workspace,
        policy="private",
        include_experience=True,
        include_workspace=False,
        approved_plan=plan,
    )
    candidate = workspace / "candidate.aimg"
    candidate_bytes = candidate.read_bytes()

    # Publication takes only the prepared workspace; no adapter/source object is
    # available to this API and the exact reviewed bytes must be copied.
    published = publish_prepared_workspace_image(workspace=workspace, output=output)

    assert output.read_bytes() == candidate_bytes
    assert published["source_reopened"] is False
    assert published["adapter_reinvoked"] is False
    assert prepared["prepared_subject"]["archive_digest"] == published["archive_digest"]
    assert verify_image(output)["valid"] is True


# B29 / R90: real package, valid Hermes image, independent publisher processes.

def _run_two_publishers(worker: str, first: Path, second: Path) -> list[dict[str, str]]:
    env = os.environ.copy()
    repo_src = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [repo_src, env.get("PYTHONPATH", "")]))
    children = [
        subprocess.Popen(
            [sys.executable, "-c", worker, str(first), str(second)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
        )
        for _ in range(2)
    ]
    reports = []
    for child in children:
        stdout, stderr = child.communicate(timeout=40)
        assert child.returncode == 0, stderr
        reports.append(json.loads(stdout.strip()))
    return reports


def test_prepared_workspace_rejects_preexisting_empty_directory_before_capture(
    hermes_source: Path, tmp_path: Path,
) -> None:
    workspace = tmp_path / "prepared"
    workspace.mkdir()
    cli = FakeHermesCLI("source", hermes_source)
    adapter = HermesAdapter(cli=cli)
    with pytest.raises(AgentImageError) as caught:
        prepare_image_workspace(adapter, source="source", workspace=workspace, policy="private")
    assert caught.value.code == "E_TARGET_EXISTS"
    assert cli.show_calls == []


def test_two_processes_publish_one_real_prepared_image_without_clobber(
    hermes_source: Path, tmp_path: Path,
) -> None:
    cli = FakeHermesCLI("source", hermes_source)
    adapter = HermesAdapter(cli=cli)
    workspace = tmp_path / "prepared"
    prepare_image_workspace(adapter, source="source", workspace=workspace, policy="private")
    candidate = (workspace / "candidate.aimg").read_bytes()
    output = tmp_path / "published.aimg"
    worker = """
import json, sys
from pathlib import Path
from agent_image.errors import AgentImageError
from agent_image.prepared_workspace import publish_prepared_workspace
try:
    result = publish_prepared_workspace(Path(sys.argv[1]), output=Path(sys.argv[2]))
    print(json.dumps({"code": "OK", "digest": result["archive_digest"]}))
except AgentImageError as error:
    print(json.dumps({"code": error.code}))
"""
    reports = _run_two_publishers(worker, workspace, output)
    assert sorted(item["code"] for item in reports) == ["E_TARGET_EXISTS", "OK"]
    assert output.read_bytes() == candidate
    assert verify_image(output)["valid"] is True


def test_two_processes_commit_one_real_prepared_receipt_without_clobber(
    hermes_source: Path, tmp_path: Path,
) -> None:
    cli = FakeHermesCLI("source", hermes_source)
    adapter = HermesAdapter(cli=cli)
    workspace = tmp_path / "prepared"
    prepare_image_workspace(adapter, source="source", workspace=workspace, policy="private")
    control = workspace / "receipt.json"
    output = tmp_path / "saved-receipt.json"
    worker = """
import json, sys
from pathlib import Path
from agent_image.errors import AgentImageError
from agent_image.prepared_build import load_prepared_build_receipt, save_prepared_build_receipt
try:
    receipt = load_prepared_build_receipt(Path(sys.argv[1]))
    save_prepared_build_receipt(receipt, Path(sys.argv[2]))
    print(json.dumps({"code": "OK"}))
except AgentImageError as error:
    print(json.dumps({"code": error.code}))
"""
    reports = _run_two_publishers(worker, control, output)
    assert sorted(item["code"] for item in reports) == ["E_TARGET_EXISTS", "OK"]
    assert output.read_bytes() == control.read_bytes()


def test_prepared_workspace_binds_valid_receipt_to_exact_seal(
    hermes_source: Path, tmp_path: Path,
) -> None:
    # A receipt can be self-valid and bind the correct candidate bytes while
    # claiming a different intent. Neither recovery nor publication may accept
    # it as the receipt for a different, valid workspace seal.
    from agent_image.canonical import canonical_json_bytes, sha256_bytes
    from agent_image.prepared_build import (
        load_prepared_build_receipt, verify_prepared_build_receipt,
    )
    from agent_image.prepared_workspace import recover_prepared_workspace

    cli = FakeHermesCLI("source", hermes_source)
    adapter = HermesAdapter(cli=cli)
    workspace = tmp_path / "prepared"
    prepare_image_workspace(adapter, source="source", workspace=workspace, policy="private")
    receipt_path = workspace / "receipt.json"
    original = load_prepared_build_receipt(receipt_path)
    altered = dict(original)
    altered["intent"] = dict(original["intent"])
    altered["intent"]["include_workspace"] = not original["intent"]["include_workspace"]
    body = {key: altered[key] for key in altered if key != "receipt_digest"}
    altered["receipt_digest"] = sha256_bytes(canonical_json_bytes(body))
    assert verify_prepared_build_receipt(altered)["receipt_digest"] == altered["receipt_digest"]
    receipt_path.write_bytes(canonical_json_bytes(altered) + b"\n")

    with pytest.raises(AgentImageError) as recovery:
        recover_prepared_workspace(workspace)
    assert recovery.value.code == "E_PREPARED_STALE"

    output = tmp_path / "must-not-publish.aimg"
    with pytest.raises(AgentImageError) as publishing:
        publish_prepared_workspace_image(workspace=workspace, output=output)
    assert publishing.value.code == "E_PREPARED_STALE"
    assert not output.exists()
