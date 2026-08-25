from __future__ import annotations

import json
import re
import tomllib
from pathlib import PurePosixPath
from typing import Any

import yaml

from agent_image.errors import AgentImageError


_SECRET_KEYS = {
    "apikey",
    "token",
    "accesstoken",
    "refreshtoken",
    "secret",
    "password",
    "credential",
    "credentials",
    "privatekey",
}


def secret_filename_reason(path: str) -> str | None:
    name = PurePosixPath(path.replace("\\", "/")).name.casefold()
    normalized_name = name.lstrip(".")
    if name == ".env" or name == "auth.json":
        return f"forbidden secret filename {name}"
    if normalized_name.startswith("credentials") or "token" in normalized_name:
        return f"credential/token filename {name}"
    if name.endswith((".pem", ".key")) or name in {"id_rsa", "id_ed25519"}:
        return f"private-key filename {name}"
    return None


def _normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _secret_key_paths(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _normalized_key(key) in _SECRET_KEYS:
                findings.append(child_path)
            findings.extend(_secret_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_secret_key_paths(child, f"{path}[{index}]"))
    return findings


def structured_secret_findings(path: str, media_type: str, data: bytes) -> list[str]:
    suffix = PurePosixPath(path).suffix.casefold()
    structured = media_type in {
        "application/json",
        "application/x-ndjson",
        "application/toml",
        "application/yaml",
        "text/yaml",
    } or suffix in {".json", ".jsonl", ".toml", ".yaml", ".yml"}
    if not structured:
        return []
    try:
        text = data.decode("utf-8", errors="strict")
        if suffix == ".jsonl" or media_type == "application/x-ndjson":
            value = [json.loads(line) for line in text.splitlines() if line.strip()]
        elif suffix == ".json" or media_type == "application/json":
            value = json.loads(text)
        elif suffix == ".toml" or media_type == "application/toml":
            value = tomllib.loads(text)
        else:
            value = yaml.safe_load(text)
    except (UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError, yaml.YAMLError) as error:
        raise AgentImageError(
            "E_SECRET_SCAN_FAILED",
            f"Structured content could not be safely scanned: {path}",
            details={"media_type": media_type, "reason": str(error)},
        ) from error
    return _secret_key_paths(value)
