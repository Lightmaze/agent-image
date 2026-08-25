from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path

from agent_image.adapters.hermes import HermesAdapter, SubprocessHermesCLI
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import verify_image


def _safe_clean(root: Path, project: Path) -> None:
    resolved = root.resolve()
    expected_parent = (project / ".tmp").resolve()
    if resolved.parent != expected_parent or not resolved.name.startswith("ci-hermes-smoke-"):
        raise RuntimeError(f"Refusing to clean unexpected smoke root: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    platform_label = platform.system().casefold() or os.name
    smoke = project / ".tmp" / f"ci-hermes-smoke-{platform_label}"
    _safe_clean(smoke, project)
    profile = smoke / "home" / "profiles" / "source"
    (profile / "memories").mkdir(parents=True)
    (profile / "sessions").mkdir()
    (profile / "skills" / "evidence-first").mkdir(parents=True)
    (profile / "workspace").mkdir()
    files = {
        ".env": "SYNTHETIC_ONLY=1\n",
        ".no-bundled-skills": "\n",
        "profile.yaml": "description: Cross-platform real Hermes smoke\ndescription_auto: false\n",
        "SOUL.md": "# Synthetic CI Agent\nProtect source provenance and report loss.\n",
        "memories/MEMORY.md": "# Synthetic memory\nRound-trip evidence belongs to no person.\n",
        "memories/USER.md": "# Synthetic principal\nNo private user data.\n",
        "sessions/practice.jsonl": json.dumps({"episode": 1, "result": "synthetic"}) + "\n",
        "skills/evidence-first/SKILL.md": "# Evidence first\nNever exceed the observed capability.\n",
        "workspace/roundtrip.md": "# Pending\nVerify the restored target.\n",
    }
    for relative, text in files.items():
        (profile / Path(*relative.split("/"))).write_bytes(text.encode("utf-8"))
    (profile / "state.db").write_bytes(b"synthetic-state-not-a-sqlite-secret\n")

    environment = {"HERMES_HOME": str((smoke / "home").resolve()), "PYTHONUTF8": "1"}
    executable_name = "hermes.exe" if os.name == "nt" else "hermes"
    hermes_binary = shutil.which("hermes") or str(Path(sys.executable).absolute().parent / executable_name)
    adapter = HermesAdapter(SubprocessHermesCLI(binary=hermes_binary, environment=environment))
    image = smoke / "source.aimg"
    source_before = adapter.inspect_source("source")["source"]["digest"]
    build = build_image(
        adapter,
        source="source",
        output=image,
        policy="private",
        include_experience=True,
        include_workspace=True,
    )
    restore = restore_image(adapter, image=image, target="restored")
    source_after = adapter.inspect_source("source")["source"]["digest"]
    if source_before != source_after:
        raise RuntimeError("Hermes source changed during cross-platform smoke.")
    if restore.get("portability") != "P1" or restore.get("validated") is not True:
        raise RuntimeError("Hermes P1 restore did not validate.")
    print(json.dumps({
        "valid": True,
        "harness": "hermes-agent==0.20.5",
        "source_immutable": True,
        "image": verify_image(image),
        "build": build,
        "restore": {
            "target": restore["target"],
            "portability": restore["portability"],
            "validated": restore["validated"],
            "inventory_count": restore["inventory_count"],
        },
        "platform": os.name,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
