from __future__ import annotations

import io
import json
import re
import tarfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from agent_image.canonical import sha256_bytes
from agent_image.container import MAX_ENTRIES, MAX_FILE_SIZE, MAX_TOTAL_SIZE
from agent_image.errors import AgentImageError
from agent_image.paths import validate_archive_path
from agent_image.native_realization import (
    NATIVE_REALIZATION_MEDIA_TYPE,
    NativeRealizationError,
    parse_native_realization_bytes,
    validate_realization_references,
)


NATIVE_CAPSULE_SPEC = "agent-image-native-capsule/v0.1"
_CAPTURE_CONSISTENCY = {"quiesced", "transaction-boundary", "flush-only", "best-effort", "unknown"}
_HISTORY_FIDELITY = {"raw-append-log", "compacted-current-state", "snapshot-current-state", "unknown"}
_SOURCE_MUTATION = {"none", "flush-only", "backend-snapshot-metadata", "other-declared"}
_PRIVACY = {"public", "private", "secret", "unknown"}
_REBUILD_POLICY = {"omit-and-rebuild", "preserve-sidecar", "not-rebuildable"}
_EXTERNAL_KIND = {"model", "corpus", "service", "object-store", "runtime-resource", "other"}
_REQUIREMENT_KIND = {"runtime", "model", "embedding", "retrieval", "filesystem", "service", "credential", "resource", "other"}
_REQUIRED_FOR = {"inspect", "query", "write", "restore", "behavioral-eval"}
_CLOSURE_POLICY = {"whole-store", "slice", "profile-defined", "unknown"}
_NATIVE_RESTORE = {"exact-authoritative", "state-compatible-with-loss", "archive-only", "unknown"}
_RETRIEVAL = {"exact-retrieval-replay", "retrieval-compatible", "semantic-migration", "structural-restore-only", "unknown"}
_HISTORY = {"audit-complete", "current-state-only", "partial", "unknown"}
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class _DuplicateJsonKey(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJsonKey(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


@dataclass(frozen=True)
class NativeCapsuleDocument:
    index: dict[str, Any]
    entries: dict[str, bytes]
    authoritative: dict[str, bytes]
    derived: dict[str, bytes]


def _spec_error(message: str) -> AgentImageError:
    return AgentImageError("E_SPEC_INVALID", message)


def _require_object(value: Any, where: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _spec_error(f"{where} must be an object.")
    extras = sorted(set(value) - keys)
    if extras:
        raise _spec_error(f"{where} has unsupported fields: {', '.join(extras)}")
    return value


def _required(value: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in value:
        raise _spec_error(f"Missing required field {where}.{key}.")
    return value[key]


def _nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise _spec_error(f"{where} must be a non-empty string.")
    return value


def _enum(value: Any, allowed: set[str], where: str) -> str:
    text = _nonempty_string(value, where)
    if text not in allowed:
        raise _spec_error(f"{where} has unsupported value: {text}")
    return text


def _bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise _spec_error(f"{where} must be boolean.")
    return value


def _integer(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _spec_error(f"{where} must be a non-negative integer.")
    return value


def _string_list(value: Any, where: str, *, allowed: set[str] | None = None, min_items: int = 0) -> list[str]:
    if not isinstance(value, list) or len(value) < min_items:
        raise _spec_error(f"{where} must be a list with at least {min_items} item(s).")
    out: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _nonempty_string(item, f"{where}[{index}]")
        if allowed is not None and text not in allowed:
            raise _spec_error(f"{where}[{index}] has unsupported value: {text}")
        if text in seen:
            raise _spec_error(f"{where} contains a duplicate value: {text}")
        seen.add(text)
        out.append(text)
    return out


def _validate_datetime(value: Any, where: str) -> None:
    text = _nonempty_string(value, where)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise _spec_error(f"{where} must be an RFC 3339-style date-time.") from error
    if "T" not in text or parsed.tzinfo is None:
        raise _spec_error(f"{where} must include time and timezone information.")


def _validate_native_object(value: Any, where: str) -> dict[str, Any]:
    item = _require_object(value, where, {"id", "path", "media_type", "digest", "size", "privacy"})
    for key in ("id", "path", "media_type", "digest", "size", "privacy"):
        _required(item, key, where)
    _nonempty_string(item["id"], f"{where}.id")
    validate_archive_path(_nonempty_string(item["path"], f"{where}.path"))
    _nonempty_string(item["media_type"], f"{where}.media_type")
    digest = _nonempty_string(item["digest"], f"{where}.digest")
    if not _DIGEST_RE.fullmatch(digest):
        raise _spec_error(f"{where}.digest must be a lowercase sha256 digest.")
    _integer(item["size"], f"{where}.size")
    _enum(item["privacy"], _PRIVACY, f"{where}.privacy")
    return item


def _validate_derived_object(value: Any, where: str) -> dict[str, Any]:
    item = _require_object(
        value,
        where,
        {"id", "path", "media_type", "digest", "size", "privacy", "rebuild"},
    )
    _nonempty_string(_required(item, "id", where), f"{where}.id")
    rebuild = _require_object(
        _required(item, "rebuild", where),
        f"{where}.rebuild",
        {"policy", "source_ids", "realization_ref"},
    )
    policy = _enum(
        _required(rebuild, "policy", f"{where}.rebuild"),
        _REBUILD_POLICY,
        f"{where}.rebuild.policy",
    )
    _string_list(
        _required(rebuild, "source_ids", f"{where}.rebuild"),
        f"{where}.rebuild.source_ids",
    )
    if "realization_ref" in rebuild:
        _nonempty_string(rebuild["realization_ref"], f"{where}.rebuild.realization_ref")

    payload_keys = {"path", "media_type", "digest", "size", "privacy"}
    present = payload_keys & set(item)
    if present and present != payload_keys:
        missing = sorted(payload_keys - present)
        raise _spec_error(
            f"{where} has an incomplete preserved payload descriptor: missing {', '.join(missing)}"
        )
    if policy in {"preserve-sidecar", "not-rebuildable"} and present != payload_keys:
        raise _spec_error(f"{where} with rebuild policy {policy} must carry a payload descriptor.")
    if present:
        _validate_native_object(
            {"id": item["id"], **{key: item[key] for key in payload_keys}},
            where,
        )
    return item


def _validate_capsule_index(value: Any) -> dict[str, Any]:
    index = _require_object(
        value,
        "capsule.json",
        {
            "spec",
            "profile",
            "capture",
            "authoritative",
            "derived",
            "external_references",
            "receiver",
            "closure",
            "compatibility",
        },
    )
    required_top = {
        "spec",
        "profile",
        "capture",
        "authoritative",
        "derived",
        "external_references",
        "receiver",
        "closure",
        "compatibility",
    }
    for key in required_top:
        _required(index, key, "capsule.json")
    if index["spec"] != NATIVE_CAPSULE_SPEC:
        raise _spec_error(f"Unsupported native capsule spec: {index['spec']!r}")

    profile = _require_object(index["profile"], "capsule.json.profile", {"id", "version"})
    _nonempty_string(
        _required(profile, "id", "capsule.json.profile"),
        "capsule.json.profile.id",
    )
    _nonempty_string(
        _required(profile, "version", "capsule.json.profile"),
        "capsule.json.profile.version",
    )

    capture = _require_object(
        index["capture"],
        "capsule.json.capture",
        {
            "captured_at",
            "consistency",
            "write_barrier",
            "flushed",
            "history_fidelity",
            "source_mutation",
        },
    )
    for key in (
        "captured_at",
        "consistency",
        "write_barrier",
        "flushed",
        "history_fidelity",
        "source_mutation",
    ):
        _required(capture, key, "capsule.json.capture")
    _validate_datetime(capture["captured_at"], "capsule.json.capture.captured_at")
    consistency = _enum(
        capture["consistency"],
        _CAPTURE_CONSISTENCY,
        "capsule.json.capture.consistency",
    )
    write_barrier = _bool(
        capture["write_barrier"],
        "capsule.json.capture.write_barrier",
    )
    flushed = _bool(capture["flushed"], "capsule.json.capture.flushed")
    if consistency == "quiesced" and not write_barrier:
        raise _spec_error("quiesced capture must declare write_barrier=true.")
    if consistency == "flush-only" and not flushed:
        raise _spec_error("flush-only capture must declare flushed=true.")
    _enum(
        capture["history_fidelity"],
        _HISTORY_FIDELITY,
        "capsule.json.capture.history_fidelity",
    )
    _enum(
        capture["source_mutation"],
        _SOURCE_MUTATION,
        "capsule.json.capture.source_mutation",
    )

    authoritative = index["authoritative"]
    if not isinstance(authoritative, list) or not authoritative:
        raise _spec_error("capsule.json.authoritative must contain at least one object.")
    auth_items = [
        _validate_native_object(item, f"capsule.json.authoritative[{i}]")
        for i, item in enumerate(authoritative)
    ]

    derived = index["derived"]
    if not isinstance(derived, list):
        raise _spec_error("capsule.json.derived must be a list.")
    derived_items = [
        _validate_derived_object(item, f"capsule.json.derived[{i}]")
        for i, item in enumerate(derived)
    ]

    ids: set[str] = set()
    paths: set[str] = set()
    for where, items in (("authoritative", auth_items), ("derived", derived_items)):
        for item in items:
            item_id = item["id"]
            if item_id in ids:
                raise _spec_error(f"Duplicate native object id: {item_id}")
            ids.add(item_id)
            if "path" in item:
                path = item["path"]
                if path == "capsule.json" or path in paths:
                    raise _spec_error(f"Duplicate or reserved native payload path: {path}")
                paths.add(path)

    authoritative_ids = {item["id"] for item in auth_items}
    for i, item in enumerate(derived_items):
        for source_id in item["rebuild"]["source_ids"]:
            if source_id not in authoritative_ids:
                raise _spec_error(
                    f"capsule.json.derived[{i}].rebuild.source_ids references "
                    f"non-authoritative object: {source_id}"
                )

    try:
        validate_realization_references(derived_items)
    except NativeRealizationError as error:
        raise _spec_error(str(error)) from error

    externals = index["external_references"]
    if not isinstance(externals, list):
        raise _spec_error("capsule.json.external_references must be a list.")
    external_ids: set[str] = set()
    for i, raw in enumerate(externals):
        where = f"capsule.json.external_references[{i}]"
        item = _require_object(
            raw,
            where,
            {"id", "kind", "locator_hint", "required_for_restore"},
        )
        item_id = _nonempty_string(_required(item, "id", where), f"{where}.id")
        if item_id in external_ids:
            raise _spec_error(f"Duplicate external reference id: {item_id}")
        external_ids.add(item_id)
        _enum(_required(item, "kind", where), _EXTERNAL_KIND, f"{where}.kind")
        if "locator_hint" in item:
            _nonempty_string(item["locator_hint"], f"{where}.locator_hint")
        _bool(
            _required(item, "required_for_restore", where),
            f"{where}.required_for_restore",
        )

    receiver = _require_object(
        index["receiver"],
        "capsule.json.receiver",
        {"authority_rebind_required", "secrets_embedded", "requirements"},
    )
    if _required(
        receiver,
        "authority_rebind_required",
        "capsule.json.receiver",
    ) is not True:
        raise _spec_error("capsule.json.receiver.authority_rebind_required must be true.")
    if _required(receiver, "secrets_embedded", "capsule.json.receiver") is not False:
        raise _spec_error("capsule.json.receiver.secrets_embedded must be false.")
    requirements = _required(receiver, "requirements", "capsule.json.receiver")
    if not isinstance(requirements, list):
        raise _spec_error("capsule.json.receiver.requirements must be a list.")
    requirement_ids: set[str] = set()
    for i, raw in enumerate(requirements):
        where = f"capsule.json.receiver.requirements[{i}]"
        item = _require_object(raw, where, {"id", "kind", "required_for"})
        item_id = _nonempty_string(_required(item, "id", where), f"{where}.id")
        if item_id in requirement_ids:
            raise _spec_error(f"Duplicate receiver requirement id: {item_id}")
        requirement_ids.add(item_id)
        _enum(_required(item, "kind", where), _REQUIREMENT_KIND, f"{where}.kind")
        _string_list(
            _required(item, "required_for", where),
            f"{where}.required_for",
            allowed=_REQUIRED_FOR,
            min_items=1,
        )

    closure = _require_object(
        index["closure"],
        "capsule.json.closure",
        {"policy", "checks"},
    )
    _enum(
        _required(closure, "policy", "capsule.json.closure"),
        _CLOSURE_POLICY,
        "capsule.json.closure.policy",
    )
    _string_list(
        _required(closure, "checks", "capsule.json.closure"),
        "capsule.json.closure.checks",
    )

    compatibility = _require_object(
        index["compatibility"],
        "capsule.json.compatibility",
        {"native_restore", "retrieval", "history", "loss_report_required"},
    )
    _enum(
        _required(compatibility, "native_restore", "capsule.json.compatibility"),
        _NATIVE_RESTORE,
        "capsule.json.compatibility.native_restore",
    )
    _enum(
        _required(compatibility, "retrieval", "capsule.json.compatibility"),
        _RETRIEVAL,
        "capsule.json.compatibility.retrieval",
    )
    _enum(
        _required(compatibility, "history", "capsule.json.compatibility"),
        _HISTORY,
        "capsule.json.compatibility.history",
    )
    _bool(
        _required(compatibility, "loss_report_required", "capsule.json.compatibility"),
        "capsule.json.compatibility.loss_report_required",
    )

    return index


def _read_tar_entries(data: bytes) -> dict[str, bytes]:
    if not isinstance(data, bytes):
        raise AgentImageError("E_IMAGE_CORRUPT", "Native capsule must be bytes.")
    entries: dict[str, bytes] = {}
    total_size = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            for member in archive:
                path = validate_archive_path(member.name)
                if path in entries:
                    raise AgentImageError(
                        "E_IMAGE_CORRUPT",
                        f"Duplicate native capsule path: {path}",
                    )
                if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE}:
                    raise AgentImageError(
                        "E_UNSAFE_PATH",
                        f"Only ordinary regular files are allowed in native capsules: {path}",
                    )
                if member.size < 0 or member.size > MAX_FILE_SIZE:
                    raise AgentImageError(
                        "E_IMAGE_CORRUPT",
                        f"Native capsule entry size is outside limits: {path}",
                    )
                total_size += member.size
                if len(entries) + 1 > MAX_ENTRIES or total_size > MAX_TOTAL_SIZE:
                    raise AgentImageError(
                        "E_IMAGE_CORRUPT",
                        "Native capsule exceeds safety limits.",
                    )
                stream = archive.extractfile(member)
                if stream is None:
                    raise AgentImageError(
                        "E_IMAGE_CORRUPT",
                        f"Cannot read native capsule entry: {path}",
                    )
                payload = stream.read(MAX_FILE_SIZE + 1)
                if len(payload) != member.size:
                    raise AgentImageError(
                        "E_IMAGE_CORRUPT",
                        f"Native capsule entry size mismatch: {path}",
                    )
                entries[path] = payload
    except AgentImageError:
        raise
    except (OSError, EOFError, tarfile.TarError) as error:
        raise AgentImageError(
            "E_IMAGE_CORRUPT",
            f"Cannot read native capsule tar: {error}",
        ) from error
    return entries


def inspect_native_capsule_bytes(data: bytes) -> NativeCapsuleDocument:
    """Safely inspect and verify one uncompressed native-capsule tar from bytes.

    The function never extracts paths to disk. Validation and digest checks are
    performed against the same captured member bytes returned to the caller.
    """
    entries = _read_tar_entries(data)
    if "capsule.json" not in entries:
        raise AgentImageError(
            "E_IMAGE_CORRUPT",
            "Native capsule is missing root capsule.json.",
        )
    try:
        raw_index = json.loads(
            entries["capsule.json"].decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as error:
        raise AgentImageError(
            "E_IMAGE_CORRUPT",
            f"Invalid capsule.json: {error}",
        ) from error
    index = _validate_capsule_index(raw_index)

    authoritative: dict[str, bytes] = {}
    derived: dict[str, bytes] = {}
    declared_paths: set[str] = set()
    for item in index["authoritative"]:
        declared_paths.add(item["path"])
    for item in index["derived"]:
        if "path" in item:
            declared_paths.add(item["path"])

    actual_payloads = set(entries) - {"capsule.json"}
    missing = sorted(declared_paths - actual_payloads)
    undeclared = sorted(actual_payloads - declared_paths)
    if missing:
        raise AgentImageError(
            "E_IMAGE_CORRUPT",
            f"Missing declared native capsule payloads: {', '.join(missing)}",
        )
    if undeclared:
        raise AgentImageError(
            "E_IMAGE_CORRUPT",
            f"Undeclared native capsule payloads: {', '.join(undeclared)}",
        )

    for bucket_name, output in (
        ("authoritative", authoritative),
        ("derived", derived),
    ):
        for item in index[bucket_name]:
            path = item.get("path")
            if path is None:
                continue
            payload = entries[path]
            if len(payload) != item["size"] or sha256_bytes(payload) != item["digest"]:
                raise AgentImageError(
                    "E_DIGEST_MISMATCH",
                    f"Native capsule digest or size mismatch: {path}",
                )
            if (
                bucket_name == "derived"
                and item.get("media_type") == NATIVE_REALIZATION_MEDIA_TYPE
            ):
                try:
                    realization = parse_native_realization_bytes(payload)
                except NativeRealizationError as error:
                    raise AgentImageError("E_SPEC_INVALID", str(error)) from error
                if realization["profile"] != index["profile"]:
                    raise AgentImageError(
                        "E_SPEC_INVALID",
                        f"Native realization profile mismatch for {item['id']}: "
                        f"{realization['profile']!r} != {index['profile']!r}",
                    )
            output[item["id"]] = payload

    return NativeCapsuleDocument(
        index=index,
        entries=entries,
        authoritative=authoritative,
        derived=derived,
    )
