from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from agent_image.adapter_contract import AdapterExport
from agent_image.adapters.dsh import (
    DSH_NATIVE_MEDIA_TYPE,
    DSH_PIN,
    DshAdapter,
    DshProfile,
    _read_native,
    _tar_bytes,
)
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import layer_root_digest, load_image, publish_image


class _FakeDshCLI:
    def __init__(self, root: Path) -> None:
        self.root = root

    def version(self) -> str:
        return DSH_PIN.version

    def home(self) -> Path:
        return self.root

    def target_profile(self, name: str) -> Path:
        return self.root / "profiles" / name

    def show_profile(self, name: str) -> DshProfile:
        path = self.target_profile(name)
        if not path.is_dir() or not (path / "package.json").is_file():
            from agent_image.errors import AgentImageError

            raise AgentImageError("E_SOURCE_NOT_FOUND", f"DSH profile does not exist: {name}")
        return DshProfile(name=name, path=path)

    def dump_config(self, name: str) -> bytes:
        profile = self.show_profile(name)
        package = json.loads((profile.path / "package.json").read_text(encoding="utf-8"))
        bundles = package["dsh"]["profile"]["bundles"]
        patch = (profile.path / "cordis.patch.yml").read_text(encoding="utf-8")
        return ("bundles:\n" + "".join(f"- {item}\n" for item in bundles) + "patch:\n" + patch).encode("utf-8")

    def delete_profile(self, name: str) -> None:
        shutil.rmtree(self.target_profile(name))


def _make_profile(cli: _FakeDshCLI, name: str) -> DshProfile:
    path = cli.target_profile(name)
    path.mkdir(parents=True)
    package = {
        "name": f"dsh-profile-{name}",
        "private": True,
        "dependencies": {},
        "dsh": {
            "profile": {
                "bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-headless"],
            }
        },
    }
    (path / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    (path / "cordis.patch.yml").write_text("[]\n", encoding="utf-8")
    (path / "cordis.yml").write_text("[]\n", encoding="utf-8")
    return DshProfile(name=name, path=path)


def _native_layer(document):
    return next(
        layer
        for layer in document.manifest["layers"]
        if layer["kind"] == "native" and layer["media_type"] == DSH_NATIVE_MEDIA_TYPE
    )


def test_dsh_new_native_writer_excludes_producer_identity(tmp_path: Path) -> None:
    cli = _FakeDshCLI(tmp_path)
    _make_profile(cli, "source")
    image = tmp_path / "source.aimg"

    build_image(DshAdapter(cli), source="source", output=image, policy="private")

    document = load_image(image)
    layer = _native_layer(document)
    entries = _read_native(document.entries[layer["path"]])
    metadata = json.loads(entries["meta/profile.json"].decode("utf-8"))

    assert metadata == {
        "bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-headless"],
        "dependencies": {},
    }
    assert "source_name" not in metadata


def test_dsh_legacy_source_name_metadata_still_restores_p1(tmp_path: Path) -> None:
    cli = _FakeDshCLI(tmp_path)
    _make_profile(cli, "source")
    adapter = DshAdapter(cli)
    current = tmp_path / "current.aimg"
    legacy = tmp_path / "legacy.aimg"

    build_image(adapter, source="source", output=current, policy="private")
    document = load_image(current)
    manifest = copy.deepcopy(document.manifest)
    layer = next(
        item
        for item in manifest["layers"]
        if item["kind"] == "native" and item["media_type"] == DSH_NATIVE_MEDIA_TYPE
    )
    entries = _read_native(document.entries[layer["path"]])
    metadata = json.loads(entries["meta/profile.json"].decode("utf-8"))
    metadata["source_name"] = "legacy-source"
    entries["meta/profile.json"] = canonical_json_bytes(metadata) + b"\n"
    legacy_native = _tar_bytes(entries)
    layer["digest"] = sha256_bytes(legacy_native)
    layer["size"] = len(legacy_native)
    manifest["image"]["digest"] = layer_root_digest(manifest["layers"])

    publish_image(
        AdapterExport(
            manifest=manifest,
            payloads={layer["path"]: legacy_native},
            source_report=document.json_entry("meta/source-report.json"),
        ),
        legacy,
    )

    report = restore_image(adapter, image=legacy, target="legacy-restored")

    assert report["validated"] is True
    assert report["portability"] == "P1"
    restored = cli.show_profile("legacy-restored")
    assert (restored.path / "package.json").is_file()
    assert (restored.path / "cordis.patch.yml").is_file()
