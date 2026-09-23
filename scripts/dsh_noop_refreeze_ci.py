#!/usr/bin/env python3
"""Real pinned DSH normalization + persistent-state continuation experiment.

This is a discriminative implementation experiment for issue #12. It keeps the
production DSH reader untouched and applies the proposed one-field writer
normalization in a local adapter subclass: remove capture-only `source_name`
from `meta/profile.json` while preserving bundles/dependencies and dump-config
restore witnesses inside the hashed native layer.

The run proves whether that minimal correction is sufficient for a rename-only
no-op refreeze and then exercises one semantically valid profile-owned
`cordis.patch.yml` mutation through independent child restore and the existing
external Continuation Evidence Binding. It does not claim learning, causal
development, behavioral retention, P3, or a production adapter fix.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_image.adapter_contract import AdapterExport
from agent_image.adapters.dsh import (
    DSH_PIN,
    DSH_NATIVE_MEDIA_TYPE,
    DshAdapter,
    SubprocessDshCLI,
    _read_native,
    _tar_bytes,
)
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.continuation import build_continuation_binding, verify_continuation_binding
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import diff_images, layer_root_digest, load_image


MUTATION_MARKER = "Agent Image DSH continuation marker v1."
# Pinned rc.6 (release merge fb826987...) defines the headless system-prompt
# row with one full `persona` config field, not the later personaPrefix/
# personaSuffix split on current upstream. The profile patch replaces the row's
# complete config and changes only that rc.6 persona string.
PROFILE_PATCH = f"""- id: system-prompt
  config:
    persona: >-
      You are a coding agent powered by the {{{{model}}}} model. Your working directory is {{{{cwd}}}}. {MUTATION_MARKER}
""".encode("utf-8")


def _bootstrap_shipped_headless(node: str, dsh_bin_js: str, dsh_home: Path) -> None:
    env = dict(os.environ)
    env["DSH_HOME"] = str(dsh_home)
    env["DSH_TELEMETRY_DISABLED"] = "1"
    env["NO_COLOR"] = "1"
    result = subprocess.run(
        [node, dsh_bin_js, "--profile", "headless", "--dump-config"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "Pinned DSH could not initialize/dump the shipped headless profile.",
            details={"exit_code": result.returncode, "stderr": result.stderr[-4000:]},
        )
    if not result.stdout.strip():
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "Pinned DSH returned an empty headless config dump.")


def _native_layer(document: object) -> dict[str, object]:
    layers = [
        layer
        for layer in document.manifest["layers"]
        if layer["kind"] == "native" and layer["media_type"] == DSH_NATIVE_MEDIA_TYPE
    ]
    if len(layers) != 1:
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Expected exactly one DSH native layer.")
    return layers[0]


def _native_entries(image: Path) -> dict[str, bytes]:
    document = load_image(image)
    layer = _native_layer(document)
    return _read_native(document.entries[layer["path"]])


def _metadata(entries: dict[str, bytes]) -> dict[str, object]:
    try:
        value = json.loads(entries["meta/profile.json"].decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", "DSH native profile metadata is missing or invalid.") from error
    if not isinstance(value, dict):
        raise AgentImageError("E_IMAGE_CORRUPT", "DSH native profile metadata must be an object.")
    return value


class CandidateNormalizedDshAdapter(DshAdapter):
    """Issue #12 writer correction, intentionally local to this real-runtime experiment."""

    def export(
        self,
        source: str,
        policy: str,
        *,
        include_experience: bool = False,
        include_workspace: bool = False,
    ) -> AdapterExport:
        exported = super().export(
            source,
            policy,
            include_experience=include_experience,
            include_workspace=include_workspace,
        )
        if policy != "private":
            return exported

        manifest = copy.deepcopy(exported.manifest)
        payloads = dict(exported.payloads)
        native_layers = [
            layer
            for layer in manifest["layers"]
            if layer["kind"] == "native" and layer["media_type"] == DSH_NATIVE_MEDIA_TYPE
        ]
        if len(native_layers) != 1:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Candidate normalization expected one DSH native layer.")
        layer = native_layers[0]
        entries = _read_native(payloads[layer["path"]])
        metadata = _metadata(entries)
        metadata.pop("source_name", None)
        entries["meta/profile.json"] = canonical_json_bytes(metadata) + b"\n"
        native = _tar_bytes(entries)
        payloads[layer["path"]] = native
        layer["digest"] = sha256_bytes(native)
        layer["size"] = len(native)
        manifest["image"]["digest"] = layer_root_digest(manifest["layers"])
        return AdapterExport(manifest=manifest, payloads=payloads, source_report=exported.source_report)


