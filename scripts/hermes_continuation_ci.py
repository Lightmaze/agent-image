from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path

from agent_image.adapters.hermes import (
    HERMES_RUNTIME_COORDINATION_PATHS,
    HermesAdapter,
    SubprocessHermesCLI,
)
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import diff_images, load_image, verify_image


BASE_MEMORY = "Synthetic base memory: preserve provenance across continuation."
CONTINUED_MEMORY = "Synthetic continuation memory: this entry was written after fresh restore."


def _safe_clean(root: Path, project: Path) -> None:
    resolved = root.resolve()
    expected_parent = (project / ".tmp").resolve()
    if resolved.parent != expected_parent or not resolved.name.startswith("ci-hermes-continuation-"):
        raise RuntimeError(f"Refusing to clean unexpected continuation root: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


@contextmanager
def _hermes_home(path: Path):
    previous = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(path.resolve())
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = previous


def _write_source_profile(profile: Path) -> None:
    (profile / "memories").mkdir(parents=True)
    (profile / "sessions").mkdir()
    (profile / "skills" / "evidence-first").mkdir(parents=True)
    (profile / "workspace").mkdir()
    files = {
        ".env": "SYNTHETIC_ONLY=1\n",
        ".no-bundled-skills": "\n",
        "profile.yaml": "description: Hermes continuation-state CI\ndescription_auto: false\n",
        "SOUL.md": "# Synthetic continuation Agent\nPreserve observed state and report loss.\n",
        "memories/MEMORY.md": BASE_MEMORY,
        "memories/USER.md": "Synthetic principal only; no private user data.",
        "sessions/practice.jsonl": json.dumps({"episode": 1, "result": "synthetic-parent"}) + "\n",
        "skills/evidence-first/SKILL.md": "# Evidence first\nNever exceed observed capability.\n",
        "workspace/continuation.md": "# Parent\nAwait one post-restore native memory update.\n",
    }
    for relative, text in files.items():
        destination = profile / Path(*relative.split("/"))
        destination.write_text(text, encoding="utf-8")
    (profile / "state.db").write_bytes(b"synthetic-state-not-a-sqlite-secret\n")


def _native_memory_add(profile: Path) -> dict[str, object]:
    # This is an upstream Hermes runtime-library mutation, not a direct file edit
    # performed by Agent Image. It exercises the same MemoryStore.add path used by
    # the built-in memory tool while avoiding a paid/model-dependent inference call.
    with _hermes_home(profile):
        from tools.memory_tool import MemoryStore

        store = MemoryStore()
        store.load_from_disk()
        result = store.add("memory", CONTINUED_MEMORY)
    if result.get("success") is not True:
        raise RuntimeError(f"Pinned Hermes MemoryStore.add did not persist the continuation state: {result}")
    return result


def _memory_text(profile: Path) -> str:
    return (profile / "memories" / "MEMORY.md").read_text(encoding="utf-8")


def _assert_runtime_coordination_is_reported_not_carried(document) -> None:
    carried_sources = {
        layer.get("source", {}).get("path")
        for layer in document.manifest["layers"]
        if isinstance(layer.get("source"), dict)
    }
    leaked = HERMES_RUNTIME_COORDINATION_PATHS & carried_sources
    if leaked:
        raise RuntimeError(f"Hermes runtime coordination files became semantic layers: {sorted(leaked)}")

    source_report = document.json_entry("meta/source-report.json")
    outcomes_by_source = {
        item.get("source"): item
        for item in source_report["outcomes"]
        if isinstance(item.get("source"), str)
    }
    for path in HERMES_RUNTIME_COORDINATION_PATHS:
        if path not in outcomes_by_source:
            continue
        if outcomes_by_source[path].get("action") != "unsupported":
            raise RuntimeError(f"Hermes runtime coordination file was not reported as unsupported: {path}")


def _assert_truthful_diff_partition(image_diff: dict[str, object], memory_layer_id: str) -> None:
    layers = image_diff.get("layers")
    if not isinstance(layers, dict):
        raise RuntimeError("Continuation diff did not return a layer result object.")
    changed = set(layers.get("changed", []))
    state_changed = set(layers.get("state_changed", []))
    metadata_changed = set(layers.get("metadata_changed", []))
    expected_state = {memory_layer_id, "hermes-native-profile"}
    if state_changed != expected_state:
        raise RuntimeError(
            f"Continuation diff misclassified durable state changes: expected {sorted(expected_state)}, "
            f"got {sorted(state_changed)}"
        )
    if not metadata_changed:
        raise RuntimeError("Continuation diff did not expose any provenance-only descriptor changes.")
    if state_changed & metadata_changed:
        raise RuntimeError("Continuation diff classified a layer as both state and metadata changed.")
    if changed != state_changed | metadata_changed:
        raise RuntimeError("Legacy changed list is not the union of state_changed and metadata_changed.")
    if layers.get("added") or layers.get("removed"):
        raise RuntimeError("Continuation diff unexpectedly added or removed semantic layer identities.")


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    platform_label = platform.system().casefold() or os.name
    smoke = project / ".tmp" / f"ci-hermes-continuation-{platform_label}"
    _safe_clean(smoke, project)

    profile = smoke / "home" / "profiles" / "source"
    _write_source_profile(profile)

    environment = {"HERMES_HOME": str((smoke / "home").resolve()), "PYTHONUTF8": "1"}
    executable_name = "hermes.exe" if os.name == "nt" else "hermes"
    hermes_binary = shutil.which("hermes") or str(Path(sys.executable).absolute().parent / executable_name)
    adapter = HermesAdapter(SubprocessHermesCLI(binary=hermes_binary, environment=environment))

    parent_image = smoke / "parent.aimg"
    parent_source_before = adapter.inspect_source("source")["source"]["digest"]
    parent_build = build_image(
        adapter,
        source="source",
        output=parent_image,
        policy="private",
        include_experience=True,
        include_workspace=True,
    )
    parent_source_after = adapter.inspect_source("source")["source"]["digest"]
    if parent_source_before != parent_source_after:
        raise RuntimeError("Parent Hermes source changed during image build.")

    parent_restore = restore_image(adapter, image=parent_image, target="continued")
    if parent_restore.get("portability") != "P1" or parent_restore.get("validated") is not True:
        raise RuntimeError("Parent fresh restore did not validate as Hermes P1.")

    continued_profile = adapter.cli.show_profile("continued").path
    if BASE_MEMORY not in _memory_text(continued_profile):
        raise RuntimeError("Parent state was not present after fresh restore.")

    memory_result = _native_memory_add(continued_profile)
    continued_text = _memory_text(continued_profile)
    if BASE_MEMORY not in continued_text or CONTINUED_MEMORY not in continued_text:
        raise RuntimeError("Hermes native memory update did not preserve parent state plus new state.")
    if not (continued_profile / "memories" / "MEMORY.md.lock").exists():
        raise RuntimeError("Pinned Hermes MemoryStore.add did not create the expected runtime coordination lock file.")

    child_source_before = adapter.inspect_source("continued")["source"]["digest"]
    child_image = smoke / "child.aimg"
    child_build = build_image(
        adapter,
        source="continued",
        output=child_image,
        policy="private",
        include_experience=True,
        include_workspace=True,
    )
    child_source_after = adapter.inspect_source("continued")["source"]["digest"]
    if child_source_before != child_source_after:
        raise RuntimeError("Continued Hermes source changed during child image build.")

    parent_verify = verify_image(parent_image)
    child_verify = verify_image(child_image)
    if parent_verify["image_digest"] == child_verify["image_digest"]:
        raise RuntimeError("Child image digest did not change after the native continuation update.")

    image_diff = diff_images(parent_image, child_image)
    parent_doc = load_image(parent_image)
    child_doc = load_image(child_image)
    _assert_runtime_coordination_is_reported_not_carried(child_doc)
    parent_memory_layers = {
        layer["source"]["path"]: layer
        for layer in parent_doc.manifest["layers"]
        if layer["kind"] == "memory" and "source" in layer
    }
    child_memory_layers = {
        layer["source"]["path"]: layer
        for layer in child_doc.manifest["layers"]
        if layer["kind"] == "memory" and "source" in layer
    }
    memory_path = "memories/MEMORY.md"
    if memory_path not in parent_memory_layers or memory_path not in child_memory_layers:
        raise RuntimeError("Expected Hermes memory layer was not represented in both images.")
    if parent_memory_layers[memory_path]["id"] != child_memory_layers[memory_path]["id"]:
        raise RuntimeError("Hermes memory logical layer identity changed across continuation.")
    if parent_memory_layers[memory_path]["digest"] == child_memory_layers[memory_path]["digest"]:
        raise RuntimeError("The memory layer digest did not record the post-restore native update.")
    _assert_truthful_diff_partition(image_diff, child_memory_layers[memory_path]["id"])

    # Remove the live continuation target before testing the child artifact. The
    # fresh child restore therefore cannot read state from the source profile it
    # was built from.
    adapter.cli.delete_profile("continued")
    child_restore = restore_image(adapter, image=child_image, target="child-restored")
    if child_restore.get("portability") != "P1" or child_restore.get("validated") is not True:
        raise RuntimeError("Independent child restore did not validate as Hermes P1.")
    child_profile = adapter.cli.show_profile("child-restored").path
    child_text = _memory_text(child_profile)
    if BASE_MEMORY not in child_text or CONTINUED_MEMORY not in child_text:
        raise RuntimeError("Fresh child restore lost inherited or post-restore Hermes memory state.")
    for path in HERMES_RUNTIME_COORDINATION_PATHS:
        if (child_profile / Path(*path.split("/"))).exists():
            raise RuntimeError(f"Fresh child restore materialized a runtime coordination file: {path}")

    result = {
        "valid": True,
        "claim": "pinned Hermes native-state continuation across parent restore -> native update -> child image -> independent child restore",
        "claim_boundary": "state continuation only; not learning, skill acquisition, behavioral retention, causal lineage, or cross-harness portability",
        "harness": "hermes-agent==0.20.5",
        "platform": os.name,
        "parent": {
            "image": parent_verify,
            "build": parent_build,
            "restore": {
                "target": parent_restore["target"],
                "portability": parent_restore["portability"],
                "validated": parent_restore["validated"],
            },
        },
        "native_update": {
            "surface": "tools.memory_tool.MemoryStore.add",
            "success": memory_result.get("success"),
            "entry_count": memory_result.get("entry_count"),
            "source_digest_before_child_build": child_source_before,
            "source_immutable_during_child_build": child_source_before == child_source_after,
        },
        "runtime_coordination": {
            "observed_after_native_update": True,
            "reported_not_carried": True,
            "paths": sorted(HERMES_RUNTIME_COORDINATION_PATHS),
        },
        "child": {
            "image": child_verify,
            "build": child_build,
            "restore": {
                "target": child_restore["target"],
                "portability": child_restore["portability"],
                "validated": child_restore["validated"],
            },
            "inherited_parent_memory": BASE_MEMORY in child_text,
            "retained_post_restore_memory": CONTINUED_MEMORY in child_text,
        },
        "diff": image_diff,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
