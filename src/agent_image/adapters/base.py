from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ExportedImage:
    manifest: dict[str, Any]
    payloads: dict[str, bytes]
    source_report: dict[str, Any]


class AgentImageAdapter(Protocol):
    id: str
    version: str

    def inspect_source(self, source: Path) -> dict[str, Any]: ...

    def export(self, source: Path, policy: str) -> ExportedImage: ...

    def capabilities(self) -> dict[str, Any]: ...

