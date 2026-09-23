#!/usr/bin/env python3
"""Real pinned DSH no-op refreeze acceptance gate.

This deliberately performs no profile mutation after fresh P1 restore. It asks a
narrow question required by the continuation-ready adapter profile: does a
producer-instance rename alone change the carried Agent-state delta?

The normalized writer must make the answer no. Any native-member difference or
state_changed layer is a hard failure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_image.adapters.dsh import (
    DSH_PIN,
    DSH_NATIVE_MEDIA_TYPE,
    DshAdapter,
    SubprocessDshCLI,
    _read_native,
)
from agent_image.canonical import sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import diff_images, load_image


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


def _native_entries(image: Path) -> dict[str, bytes]:
    document = load_image(image)
    layers = [
        layer
        for layer in document.manifest["layers"]
        if layer["kind"] == "native" and layer["media_type"] == DSH_NATIVE_MEDIA_TYPE
    ]
    if len(layers) != 1:
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Expected exactly one DSH native layer.")
    return _read_native(document.entries[layers[0]["path"]])


def _metadata(entries: dict[str, bytes]) -> dict[str, object]:
    try:
        value = json.loads(entries["meta/profile.json"].decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", "DSH native profile metadata is missing or invalid.") from error
    if not isinstance(value, dict):
        raise AgentImageError("E_IMAGE_CORRUPT", "DSH native profile metadata must be an object.")
    return value


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsh-bin-js", required=True)
    parser.add_argument("--node-binary", required=True)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="agent-image-dsh-noop-") as temporary:
        root = Path(temporary).resolve()
        dsh_home = root / "dsh-home"
        images = root / "images"
        dsh_home.mkdir(parents=True)
        images.mkdir(parents=True)

        _bootstrap_shipped_headless(args.node_binary, args.dsh_bin_js, dsh_home)

        cli = SubprocessDshCLI(
            binary=args.dsh_bin_js,
            node_binary=args.node_binary,
            dsh_home=dsh_home,
        )
        if cli.version() != DSH_PIN.version:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Pinned DSH version mismatch in no-op refreeze CI.")
        adapter = DshAdapter(cli)

        parent = images / "parent.aimg"
        noop_child = images / "noop-child.aimg"

        try:
            source_before = adapter.inspect_source("headless")["source"]["digest"]
            build_image(adapter, source="headless", output=parent, policy="private")
            if adapter.inspect_source("headless")["source"]["digest"] != source_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "Parent build changed the DSH source profile.")

            parent_restore = restore_image(adapter, image=parent, target="continued")
            if not parent_restore.get("validated") or parent_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH parent fresh restore did not validate as P1.")

            continued_before = adapter.inspect_source("continued")["source"]["digest"]
            build_image(adapter, source="continued", output=noop_child, policy="private")
            if adapter.inspect_source("continued")["source"]["digest"] != continued_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "No-op child build changed the restored DSH profile.")

            noop_diff = diff_images(parent, noop_child)
            parent_entries = _native_entries(parent)
            child_entries = _native_entries(noop_child)
            if set(parent_entries) != set(child_entries):
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH no-op refreeze changed native member inventory.",
                    details={"parent": sorted(parent_entries), "child": sorted(child_entries)},
                )

            changed_members = sorted(
                path for path in parent_entries if parent_entries[path] != child_entries[path]
            )
            parent_meta = _metadata(parent_entries)
            child_meta = _metadata(child_entries)

            if changed_members:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "Normalized DSH no-op refreeze changed native bytes.",
                    details={"changed_members": changed_members},
                )
            if "source_name" in parent_meta or "source_name" in child_meta:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "Normalized DSH native metadata still contains producer identity.",
                    details={"parent_meta": parent_meta, "child_meta": child_meta},
                )
            if parent_meta != child_meta:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH no-op refreeze changed restore-witness metadata.",
                    details={"parent": parent_meta, "child": child_meta},
                )

            state_changed = noop_diff["layers"]["state_changed"]
            if state_changed:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "Normalized DSH no-op refreeze still reports Agent-state changes.",
                    details=noop_diff,
                )

            report = {
                "evidence_version": "agent-image-dsh-noop-refreeze-normalized/v0.1",
                "contract": {
                    "package": f"@deepseek-ai/dsh@{DSH_PIN.version}",
                    "node": DSH_PIN.node,
                    "npm": DSH_PIN.npm,
                    "platform": "windows",
                },
                "parent_restore": {"validated": True, "portability": "P1"},
                "noop_control": {
                    "state_changed": state_changed,
                    "metadata_changed": noop_diff["layers"]["metadata_changed"],
                    "changed_native_members": changed_members,
                },
                "native_metadata": {
                    "parent": parent_meta,
                    "child": child_meta,
                    "producer_identity_absent": True,
                    "restore_witness_equal": True,
                    "parent_meta_digest": sha256_bytes(parent_entries["meta/profile.json"]),
                    "child_meta_digest": sha256_bytes(child_entries["meta/profile.json"]),
                },
                "finding": {
                    "producer_identity_inside_native_bytes": False,
                    "receiver_state_changed": False,
                    "current_raw_native_digest_truthful_for_noop": True,
                },
                "claim_boundary": {
                    "dsh_p1_revalidated": True,
                    "noop_discrimination_passed": True,
                    "continuation_ready": False,
                    "positive_mutation_not_run": True,
                    "causal_development_verified": False,
                    "behavioral_retention_verified": False,
                },
            }
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        finally:
            for name in ("continued",):
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
