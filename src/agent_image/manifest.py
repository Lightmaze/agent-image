from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from agent_image.errors import AgentImageError
from agent_image.paths import validate_archive_path


SPEC = "agent-image/v0.1"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
LAYER_KINDS = {
    "identity",
    "skills",
    "memory",
    "experience",
    "workspace",
    "development",
    "evaluation",
    "native",
    "other",
}
PRIVACY_CLASSES = {"public", "private", "secret", "unknown"}
PORTABILITY_CLASSES = {"portable", "adapter-specific", "opaque"}
EVALUATION_STATUSES = {"self_reported", "reproduced", "third_party"}
DEVELOPMENT_METHODS = {"habitat", "self_play", "human_coaching", "rl", "sft", "mixed", "unknown"}


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        return load_yaml_bytes(path.read_bytes())
    except OSError as error:
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"Cannot read YAML file {path}: {error}") from error


def load_yaml_bytes(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8", errors="strict")
        value = yaml.safe_load(text)
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise AgentImageError("E_SPEC_INVALID", f"Invalid UTF-8 YAML: {error}") from error
    if not isinstance(value, dict):
        raise AgentImageError("E_SPEC_INVALID", "YAML document must be an object.")
    return value


def dump_yaml(value: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(
        dict(value),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).encode("utf-8")


def _fail(message: str, *, details: Any | None = None) -> None:
    raise AgentImageError("E_SPEC_INVALID", message, details=details)


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{path} must be an object.")
    return value


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{path} must be a non-empty string.")
    return value


def _digest(value: Any, path: str) -> str:
    text = _nonempty(value, path)
    if not DIGEST.fullmatch(text):
        _fail(f"{path} must be a lowercase SHA-256 digest.")
    return text


def _keys(value: Mapping[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        _fail(f"{path} is missing required fields: {', '.join(missing)}.")
    if unknown:
        _fail(f"{path} contains unknown fields: {', '.join(unknown)}.")


def _date_time(value: Any, path: str) -> None:
    text = _nonempty(value, path)
    if "T" not in text or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", text):
        _fail(f"{path} must be an RFC-3339 date-time with an explicit offset.")
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        _fail(f"{path} must be an ISO-8601 date-time: {error}")


def validate_manifest(value: Mapping[str, Any]) -> None:
    manifest = _object(value, "/")
    _keys(
        manifest,
        {"spec", "image", "runtime", "layers", "development", "evaluations", "lineage", "privacy", "provenance", "extensions"},
        {"spec", "image", "layers", "privacy", "provenance"},
        "/",
    )
    if manifest["spec"] != SPEC:
        _fail(f"/spec must equal {SPEC!r}.")

    image = _object(manifest["image"], "/image")
    _keys(image, {"name", "version", "created_at", "digest", "description"}, {"name", "version", "created_at", "digest"}, "/image")
    _nonempty(image["name"], "/image/name")
    _nonempty(image["version"], "/image/version")
    _date_time(image["created_at"], "/image/created_at")
    _digest(image["digest"], "/image/digest")

    if "runtime" in manifest:
        runtime = _object(manifest["runtime"], "/runtime")
        _keys(runtime, {"harness", "adapter", "model"}, set(), "/runtime")
        for field in ("harness", "adapter"):
            if field in runtime:
                identifier = _object(runtime[field], f"/runtime/{field}")
                _keys(identifier, {"id", "version"}, {"id", "version"}, f"/runtime/{field}")
                _nonempty(identifier["id"], f"/runtime/{field}/id")
                _nonempty(identifier["version"], f"/runtime/{field}/version")
        if "model" in runtime:
            model = _object(runtime["model"], "/runtime/model")
            _keys(model, {"provider", "family", "id", "digest"}, set(), "/runtime/model")
            for field in ("provider", "family", "id"):
                if field in model:
                    _nonempty(model[field], f"/runtime/model/{field}")
            if "digest" in model:
                _digest(model["digest"], "/runtime/model/digest")

    layers = manifest["layers"]
    if not isinstance(layers, list):
        _fail("/layers must be an array.")
    ids: set[str] = set()
    paths: set[str] = set()
    for index, raw_layer in enumerate(layers):
        path = f"/layers/{index}"
        layer = _object(raw_layer, path)
        _keys(
            layer,
            {"id", "kind", "media_type", "path", "digest", "size", "privacy", "portability", "source"},
            {"id", "kind", "media_type", "path", "digest", "size", "privacy", "portability"},
            path,
        )
        layer_id = _nonempty(layer["id"], f"{path}/id")
        if layer_id in ids:
            _fail(f"Duplicate layer id {layer_id!r}.")
        ids.add(layer_id)
        kind = layer["kind"]
        if kind not in LAYER_KINDS:
            _fail(f"{path}/kind is not a v0.1 layer kind.")
        archive_path = validate_archive_path(_nonempty(layer["path"], f"{path}/path"))
        if not archive_path.startswith(f"layers/{kind}/"):
            _fail(f"{path}/path must be below layers/{kind}/.")
        if archive_path in paths:
            _fail(f"Duplicate layer path {archive_path!r}.")
        paths.add(archive_path)
        _nonempty(layer["media_type"], f"{path}/media_type")
        _digest(layer["digest"], f"{path}/digest")
        if not isinstance(layer["size"], int) or isinstance(layer["size"], bool) or layer["size"] < 0:
            _fail(f"{path}/size must be a non-negative integer.")
        if layer["privacy"] not in PRIVACY_CLASSES:
            _fail(f"{path}/privacy is invalid.")
        if layer["portability"] not in PORTABILITY_CLASSES:
            _fail(f"{path}/portability is invalid.")
        if "source" in layer:
            source = _object(layer["source"], f"{path}/source")
            _keys(source, {"path", "origin", "reason"}, set(), f"{path}/source")
            for key, field_value in source.items():
                _nonempty(field_value, f"{path}/source/{key}")

    privacy = _object(manifest["privacy"], "/privacy")
    _keys(privacy, {"default", "public_build", "unresolved_items"}, {"default", "public_build", "unresolved_items"}, "/privacy")
    if privacy["default"] != "private":
        _fail("/privacy/default must be 'private'.")
    if not isinstance(privacy["public_build"], bool):
        _fail("/privacy/public_build must be a boolean.")
    if not isinstance(privacy["unresolved_items"], int) or isinstance(privacy["unresolved_items"], bool) or privacy["unresolved_items"] < 0:
        _fail("/privacy/unresolved_items must be a non-negative integer.")

    provenance = _object(manifest["provenance"], "/provenance")
    _keys(provenance, {"source_harness", "source_adapter", "export_tool_version", "source_uri"}, {"source_harness", "source_adapter", "export_tool_version"}, "/provenance")
    for key, field_value in provenance.items():
        _nonempty(field_value, f"/provenance/{key}")

    development = manifest.get("development")
    if development is not None:
        development = _object(development, "/development")
        if development.get("method") not in DEVELOPMENT_METHODS:
            _fail("/development/method is missing or invalid.")

    evaluations = manifest.get("evaluations", [])
    if not isinstance(evaluations, list):
        _fail("/evaluations must be an array.")
    for index, evaluation in enumerate(evaluations):
        evaluation = _object(evaluation, f"/evaluations/{index}")
        _nonempty(evaluation.get("id"), f"/evaluations/{index}/id")
        if evaluation.get("status") not in EVALUATION_STATUSES:
            _fail(f"/evaluations/{index}/status is invalid.")
