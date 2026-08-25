from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agent_image.adapters.dsh import DSH_PIN, DshAdapter, DshProfile, SubprocessDshCLI
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import load_image, verify_image


# MOCK_POINT {"id":"MOCK-DSH-CLI-TEST-001","type":"test_fixture","target":"SubprocessDshCLI against @deepseek-ai/dsh@0.1.0-rc.6","replace_by":"before_dsh_p1_capability_claim","owner":"dsh-adapter","status":"accepted_test_only","production_allowed":false,"reason":"Unit tests need deterministic dependency drift and rollback injection; capability evidence is generated separately with the real pinned CLI."}
class FakeDshCLI:
    def __init__(self, root: Path, *, available_dependencies: set[str] | None = None) -> None:
        self.root = root
        self.available_dependencies = set(available_dependencies or set())

    def version(self) -> str:
        return DSH_PIN.version

    def home(self) -> Path:
        return self.root

    def target_profile(self, name: str) -> Path:
        return self.root / "profiles" / name

    def show_profile(self, name: str) -> DshProfile:
        path = self.target_profile(name)
        if not path.is_dir() or not (path / "package.json").is_file():
            raise AgentImageError("E_SOURCE_NOT_FOUND", f"DSH profile does not exist: {name}")
        return DshProfile(name=name, path=path)

    def dump_config(self, name: str) -> bytes:
        profile = self.show_profile(name)
        package = json.loads((profile.path / "package.json").read_text(encoding="utf-8"))
        dependencies = package.get("dependencies", {})
        missing = sorted(set(dependencies) - self.available_dependencies)
        if missing:
            raise AgentImageError(
                "E_NATIVE_INCOMPATIBLE",
                f"Unresolved DSH dependencies: {', '.join(missing)}",
            )
        bundles = package["dsh"]["profile"]["bundles"]
        patch = (profile.path / "cordis.patch.yml").read_text(encoding="utf-8")
        return ("bundles:\n" + "".join(f"- {item}\n" for item in bundles) + "patch:\n" + patch).encode("utf-8")

    def delete_profile(self, name: str) -> None:
        shutil.rmtree(self.target_profile(name))


def _make_profile(
    cli: FakeDshCLI,
    name: str,
    *,
    dependencies: dict[str, str] | None = None,
) -> DshProfile:
    path = cli.target_profile(name)
    path.mkdir(parents=True)
    package = {
        "name": f"dsh-profile-{name}",
        "private": True,
        "dependencies": dependencies or {},
        "dsh": {
            "profile": {
                "bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-headless"],
            }
        },
    }
    (path / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    (path / "cordis.patch.yml").write_text("[]\n", encoding="utf-8")
    (path / "cordis.yml").write_text("[]\n", encoding="utf-8")
    (path / "pnpm-workspace.yaml").write_text("onlyBuiltDependencies: []\n", encoding="utf-8")
    (path / "notes.txt").write_text("opaque native profile state\n", encoding="utf-8")
    return DshProfile(name=name, path=path)


def test_dsh_private_export_and_native_restore_preserve_order_and_dump(tmp_path: Path) -> None:
    cli = FakeDshCLI(tmp_path)
    source = _make_profile(cli, "source")
    adapter = DshAdapter(cli)
    image = tmp_path / "source.aimg"
    before = adapter.inspect_source("source")["source"]["digest"]

    build_image(adapter, source="source", output=image, policy="private")

    assert verify_image(image)["valid"] is True
    assert adapter.inspect_source("source")["source"]["digest"] == before
    document = load_image(image)
    assert [layer["kind"] for layer in document.manifest["layers"]] == ["native"]
    assert document.manifest["extensions"]["org.agentimage.dsh.contract"]["bundle_order"] == [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-headless",
    ]

    report = restore_image(adapter, image=image, target="restored")

    assert report["validated"] is True
    assert report["portability"] == "P1"
    assert report["bundle_order"] == ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-headless"]
    assert report["inventory_count"] == len(report["outcomes"])
    assert report["loss_summary"]["unsupported"] == 0
    target = cli.show_profile("restored")
    for filename in ("package.json", "cordis.patch.yml", "cordis.yml", "pnpm-workspace.yaml", "notes.txt"):
        assert (target.path / filename).read_bytes() == (source.path / filename).read_bytes()
    assert cli.dump_config("restored") == cli.dump_config("source")

    with pytest.raises(AgentImageError) as caught:
        restore_image(adapter, image=image, target="restored")
    assert caught.value.code == "E_TARGET_EXISTS"


def test_dsh_unresolved_dependency_fails_loud_and_rolls_back(tmp_path: Path) -> None:
    source_root = tmp_path / "source-host"
    source_cli = FakeDshCLI(source_root, available_dependencies={"@example/plugin"})
    _make_profile(source_cli, "source", dependencies={"@example/plugin": "1.0.0"})
    image = tmp_path / "source.aimg"
    build_image(DshAdapter(source_cli), source="source", output=image, policy="private")

    target_cli = FakeDshCLI(tmp_path / "target-host")
    with pytest.raises(AgentImageError) as caught:
        restore_image(DshAdapter(target_cli), image=image, target="restored")

    assert caught.value.code == "E_NATIVE_INCOMPATIBLE"
    assert "Unresolved DSH dependencies" in caught.value.message
    assert not target_cli.target_profile("restored").exists()


def test_dsh_secret_profile_file_fails_closed(tmp_path: Path) -> None:
    cli = FakeDshCLI(tmp_path)
    source = _make_profile(cli, "source")
    (source.path / ".credentials.yaml").write_text("provider: synthetic\n", encoding="utf-8")

    with pytest.raises(AgentImageError) as caught:
        build_image(DshAdapter(cli), source="source", output=tmp_path / "secret.aimg", policy="private")

    assert caught.value.code == "E_SECRET_DETECTED"


def test_subprocess_dsh_cli_uses_explicit_node_for_package_entry(tmp_path: Path) -> None:
    script = tmp_path / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
    script.parent.mkdir(parents=True)
    script.write_text("// official package entry placeholder\n", encoding="utf-8")
    cli = SubprocessDshCLI(binary=str(script), node_binary="C:/runtime/node.exe", dsh_home=tmp_path / "home")

    assert cli._command(["--version"]) == ["C:/runtime/node.exe", str(script), "--version"]
