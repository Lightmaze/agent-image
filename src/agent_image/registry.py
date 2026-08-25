from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from agent_image.canonical import sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.paths import validate_archive_path


REGISTRY_VERSION = "agent-image-registry/v0.1"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
ENTRY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
EVIDENCE_STATUS = {"verified", "negative", "unverified"}
CLAIM_STATUS = {"verified", "negative", "unverified", "not_applicable"}
LEVELS = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
ALLOWED_URI_SCHEMES = {"https", "oci", "withheld"}


def _fail(message: str, *, details: Any | None = None) -> None:
    raise AgentImageError("E_REGISTRY_INVALID", message, details=details)


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{path} must be an object.")
    return value


def _keys(value: Mapping[str, Any], *, required: set[str], path: str) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing or unknown:
        _fail(f"{path} field mismatch.", details={"missing": missing, "unknown": unknown})


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{path} must be a non-empty string.")
    return value


def _digest(value: Any, path: str) -> str:
    text = _string(value, path)
    if not DIGEST.fullmatch(text):
        _fail(f"{path} must be a lowercase SHA-256 digest.")
    return text


def _repo_root(registry_path: Path) -> Path:
    resolved = registry_path.resolve()
    for candidate in resolved.parents:
        if (candidate / "pyproject.toml").is_file() and (candidate / "registry").is_dir():
            return candidate
    _fail("Could not locate the repository root for registry evidence validation.")


