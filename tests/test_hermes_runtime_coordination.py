from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path

from agent_image.adapters.hermes import (
    HERMES_NATIVE_MEDIA_TYPE,
    HERMES_PIN,
    HERMES_RUNTIME_COORDINATION_PATHS,
    HermesAdapter,
    HermesProfile,
)


def _profile_archive(root_name: str, root: Path) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for source in sorted(path for path in root.rglob("*") if path.is_file()):
                data = source.read_bytes()
                info = tarfile.TarInfo(f"{root_name}/{source.relative_to(root).as_posix()}")
                info.size = len(data)
                info.mtime = 0
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


class _FakeHermesCLI:
    def __init__(self, root: Path) -> None:
        self.root = root

    def version(self) -> str:
        return HERMES_PIN.version

    def show_profile(self, name: str) -> HermesProfile:
        assert name == "source"
        return HermesProfile(name=name, path=self.root)

    def export_profile(self, name: str, output: Path) -> Path:
        output.write_bytes(_profile_archive(name, self.root))
        return output

    def import_profile(self, archive: Path, name: str) -> HermesProfile:  # pragma: no cover - not used here
        raise AssertionError("not used")

    def delete_profile(self, name: str) -> None:  # pragma: no cover - not used here
        raise AssertionError("not used")


def test_memory_lock_is_reported_but_not_carried_as_semantic_or_native_state(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "memories").mkdir(parents=True)
    (source / "memories" / "MEMORY.md").write_text("durable learned state\n", encoding="utf-8")
    (source / "memories" / "MEMORY.md.lock").write_bytes(b"")

    exported = HermesAdapter(_FakeHermesCLI(source)).export(
        "source",
        "private",
        include_experience=True,
        include_workspace=True,
    )

    carried_sources = {
        layer.get("source", {}).get("path")
        for layer in exported.manifest["layers"]
        if isinstance(layer.get("source"), dict)
    }
    assert HERMES_RUNTIME_COORDINATION_PATHS.isdisjoint(carried_sources)

    lock_outcome = next(
        item
        for item in exported.source_report["outcomes"]
        if item.get("source") == "memories/MEMORY.md.lock"
    )
    assert lock_outcome["action"] == "unsupported"
    assert "coordination" in lock_outcome["reason"]

    native_layer = next(
        layer
        for layer in exported.manifest["layers"]
        if layer["kind"] == "native" and layer["media_type"] == HERMES_NATIVE_MEDIA_TYPE
    )
    native = exported.payloads[native_layer["path"]]
    with tarfile.open(fileobj=io.BytesIO(native), mode="r:gz") as archive:
        native_paths = {
            "/".join(member.name.replace("\\", "/").split("/")[1:])
            for member in archive.getmembers()
            if member.isfile()
        }
    assert "memories/MEMORY.md" in native_paths
    assert HERMES_RUNTIME_COORDINATION_PATHS.isdisjoint(native_paths)
