from __future__ import annotations

from typing import Any


class AgentImageError(Exception):
    """A stable, machine-readable protocol or CLI failure."""

    def __init__(self, code: str, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"error": {"code": self.code, "message": self.message}}
        if self.details is not None:
            value["error"]["details"] = self.details
        return value

