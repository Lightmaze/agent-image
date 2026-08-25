from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path

import pytest

from agent_image.adapters.hermes import HERMES_PIN, HermesAdapter, HermesProfile
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
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