def validate_registry(path: Path, *, repository_root: Path | None = None) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"Registry is unavailable or invalid UTF-8 JSON: {error}")
    root = repository_root.resolve() if repository_root is not None else _repo_root(path)
    registry = _object(value, "/")
    _keys(registry, required={"registry_version", "updated_at", "entries"}, path="/")
    if registry["registry_version"] != REGISTRY_VERSION:
        _fail(f"/registry_version must equal {REGISTRY_VERSION!r}.")
    updated_at = _string(registry["updated_at"], "/updated_at")
    try:
        datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError as error:
        _fail(f"/updated_at must be an RFC-3339 date-time: {error}")
    entries = registry["entries"]
    if not isinstance(entries, list) or not entries:
        _fail("/entries must be a non-empty array.")

    ids: set[str] = set()
    artifact_digests: set[str] = set()
    statuses = {status: 0 for status in sorted(EVIDENCE_STATUS)}
    privacy_counts = {privacy: 0 for privacy in ("public", "private", "unknown")}
    harness_counts: dict[str, int] = {}
    for index, raw_entry in enumerate(entries):
        item_path = f"/entries/{index}"
        entry = _object(raw_entry, item_path)
        _keys(
            entry,
            required={
                "id", "name", "artifact_uri", "artifact_digest", "source_harness", "license",
                "privacy", "lineage", "portability", "evidence",
            },
            path=item_path,
        )
        entry_id = _string(entry["id"], f"{item_path}/id")
        if not ENTRY_ID.fullmatch(entry_id) or entry_id in ids:
            _fail(f"{item_path}/id is invalid or duplicated: {entry_id}")
        ids.add(entry_id)
        _string(entry["name"], f"{item_path}/name")
        artifact_uri = _string(entry["artifact_uri"], f"{item_path}/artifact_uri")
        uri = urlparse(artifact_uri)
        if uri.scheme not in ALLOWED_URI_SCHEMES or not uri.netloc:
            _fail(f"{item_path}/artifact_uri has an unsupported or incomplete scheme.")
        artifact_digest = _digest(entry["artifact_digest"], f"{item_path}/artifact_digest")
        if artifact_digest in artifact_digests:
            _fail(f"Duplicate artifact digest: {artifact_digest}")
        artifact_digests.add(artifact_digest)
        harness = _object(entry["source_harness"], f"{item_path}/source_harness")
        _keys(harness, required={"id", "version"}, path=f"{item_path}/source_harness")
        harness_id = _string(harness["id"], f"{item_path}/source_harness/id")
        _string(harness["version"], f"{item_path}/source_harness/version")
        harness_counts[harness_id] = harness_counts.get(harness_id, 0) + 1
        _string(entry["license"], f"{item_path}/license")

        privacy = _object(entry["privacy"], f"{item_path}/privacy")
        _keys(privacy, required={"classification", "distribution"}, path=f"{item_path}/privacy")
        classification = privacy.get("classification")
        distribution = privacy.get("distribution")
        if classification not in privacy_counts or distribution not in {"publishable", "withheld"}:
            _fail(f"{item_path}/privacy contains an invalid value.")
        if classification != "public" and distribution == "publishable":
            _fail(f"{item_path} cannot publish non-public or unknown state.")
        if uri.scheme == "withheld" and distribution != "withheld":
            _fail(f"{item_path} withheld URI requires withheld distribution.")
        if uri.scheme != "withheld" and distribution == "withheld":
            _fail(f"{item_path} withheld distribution requires a withheld URI.")
        privacy_counts[classification] += 1

        lineage = _object(entry["lineage"], f"{item_path}/lineage")
        _keys(lineage, required={"parent_digests"}, path=f"{item_path}/lineage")
        parents = lineage["parent_digests"]
        if not isinstance(parents, list) or len(parents) != len(set(parents)):
            _fail(f"{item_path}/lineage/parent_digests must be a unique array.")
        for parent_index, parent in enumerate(parents):
            parent_digest = _digest(parent, f"{item_path}/lineage/parent_digests/{parent_index}")
            if parent_digest == artifact_digest:
                _fail(f"{item_path} cannot name itself as a lineage parent.")

        portability = _object(entry["portability"], f"{item_path}/portability")
        _keys(
            portability,
            required={"level", "archive", "native_restore", "semantic_migration", "behavioral"},
            path=f"{item_path}/portability",
        )
        level = portability.get("level")
        if level not in LEVELS or any(portability.get(field) not in CLAIM_STATUS for field in (
            "archive", "native_restore", "semantic_migration", "behavioral"
        )):
            _fail(f"{item_path}/portability contains an invalid value.")
        required_claims = ["archive", "native_restore", "semantic_migration", "behavioral"][: LEVELS[level] + 1]
        if any(portability[field] != "verified" for field in required_claims):
            _fail(f"{item_path} portability level {level} exceeds verified evidence.")

        evidence = _object(entry["evidence"], f"{item_path}/evidence")
        _keys(evidence, required={"status", "path", "digest", "scope"}, path=f"{item_path}/evidence")
        status = evidence.get("status")
        if status not in EVIDENCE_STATUS:
            _fail(f"{item_path}/evidence/status is invalid.")
        if status == "negative" and "negative" not in portability.values():
            _fail(f"{item_path} negative evidence must be reflected in portability.")
        evidence_path_text = validate_archive_path(_string(evidence["path"], f"{item_path}/evidence/path"))
        evidence_path = (root / Path(*evidence_path_text.split("/"))).resolve()
        try:
            evidence_path.relative_to(root)
        except ValueError:
            _fail(f"{item_path}/evidence/path escapes the repository root.")
        if not evidence_path.is_file() or evidence_path.is_symlink():
            _fail(f"{item_path}/evidence/path is not a regular repository file.")
        declared_evidence_digest = _digest(evidence["digest"], f"{item_path}/evidence/digest")
        actual_evidence_digest = sha256_bytes(evidence_path.read_bytes())
        if actual_evidence_digest != declared_evidence_digest:
            _fail(
                f"{item_path} evidence digest mismatch.",
                details={"declared": declared_evidence_digest, "actual": actual_evidence_digest},
            )
        _string(evidence["scope"], f"{item_path}/evidence/scope")
        statuses[status] += 1

    return {
        "valid": True,
        "registry_version": REGISTRY_VERSION,
        "entries": len(entries),
        "evidence_status": statuses,
        "privacy": privacy_counts,
        "source_harnesses": dict(sorted(harness_counts.items())),
        "artifact_digests_unique": True,
        "evidence_digests_verified": True,
    }
