#!/usr/bin/env python3
"""Exercise pinned DSH parent -> restore -> profile patch update -> child continuation.

The experiment is no-model/no-provider. It derives the mutation from the real
pinned rc.6 composed tree rather than assuming current upstream configuration.
A no-op refreeze control runs before mutation, and the live continuation profile
is deleted before child restore.
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
from typing import Any

import yaml

from agent_image.adapters.dsh import DSH_PIN, DshAdapter, SubprocessDshCLI
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.continuation import build_continuation_binding, verify_continuation_binding
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import diff_images


MUTATION_MARKER = " [agent-image-continuation]"
SAFE_FIELDS = ("persona", "personaSuffix", "personaPrefix")


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


def _load_rows(data: bytes, *, label: str) -> list[dict[str, Any]]:
    try:
        value = yaml.safe_load(data.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"{label} is not safe-loadable UTF-8 YAML.") from error
    if not isinstance(value, list):
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"{label} must be a top-level YAML list.")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"{label} row {index} must be an object.")
        row_id = row.get("id")
        if isinstance(row_id, str):
            if row_id in ids:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"{label} contains duplicate row id {row_id!r}.")
            ids.add(row_id)
        rows.append(dict(row))
    return rows


def _rows_by_id(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get("id")
        if isinstance(row_id, str):
            if row_id in result:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"{label} contains duplicate row id {row_id!r}.")
            result[row_id] = row
    return result


def _select_safe_mutation(dump_rows: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
    rows = _rows_by_id(dump_rows, label="Pinned DSH composed config")
    row = rows.get("system-prompt")
    if row is None:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "Pinned DSH composed config has no allowlisted system-prompt row.",
            details={"known_ids": sorted(rows)},
        )
    config = row.get("config")
    if not isinstance(config, dict):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "Pinned DSH system-prompt config is not an object.")

    for field in SAFE_FIELDS:
        value = config.get(field)
        if isinstance(value, str) and value:
            mutated = copy.deepcopy(config)
            mutated[field] = value + MUTATION_MARKER
            return "system-prompt", field, mutated
    raise AgentImageError(
        "E_SOURCE_UNSUPPORTED",
        "Pinned DSH system-prompt row has no allowlisted string field.",
        details={"available_fields": sorted(str(key) for key in config)},
    )


def _write_profile_patch(profile: Path, row_id: str, mutated_config: dict[str, Any]) -> tuple[bytes, bytes]:
    patch_path = profile / "cordis.patch.yml"
    before = patch_path.read_bytes()
    patch_rows = _load_rows(before, label="Profile cordis.patch.yml")
    replacement = {"id": row_id, "config": mutated_config}

    updated: list[dict[str, Any]] = []
    replaced = False
    for row in patch_rows:
        if row.get("id") == row_id:
            candidate = copy.deepcopy(row)
            candidate["config"] = copy.deepcopy(mutated_config)
            updated.append(candidate)
            replaced = True
        else:
            updated.append(copy.deepcopy(row))
    if not replaced:
        updated.append(replacement)

    rendered = yaml.safe_dump(
        updated,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    ).encode("utf-8")
    patch_path.write_bytes(rendered)
    return before, rendered


def _assert_composed_mutation(before: bytes, after: bytes, *, row_id: str, field: str) -> None:
    before_rows = _rows_by_id(_load_rows(before, label="Pre-mutation composed config"), label="before")
    after_rows = _rows_by_id(_load_rows(after, label="Post-mutation composed config"), label="after")
    if set(before_rows) != set(after_rows):
        raise AgentImageError(
            "E_NATIVE_INCOMPATIBLE",
            "DSH profile mutation changed composed row inventory.",
            details={"before": sorted(before_rows), "after": sorted(after_rows)},
        )

    for other_id in sorted(set(before_rows) - {row_id}):
        if before_rows[other_id] != after_rows[other_id]:
            raise AgentImageError(
                "E_NATIVE_INCOMPATIBLE",
                "DSH profile mutation changed an unrelated composed row.",
                details={"row_id": other_id},
            )

    before_row = before_rows[row_id]
    after_row = after_rows[row_id]
    before_nonconfig = {key: value for key, value in before_row.items() if key != "config"}
    after_nonconfig = {key: value for key, value in after_row.items() if key != "config"}
    if before_nonconfig != after_nonconfig:
        raise AgentImageError(
            "E_NATIVE_INCOMPATIBLE",
            "DSH profile mutation changed system-prompt row metadata.",
            details={"before": before_nonconfig, "after": after_nonconfig},
        )

    before_config = before_row.get("config")
    after_config = after_row.get("config")
    if not isinstance(before_config, dict) or not isinstance(after_config, dict):
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH system-prompt config ceased to be an object.")
    if set(before_config) != set(after_config):
        raise AgentImageError(
            "E_NATIVE_INCOMPATIBLE",
            "DSH profile mutation changed system-prompt config field inventory.",
            details={"before": sorted(before_config), "after": sorted(after_config)},
        )
    for key in before_config:
        if key == field:
            expected = before_config[key] + MUTATION_MARKER
            if after_config[key] != expected:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH profile mutation did not produce the intended prompt-field value.",
                    details={"field": field, "expected": expected, "actual": after_config[key]},
                )
        elif before_config[key] != after_config[key]:
            raise AgentImageError(
                "E_NATIVE_INCOMPATIBLE",
                "DSH profile mutation changed an unintended system-prompt field.",
                details={"field": key},
            )


def _safe_delete(cli: SubprocessDshCLI, name: str) -> None:
    try:
        if cli.target_profile(name).is_dir():
            cli.delete_profile(name)
    except Exception:
        pass


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
        adapter = DshAdapter(cli)

        parent = images / "parent.aimg"
        noop_child = images / "noop-child.aimg"
        child = images / "child.aimg"
        binding_path = images / "continuation-binding.json"

        for name in ("continued", "child-restored"):
            _safe_delete(cli, name)

        try:
            source_profile = cli.show_profile("headless")
            inherited_package = (source_profile.path / "package.json").read_bytes()
            source_before = adapter.inspect_source("headless")["source"]["digest"]
            parent_report = build_image(adapter, source="headless", output=parent, policy="private")
            if adapter.inspect_source("headless")["source"]["digest"] != source_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "Parent build changed the DSH source profile.")

            parent_restore = restore_image(adapter, image=parent, target="continued")
            if not parent_restore.get("validated") or parent_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH parent fresh restore did not validate as P1.")

            continued = cli.show_profile("continued")
            if (continued.path / "package.json").read_bytes() != inherited_package:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Inherited DSH package manifest changed on parent restore.")

            continued_before = adapter.inspect_source("continued")["source"]["digest"]
            build_image(adapter, source="continued", output=noop_child, policy="private")
            if adapter.inspect_source("continued")["source"]["digest"] != continued_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "No-op child build changed the restored DSH profile.")
            noop_diff = diff_images(parent, noop_child)
            if noop_diff["layers"]["state_changed"]:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "Normalized DSH no-op refreeze still changed Agent state.",
                    details=noop_diff,
                )

            dump_before = cli.dump_config("continued")
            dump_rows = _load_rows(dump_before, label="Pinned DSH composed config")
            row_id, field, mutated_config = _select_safe_mutation(dump_rows)
            patch_before, patch_after = _write_profile_patch(continued.path, row_id, mutated_config)
            if patch_before == patch_after:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH profile patch mutation produced no byte change.")

            dump_after = cli.dump_config("continued")
            if dump_after == dump_before:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH profile patch did not change composed config.")
            _assert_composed_mutation(dump_before, dump_after, row_id=row_id, field=field)

            mutated_before = adapter.inspect_source("continued")["source"]["digest"]
            child_report = build_image(adapter, source="continued", output=child, policy="private")
            if adapter.inspect_source("continued")["source"]["digest"] != mutated_before:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "Child build changed the mutated DSH source profile.")

            actual_diff = diff_images(parent, child)
            if actual_diff["layers"]["state_changed"] != ["dsh-native-profile"]:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH continuation state delta was not exactly the typed native profile.",
                    details=actual_diff,
                )

            cli.delete_profile("continued")
            if cli.target_profile("continued").exists():
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Live DSH continuation profile survived deletion.")

            child_restore = restore_image(adapter, image=child, target="child-restored")
            if not child_restore.get("validated") or child_restore.get("portability") != "P1":
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH child independent restore did not validate as P1.")

            restored = cli.show_profile("child-restored")
            if (restored.path / "package.json").read_bytes() != inherited_package:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH child restore lost inherited profile state.")
            restored_patch = (restored.path / "cordis.patch.yml").read_bytes()
            if restored_patch != patch_after:
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH child restore changed the persisted profile patch.")
            restored_dump = cli.dump_config("child-restored")
            if restored_dump != dump_after:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH child restore did not reproduce the post-mutation composed config.",
                    details={"expected_digest": sha256_bytes(dump_after), "actual_digest": sha256_bytes(restored_dump)},
                )

            observation: dict[str, Any] = {
                "evidence_version": "agent-image-dsh-continuation-observation/v0.1",
                "harness": {
                    "id": "dsh",
                    "version": DSH_PIN.version,
                    "node": DSH_PIN.node,
                    "npm": DSH_PIN.npm,
                    "platform": "windows",
                },
                "adapter": {"id": adapter.id, "version": adapter.version},
                "transition": {
                    "parent_fresh_restore_validated": True,
                    "noop_discrimination_passed": True,
                    "mutation_surface": "profile/cordis.patch.yml",
                    "mutation_row_id": row_id,
                    "mutation_field": field,
                    "mutation_kind": "complete-config profile patch derived from pinned composed row",
                    "model_or_provider_call": False,
                    "pre_mutation_dump_digest": sha256_bytes(dump_before),
                    "post_mutation_dump_digest": sha256_bytes(dump_after),
                    "pre_mutation_patch_digest": sha256_bytes(patch_before),
                    "post_mutation_patch_digest": sha256_bytes(patch_after),
                    "child_build_source_stable": True,
                    "live_continuation_profile_deleted_before_child_restore": True,
                    "child_fresh_restore_validated": True,
                    "inherited_profile_state_present": True,
                    "post_restore_patch_present": True,
                    "post_restore_composed_config_equal": True,
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
                evidence_kind="dsh-runtime-continuation-observation",
                evidence_media_type="application/json",
            )
            binding_path.write_bytes(
                json.dumps(binding, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
            )
            round_tripped = json.loads(binding_path.read_text(encoding="utf-8"))
            verified = verify_continuation_binding(
                round_tripped,
                parent,
                child,
                transition_evidence=evidence_bytes,
            )
            if binding["state_delta"]["state_changed"] != actual_diff["layers"]["state_changed"]:
                raise AgentImageError("E_DIGEST_MISMATCH", "DSH binding disagrees with generic state diff.")

            report = {
                "evidence_version": "agent-image-dsh-continuation-ci/v0.1",
                "contract": observation["harness"],
                "parent_restore": {"validated": True, "portability": "P1"},
                "noop_control": {
                    "state_changed": noop_diff["layers"]["state_changed"],
                    "metadata_changed": noop_diff["layers"]["metadata_changed"],
                },
                "mutation": {
                    "surface": "profile/cordis.patch.yml",
                    "row_id": row_id,
                    "field": field,
                    "pre_dump_digest": sha256_bytes(dump_before),
                    "post_dump_digest": sha256_bytes(dump_after),
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
                    "persistent_profile_state_continuation_observed": True,
                    "semantic_composed_config_mutation_observed": True,
                    "exact_binding_verified": True,
                    "causal_development_verified": False,
                    "learning_verified": False,
                    "behavioral_retention_verified": False,
                },
            }
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        finally:
            for name in ("child-restored", "continued"):
                _safe_delete(cli, name)
            shutil.rmtree(dsh_home, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except AgentImageError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