def _build_checked(adapter: DshAdapter, source: str, output: Path) -> None:
    before = adapter.inspect_source(source)["source"]["digest"]
    build_image(adapter, source=source, output=output, policy="private")
    after = adapter.inspect_source(source)["source"]["digest"]
    if before != after:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "DSH build changed its source profile.",
            details={"source": source, "before": before, "after": after},
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsh-bin-js", required=True)
    parser.add_argument("--node-binary", required=True)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="agent-image-dsh-continuation-") as temporary:
        root = Path(temporary).resolve()
        dsh_home = root / "dsh-home"
        images = root / "images"
        dsh_home.mkdir(parents=True)
        images.mkdir(parents=True)

        _bootstrap_shipped_headless(args.node_binary, args.dsh_bin_js, dsh_home)
        cli = SubprocessDshCLI(binary=args.dsh_bin_js, node_binary=args.node_binary, dsh_home=dsh_home)
        if cli.version() != DSH_PIN.version:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Pinned DSH version mismatch in continuation CI.")

        legacy_adapter = DshAdapter(cli)
        adapter = CandidateNormalizedDshAdapter(cli)
        legacy = images / "legacy.aimg"
        parent = images / "parent.aimg"
        noop_child = images / "noop-child.aimg"
        child = images / "child.aimg"

        cleanup_profiles = ["legacy-restored", "continued", "child-restored"]
        try:
            # Backward-reader witness: current production reader must still accept
            # an old-style capsule containing source_name.
            _build_checked(legacy_adapter, "headless", legacy)
            legacy_meta = _metadata(_native_entries(legacy))
            if legacy_meta.get("source_name") != "headless":
                raise AgentImageError("E_IMAGE_CORRUPT", "Legacy DSH artifact did not contain source_name as expected.")
            legacy_restore = restore_image(adapter, image=legacy, target="legacy-restored")
            if not legacy_restore.get("validated") or legacy_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Legacy DSH capsule did not restore through normalized reader.")
            cli.delete_profile("legacy-restored")

            # Candidate normalized writer: producer identity must not enter native bytes.
            _build_checked(adapter, "headless", parent)
            parent_entries = _native_entries(parent)
            parent_meta = _metadata(parent_entries)
            if "source_name" in parent_meta:
                raise AgentImageError("E_IMAGE_CORRUPT", "Candidate normalized parent still contains source_name.")

            parent_restore = restore_image(adapter, image=parent, target="continued")
            if not parent_restore.get("validated") or parent_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH parent fresh restore did not validate as P1.")

            # No-op discrimination gate after instance rename.
            before_dump = cli.dump_config("continued")
            _build_checked(adapter, "continued", noop_child)
            noop_diff = diff_images(parent, noop_child)
            if noop_diff["layers"]["state_changed"]:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "Candidate DSH normalization still reports state change on rename-only no-op refreeze.",
                    details=noop_diff,
                )
            child_noop_entries = _native_entries(noop_child)
            if set(parent_entries) != set(child_noop_entries):
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Normalized no-op changed native member inventory.")
            changed_noop_members = sorted(
                path for path in parent_entries if parent_entries[path] != child_noop_entries[path]
            )
            if changed_noop_members:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "Normalized no-op changed committed native bytes.",
                    details={"changed_members": changed_noop_members},
                )

            # Positive persistent profile-state mutation. The pinned rc.6 release
            # defines system-prompt.config as a single `persona` field. We replace
            # that full row config and change only the persona text. No model or
            # provider call is made.
            continued = cli.show_profile("continued")
            patch_path = continued.path / "cordis.patch.yml"
            patch_path.write_bytes(PROFILE_PATCH)
            mutated_dump = cli.dump_config("continued")
            if mutated_dump == before_dump or MUTATION_MARKER.encode("utf-8") not in mutated_dump:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH profile patch mutation was not observable through official --dump-config.",
                )

            _build_checked(adapter, "continued", child)
            child_diff = diff_images(parent, child)
            if child_diff["layers"]["state_changed"] != ["dsh-native-profile"]:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH persistent profile mutation produced unexpected Agent-state delta.",
                    details=child_diff,
                )

            # Independence boundary: remove live source before child restore.
            cli.delete_profile("continued")
            if cli.target_profile("continued").exists():
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Live DSH continuation source survived deletion.")
            child_restore = restore_image(adapter, image=child, target="child-restored")
            if not child_restore.get("validated") or child_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH child independent restore did not validate as P1.")
            restored = cli.show_profile("child-restored")
            if (restored.path / "cordis.patch.yml").read_bytes() != PROFILE_PATCH:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH child restore lost the post-restore profile patch.")
            restored_dump = cli.dump_config("child-restored")
            if restored_dump != mutated_dump or MUTATION_MARKER.encode("utf-8") not in restored_dump:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH child restore changed the composed config witness.")

            transition_observation = {
                "evidence_version": "agent-image-dsh-continuation-observation/v0.1",
                "contract": {
                    "package": f"@deepseek-ai/dsh@{DSH_PIN.version}",
                    "release_merge": "fb82698709c39f1860b0ab0ed147e1fa30c1d5d0",
                    "node": DSH_PIN.node,
                    "npm": DSH_PIN.npm,
                    "platform": "windows",
                },
                "legacy_reader": {"validated": True, "portability": "P1", "source_name_accepted": True},
                "parent_restore": {"validated": True, "portability": "P1"},
                "noop_control": {
                    "state_changed": noop_diff["layers"]["state_changed"],
                    "metadata_changed": noop_diff["layers"]["metadata_changed"],
                    "changed_native_members": changed_noop_members,
                },
                "mutation": {
                    "surface": "profile/cordis.patch.yml",
                    "kind": "profile-owned full-row rc.6 system-prompt persona override",
                    "marker": MUTATION_MARKER,
                    "observable_through_dump_config": True,
                    "state_changed": child_diff["layers"]["state_changed"],
                    "behavior_executed": False,
                },
                "independence": {
                    "live_continuation_source_deleted_before_child_restore": True,
                    "child_restore_validated": True,
                    "profile_patch_preserved": True,
                    "dump_config_preserved": True,
                },
                "claim_boundary": {
                    "persistent_profile_state_continuation_observed": True,
                    "causal_development_verified": False,
                    "behavioral_retention_verified": False,
                    "learning_verified": False,
                    "p3_verified": False,
                },
            }
            evidence_bytes = canonical_json_bytes(transition_observation)
            binding = build_continuation_binding(
                parent,
                child,
                transition_evidence=evidence_bytes,
                evidence_kind="dsh-runtime-continuation-observation",
                evidence_media_type="application/json",
            )
            binding_verification = verify_continuation_binding(
                binding,
                parent,
                child,
                transition_evidence=evidence_bytes,
            )
            if not binding_verification.get("valid"):
                raise AgentImageError("E_DIGEST_MISMATCH", "DSH continuation binding did not verify.")

            report = {
                "evidence_version": "agent-image-dsh-normalization-and-continuation/v0.1",
                "candidate_writer_normalization": {
                    "removed_field": "meta/profile.json.source_name",
                    "restore_witness_preserved": ["bundles", "dependencies", "meta/dump-config.yml"],
                    "legacy_reader_p1": True,
                },
                "noop_control": transition_observation["noop_control"],
                "persistent_profile_mutation": transition_observation["mutation"],
                "independence": transition_observation["independence"],
                "continuation_binding": binding_verification,
                "claim_boundary": transition_observation["claim_boundary"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        finally:
            for name in cleanup_profiles:
                try:
                    if cli.target_profile(name).exists():
                        cli.delete_profile(name)
                except Exception:
                    pass
            shutil.rmtree(dsh_home, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except AgentImageError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
