#!/usr/bin/env python3
"""Diagnose pinned DSH restore-witness drift without relaxing P1 acceptance.

This probe deliberately does not call a softened restore path. It builds a real
parent Image, materializes only the image's captured profile files into a fresh
receiver profile, asks pinned DSH for a new --dump-config witness, and compares
that witness structurally with the integrity-bound source witness.

It never evaluates !!js. The result is diagnostic evidence only: raw or semantic
agreement here does not change DshAdapter.native_restore acceptance.

The probe also records a receiver-local acquisition witness for the installed DSH
runtime. npm is treated as acquisition provenance, while the exact resolved
package-lock graph is hashed separately. This avoids treating a package-manager
version as if it were Agent state or a receiver runtime state commitment.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agent_image.adapters.dsh import (
    DSH_NATIVE_MEDIA_TYPE,
    DSH_PIN,
    DshAdapter,
    SubprocessDshCLI,
    _read_native,
    _source_items,
    _write_profile,
)
from agent_image.adapters.dsh_witness import compare_witness
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image
from agent_image.image_archive import load_image


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


def _native_snapshot(parent_image: Path) -> tuple[dict[str, bytes], bytes]:
    document = load_image(parent_image)
    native_layers = [
        layer
        for layer in document.manifest["layers"]
        if layer["kind"] == "native" and layer["media_type"] == DSH_NATIVE_MEDIA_TYPE
    ]
    if len(native_layers) != 1:
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Expected one pinned DSH native layer in diagnostic image.")
    entries = _read_native(document.entries[native_layers[0]["path"]])
    expected_dump = entries.pop("meta/dump-config.yml", None)
    entries.pop("meta/profile.json", None)
    if expected_dump is None:
        raise AgentImageError("E_IMAGE_CORRUPT", "Diagnostic parent image has no DSH dump witness.")
    profile_entries = {
        path.removeprefix("profile/"): data
        for path, data in entries.items()
        if path.startswith("profile/")
    }
    if len(profile_entries) != len(entries):
        raise AgentImageError("E_IMAGE_CORRUPT", "Diagnostic DSH native layer has an unknown root entry.")
    return profile_entries, expected_dump


def _runtime_lock_witness(lockfile: Path) -> dict[str, object]:
    try:
        raw = lockfile.read_bytes()
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "DSH receiver-local package-lock witness is missing or invalid JSON.",
        ) from error
    if not isinstance(value, dict):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH package-lock witness must be a JSON object.")
    lockfile_version = value.get("lockfileVersion")
    packages = value.get("packages")
    if not isinstance(lockfile_version, int) or not isinstance(packages, dict):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH package-lock witness lacks lockfileVersion/packages.")
    root = packages.get("")
    if not isinstance(root, dict):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH package-lock witness lacks a root package record.")
    dependencies = root.get("dependencies")
    if not isinstance(dependencies, dict) or dependencies.get("@deepseek-ai/dsh") != DSH_PIN.version:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "DSH package-lock witness does not pin the expected top-level DSH version.",
            details={"expected": DSH_PIN.version, "actual": dependencies.get("@deepseek-ai/dsh") if isinstance(dependencies, dict) else None},
        )
    canonical = canonical_json_bytes(value)
    return {
        "lockfile_version": lockfile_version,
        "package_records": len(packages),
        "raw_digest": sha256_bytes(raw),
        "semantic_digest": sha256_bytes(canonical),
    }


def run(
    node: str,
    dsh_bin_js: str,
    *,
    acquisition_npm_version: str,
    runtime_lockfile: Path,
) -> dict[str, object]:
    acquisition = _runtime_lock_witness(runtime_lockfile)
    acquisition.update(
        {
            "tool": "npm",
            "tool_version": acquisition_npm_version,
            "method": "receiver-local prefix install",
            "top_level": f"@deepseek-ai/dsh@{DSH_PIN.version}",
        }
    )

    with tempfile.TemporaryDirectory(prefix="agent-image-dsh-witness-") as temporary:
        root = Path(temporary)
        dsh_home = root / "dsh-home"
        dsh_home.mkdir(parents=True, exist_ok=True)
        _bootstrap_shipped_headless(node, dsh_bin_js, dsh_home)

        cli = SubprocessDshCLI(
            binary=dsh_bin_js,
            node_binary=node,
            dsh_home=dsh_home,
            environment={"DSH_TELEMETRY_DISABLED": "1", "NO_COLOR": "1"},
        )
        if cli.version() != DSH_PIN.version:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Unexpected pinned DSH version in witness diagnostic.")

        adapter = DshAdapter(cli)
        parent_image = root / "parent.aimg"
        build_image(adapter, source="headless", output=parent_image, policy="private")
        profile_entries, expected_dump = _native_snapshot(parent_image)

        target = "diagnostic-restored"
        target_path = cli.target_profile(target)
        if target_path.exists():
            raise AgentImageError("E_TARGET_EXISTS", "Diagnostic receiver profile already exists.")

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            _write_profile(target_path, profile_entries)
            cli.show_profile(target)
            actual_dump = cli.dump_config(target)

            actual_items = _source_items(target_path)
            actual_files = {
                item.source.removeprefix("profile/"): item.data
                for item in actual_items.values()
                if item.item_type == "file" and item.data is not None
            }
            if actual_files != profile_entries:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "Witness diagnostic receiver files differ from captured profile bytes.",
                    details={"expected": sorted(profile_entries), "actual": sorted(actual_files)},
                )

            comparison = compare_witness(expected_dump, actual_dump)
            if comparison.get("parser_status") != "parsed":
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH witness diagnostic could not parse one side fail-closed.",
                    details=comparison,
                )

            return {
                "evidence_version": "agent-image-dsh-restore-witness-diagnostic/v0.2",
                "runtime": {
                    "dsh": DSH_PIN.version,
                    "node": subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip(),
                },
                "acquisition": acquisition,
                "adapter_metadata": {
                    "historical_tested_npm": DSH_PIN.npm,
                    "npm_enforced_by_adapter": False,
                },
                "materialization": {
                    "receiver_profile": target,
                    "profile_files_equal": True,
                },
                "witness": comparison,
                "claim_boundary": {
                    "diagnostic_only": True,
                    "p1_acceptance_changed": False,
                    "continuation_ready": False,
                },
            }
        finally:
            if target_path.exists():
                shutil.rmtree(target_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsh-bin-js", required=True)
    parser.add_argument("--node-binary", required=True)
    parser.add_argument("--acquisition-npm-version", required=True)
    parser.add_argument("--runtime-lockfile", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(
            args.node_binary,
            args.dsh_bin_js,
            acquisition_npm_version=args.acquisition_npm_version,
            runtime_lockfile=args.runtime_lockfile,
        )
    except AgentImageError as error:
        print(json.dumps({"error": error.to_dict()}, ensure_ascii=False, sort_keys=True), file=os.sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
