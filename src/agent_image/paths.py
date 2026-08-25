from __future__ import annotations

import re

from agent_image.errors import AgentImageError


_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def validate_archive_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise AgentImageError("E_UNSAFE_PATH", "Archive path must be a non-empty string.")
    if "\x00" in path or "\\" in path:
        raise AgentImageError("E_UNSAFE_PATH", f"Archive path is not portable: {path!r}.")
    if path.startswith("/") or _DRIVE_PREFIX.match(path):
        raise AgentImageError("E_UNSAFE_PATH", f"Archive path must be relative: {path!r}.")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise AgentImageError("E_UNSAFE_PATH", f"Archive path contains an unsafe segment: {path!r}.")
    return path

