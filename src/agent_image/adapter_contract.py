from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class AdapterExport:
    manifest: dict[str, Any]
    payloads: dict[str, bytes]
    source_report: dict[str, Any]


class ProductionAdapter(Protocol):
    id: str
    version: str

    def capabilities(self) -> dict[str, Any]: ...

    def inspect_source(self, source: str) -> dict[str, Any]: ...

    def export(
        self,
        source: str,
        policy: str,
        *,
        include_experience: bool = False,
        include_workspace: bool = False,
    ) -> AdapterExport: ...

    def native_restore(self, image: Any, target: str) -> dict[str, Any]: ...


def require_absent_output(output: Path) -> None:
    if output.exists():
        from agent_image.errors import AgentImageError

        raise AgentImageError("E_TARGET_EXISTS", f"Output already exists: {output}")
