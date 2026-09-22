#!/usr/bin/env python3
"""Exercise parent -> restore -> native workspace update -> child on pinned OpenClaw.

This is a no-model continuation experiment. It first builds a no-op refreeze
control before changing MEMORY.md so state-diff noise is visible rather than
mistaken for development. The real transition is then bound with the generic
continuation evidence object from the preceding candidate change.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from agent_image.adapters.openclaw import OPENCLAW_PIN, OpenClawAdapter, SubprocessOpenClawCLI
from agent_image.canonical import canonical_json_bytes
from agent_image.continuation import build_continuation_binding, verify_continuation_binding
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import diff_images, load_image


PARENT_MEMORY = "Synthetic parent memory.\n"
CONTINUED_MEMORY = "Synthetic post-restore continuation memory.\n"


def _memory_layer_id(image: Path) -> str:
    document = load_image(image)
    matches = [
        layer["id"]
        for layer in document.manifest["layers"]
        if layer.get("source", {}).get("path") == "workspace/MEMORY.md"
    ]
    if len(matches) != 1:
        raise AgentImageError(
            "E_NATIVE_INCOMPATIBLE",
            "Expected exactly one OpenClaw semantic MEMORY.md layer.",
            details={"matches": matches},
        )
    return matches[0]


def _safe_delete(cli: SubprocessOpenClawCLI, name: str) -> None:
    try:
        names = {agent.id for agent in cli.list_agents()}
        if name in names:
            cli.delete_agent(name)
    except Exception:
        # CI uses an isolated state directory that is discarded after the run.
        pass


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openclaw-binary", required=True)
    parser.add_argument("--node-binary", required=True)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="agent-image-openclaw-continuation-") as temporary:
        root = Path(temporary).resolve()
        state_dir = root / "state"
        workspace_root = root / "workspaces"
        images = root / "images"
        state_dir.mkdir(parents=True)
        workspace_root.mkdir(parents=True)
        images.mkdir(parents=True)

        cli = SubprocessOpenClawCLI(
            binary=args.openclaw_binary,
            node_binary=args.node_binary,
            environment={"OPENCLAW_STATE_DIR": str(state_dir)},
            workspace_root=workspace_root,
        )
        if cli.version() != OPENCLAW_PIN.version:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Pinned OpenClaw version mismatch in continuation CI.")
        adapter = OpenClawAdapter(cli)

        parent = images / "parent.aimg"
        noop_child = images / "noop-child.aimg"
        child = images / "child.aimg"
        binding_path = images / "continuation-binding.json"

        for name in ("source", "continued", "child-restored"):
            _safe_delete(cli, name)

        try:
            source = cli.add_agent("source", cli.target_workspace("source"))
            memory = source.workspace / "MEMORY.md"
            memory.write_text(PARENT_MEMORY, encoding="utf-8", newline="\n")

            source_before = adapter.agent_digest("source")
            parent_report = build_image(
                adapter,
                source="source",
                output=parent,
                policy="private",
                include_workspace=True,
            )
            if adapter.agent_digest("source") != source_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "Parent build changed the OpenClaw source state.")

            parent_restore = restore_image(adapter, image=parent, target="continued")
            if not parent_restore.get("validated") or parent_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Parent fresh restore did not validate as P1.")

            continued = cli.show_agent("continued")
            continued_memory = continued.workspace / "MEMORY.md"
            if continued_memory.read_text(encoding="utf-8") != PARENT_MEMORY:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Parent memory did not survive fresh restore.")

            # Negative/no-op control: refreeze immediately, before any intended mutation.
            continued_before = adapter.agent_digest("continued")
            build_image(
                adapter,
                source="continued",
                output=noop_child,
                policy="private",
                include_workspace=True,
            )
            if adapter.agent_digest("continued") != continued_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "No-op child build changed the OpenClaw source state.")
            noop_diff = diff_images(parent, noop_child)

            # Native persistent-state update on OpenClaw's documented workspace memory surface.
            continued_memory.write_text(PARENT_MEMORY + CONTINUED_MEMORY, encoding="utf-8", newline="\n")
            if continued_memory.read_text(encoding="utf-8") != PARENT_MEMORY + CONTINUED_MEMORY:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "OpenClaw workspace memory update did not persist.")

            mutated_before = adapter.agent_digest("continued")
            child_report = build_image(
                adapter,
                source="continued",
                output=child,
                policy="private",
                include_workspace=True,
            )
            if adapter.agent_digest("continued") != mutated_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "Child build changed the OpenClaw source state.")

            actual_diff = diff_images(parent, child)
            memory_layer = _memory_layer_id(parent)
            expected_semantic_change = memory_layer in actual_diff["layers"]["state_changed"]
            if not expected_semantic_change:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "OpenClaw MEMORY.md mutation was not reported as a state change.",
                    details=actual_diff,
                )

            # Independence boundary: remove the live continuation agent before child restore.
            cli.delete_agent("continued")
            if "continued" in {agent.id for agent in cli.list_agents()}:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Live continuation registration survived deletion.")

            child_restore = restore_image(adapter, image=child, target="child-restored")
            if not child_restore.get("validated") or child_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Child independent restore did not validate as P1.")
            restored = cli.show_agent("child-restored")
            restored_memory = (restored.workspace / "MEMORY.md").read_text(encoding="utf-8")
            if PARENT_MEMORY not in restored_memory or CONTINUED_MEMORY not in restored_memory:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Child restore lost inherited or continued memory state.")

            observation: dict[str, Any] = {
                "evidence_version": "agent-image-openclaw-continuation-observation/v0.1",
                "harness": {
                    "id": "openclaw",
                    "version": OPENCLAW_PIN.version,
                    "tag": OPENCLAW_PIN.tag,
                    "commit": OPENCLAW_PIN.commit,
                    "node": OPENCLAW_PIN.node,
                },
                "adapter": {"id": adapter.id, "version": adapter.version},
                "transition": {
                    "parent_fresh_restore_validated": True,
                    "mutation_surface": "workspace/MEMORY.md",
                    "mutation_kind": "direct documented workspace-memory file update",
                    "model_or_provider_call": False,
                    "child_build_source_stable": True,
                    "live_continuation_registration_deleted_before_child_restore": True,
                    "child_fresh_restore_validated": True,
                    "inherited_parent_memory_present": True,
                    "post_restore_memory_present": True,
                },
                "controls": {
                    "noop_refreeze_state_changed": noop_diff["layers"]["state_changed"],
                    "noop_refreeze_metadata_changed": noop_diff["layers"]["metadata_changed"],
                },
                "observed_delta": actual_diff["layers"],
                "parent_image_digest": parent_report["image_digest"],
                "child_image_digest": child_report["image_digest"],
            }
            evidence_bytes = canonical_json_bytes(observation)
            binding = build_continuation_binding(
                parent,
                child,
                transition_evidence=evidence_bytes,
                evidence_kind="openclaw-runtime-continuation-observation",
                evidence_media_type="application/json",
            )
            binding_path.write_bytes(json.dumps(binding, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
            round_tripped = json.loads(binding_path.read_text(encoding="utf-8"))
            verified = verify_continuation_binding(
                round_tripped,
                parent,
                child,
                transition_evidence=evidence_bytes,
            )
            if binding["state_delta"]["state_changed"] != actual_diff["layers"]["state_changed"]:
                raise AgentImageError("E_DIGEST_MISMATCH", "OpenClaw binding disagrees with generic state diff.")

            report = {
                "evidence_version": "agent-image-openclaw-continuation-ci/v0.1",
                "contract": observation["harness"],
                "parent_restore": {"validated": True, "portability": "P1"},
                "noop_control": {
                    "state_changed": noop_diff["layers"]["state_changed"],
                    "metadata_changed": noop_diff["layers"]["metadata_changed"],
                },
                "continued_delta": {
                    "state_changed": actual_diff["layers"]["state_changed"],
                    "metadata_changed": actual_diff["layers"]["metadata_changed"],
                    "added": actual_diff["layers"]["added"],
                    "removed": actual_diff["layers"]["removed"],
                },
                "child_restore": {"validated": True, "portability": "P1"},
                "binding": verified,
                "claim_boundary": {
                    "native_persistent_state_continuation_observed": True,
                    "exact_binding_verified": True,
                    "causal_development_verified": False,
                    "learning_verified": False,
                    "behavioral_retention_verified": False,
                },
            }
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        finally:
            for name in ("child-restored", "continued", "source"):
                _safe_delete(cli, name)
            shutil.rmtree(workspace_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except AgentImageError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
