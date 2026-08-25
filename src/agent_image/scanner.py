from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

import yaml


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
    if name == ".env" or name == "auth.json":
        return f"forbidden secret filename {name}"
    if name.startswith("credentials") or "token" in name:
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
    structured = media_type in {"application/json", "application/yaml", "text/yaml"} or suffix in {".json", ".yaml", ".yml"}
    if not structured:
        return []
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text) if suffix == ".json" or media_type == "application/json" else yaml.safe_load(text)
    except (UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError):
        return []
    return _secret_key_paths(value)

