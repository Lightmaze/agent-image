from __future__ import annotations

import copy
import io
import tarfile
from typing import Any, Mapping

from agent_image.adapter_contract import AdapterExport
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.native_capsule import inspect_native_capsule_bytes
from agent_image.native_classification import (
    NativeClassificationError,
    require_finalized_privacy_homogeneity,
    require_structured_native_portability,
)
from agent_image.native_privacy_plan import (
    NativePrivacyItem,
    NativePrivacyPlanError,
    coarsen_capsule_index_privacy,
    plan_atomic_restore_unit,
)


NATIVE_CAPSULE_MEDIA_TYPE = "application/vnd.agent-image.native-capsule+tar"
NATIVE_PRIVACY_PLANNING_SCHEMA = "agent-image-native-privacy-export/v0.1"


def _fail(message: str) -> AgentImageError:
    return AgentImageError("E_SPEC_INVALID", message)


def _layer_root_digest(layers: list[dict[str, Any]]) -> str:
    projection = [
        {
            "path": layer["path"],
            "digest": layer["digest"],
            "size": layer["size"],
            "media_type": layer["media_type"],
        }
        for layer in sorted(layers, key=lambda item: item["path"])
    ]
    return sha256_bytes(canonical_json_bytes(projection))


def _payload_items(index: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    items.extend(index["authoritative"])
    items.extend(item for item in index["derived"] if "path" in item)
    return items


def _pack_plain_tar(entries: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name in sorted(entries):
            data = entries[name]
            if not isinstance(data, bytes):
                raise _fail(f"Native capsule entry {name!r} is not bytes.")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _digest_map(index: Mapping[str, Any]) -> dict[str, str]:
    return {item["id"]: item["digest"] for item in _payload_items(index)}


def _unit_audit(
    *,
    source_outer_privacy: str,
    source_index: Mapping[str, Any],
    plan: Any,
    capsule_digest_before: str,
    capsule_digest_after: str | None,
    capsule_control_rewritten: bool,
) -> dict[str, Any]:
    return {
        "unit_id": plan.unit_id,
        "profile": dict(source_index["profile"]),
        "source_outer_privacy": source_outer_privacy,
        "requested_policy": plan.requested_policy,
        "effective_privacy": plan.effective_privacy,
        "action": plan.action,
        "exact_native_payload_bytes_preserved": plan.exact_native_bytes_preserved,
        "authoritative_payload_digests_preserved": plan.action == "preserve-whole",
        "capsule_control_rewritten": capsule_control_rewritten,
        "capsule_digest_before": capsule_digest_before,
        "capsule_digest_after": capsule_digest_after,
        "public_subset_requires_profile_projection": plan.public_subset_requires_profile_projection,
        "outcomes": [dict(item) for item in plan.outcomes],
    }


def finalize_structured_native_export(export: AdapterExport, *, policy: str) -> AdapterExport:
    if policy not in {"private", "public"}:
        raise _fail(f"Unsupported export policy: {policy}")

    structured = [
        layer
        for layer in export.manifest.get("layers", [])
        if layer.get("media_type") == NATIVE_CAPSULE_MEDIA_TYPE
    ]
    if not structured:
        return export

    if not isinstance(export.source_report, dict):
        raise _fail("Structured native export requires an object source report.")
    if "native_privacy_planning" in export.source_report:
        raise _fail("native_privacy_planning is finalizer-owned and must not be pre-authored by an adapter.")

    manifest = copy.deepcopy(export.manifest)
    payloads = dict(export.payloads)
    report = copy.deepcopy(export.source_report)
    audits: list[dict[str, Any]] = []
    kept_layers: list[dict[str, Any]] = []

    for layer in manifest.get("layers", []):
        if layer.get("media_type") != NATIVE_CAPSULE_MEDIA_TYPE:
            kept_layers.append(layer)
            continue
        if layer.get("kind") != "native":
            raise _fail(f"Structured native layer {layer.get('id', '<unknown>')} must use kind=native.")
        try:
            require_structured_native_portability(layer.get("portability"))
        except NativeClassificationError as error:
            raise _fail(f"Structured native layer {layer.get('id', '<unknown>')}: {error}") from error
        path = layer.get("path")
        if not isinstance(path, str) or path not in payloads:
            raise _fail(f"Structured native layer {layer.get('id', '<unknown>')} is missing payload bytes.")

        source_outer_privacy = str(layer.get("privacy", "unknown"))
        source_bytes = payloads[path]
        source_document = inspect_native_capsule_bytes(source_bytes)
        source_items = tuple(
            NativePrivacyItem(item_id=item["id"], source_privacy=item["privacy"])
            for item in _payload_items(source_document.index)
        )
        try:
            plan = plan_atomic_restore_unit(str(layer["id"]), source_items, requested_policy=policy)
        except NativePrivacyPlanError as error:
            code = "E_SECRET_DETECTED" if "secret material" in str(error) else "E_SPEC_INVALID"
            raise AgentImageError(code, f"Structured native privacy planning failed for layer {layer['id']}: {error}") from error
        before_digest = sha256_bytes(source_bytes)

        if plan.action == "redact-whole":
            payloads.pop(path, None)
            audits.append(
                _unit_audit(
                    source_outer_privacy=source_outer_privacy,
                    source_index=source_document.index,
                    plan=plan,
                    capsule_digest_before=before_digest,
                    capsule_digest_after=None,
                    capsule_control_rewritten=False,
                )
            )
            continue

        effective_index = coarsen_capsule_index_privacy(source_document.index, plan)
        rewritten_entries = dict(source_document.entries)
        rewritten_entries["capsule.json"] = canonical_json_bytes(effective_index) + b"\n"
        finalized_bytes = _pack_plain_tar(rewritten_entries)

        finalized_document = inspect_native_capsule_bytes(finalized_bytes)
        if _digest_map(finalized_document.index) != _digest_map(source_document.index):
            raise _fail(f"Structured native finalization changed payload digests for layer {layer['id']}.")
        embedded = {item["privacy"] for item in _payload_items(finalized_document.index)}
        try:
            require_finalized_privacy_homogeneity(plan.effective_privacy, embedded)
        except NativeClassificationError as error:
            raise _fail(
                f"Structured native finalization did not produce a valid effective classification "
                f"for layer {layer['id']}: {error}"
            ) from error

        payloads[path] = finalized_bytes
        layer["privacy"] = plan.effective_privacy
        layer["digest"] = sha256_bytes(finalized_bytes)
        layer["size"] = len(finalized_bytes)
        kept_layers.append(layer)
        audits.append(
            _unit_audit(
                source_outer_privacy=source_outer_privacy,
                source_index=source_document.index,
                plan=plan,
                capsule_digest_before=before_digest,
                capsule_digest_after=layer["digest"],
                capsule_control_rewritten=finalized_bytes != source_bytes,
            )
        )

    manifest["layers"] = kept_layers
    manifest["image"]["digest"] = _layer_root_digest(kept_layers)
    manifest["privacy"]["public_build"] = policy == "public"
    manifest["privacy"]["unresolved_items"] = sum(
        1 for layer in kept_layers if layer.get("privacy") == "unknown"
    )

    report["native_privacy_planning"] = {
        "schema": NATIVE_PRIVACY_PLANNING_SCHEMA,
        "authority": "agent-image-build-finalizer",
        "atomicity_default": "one-structured-capsule-layer-per-native-restore-unit",
        "policy": policy,
        "units": audits,
    }

    return AdapterExport(manifest=manifest, payloads=payloads, source_report=report)
