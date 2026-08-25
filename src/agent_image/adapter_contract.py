from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol


OutcomeAction = Literal["preserved", "transformed", "redacted", "unsupported", "dropped_by_user"]


@dataclass(frozen=True)
class AdapterCapabilities:
    archive: bool
    native_restore: bool
    semantic_migration: bool
    portability_level: str
    pinned_harness: dict[str, str]


@dataclass(frozen=True)
class SourceInventoryItem:
    id: str
    source: str
    privacy: str
    media_type: str


@dataclass(frozen=True)
class SourceInventory:
    adapter_id: str
    harness_id: str
    source_uri: str
    digest: str
    items: tuple[SourceInventoryItem, ...]


@dataclass(frozen=True)
class ExportPlan:
    source: SourceInventory
    policy: str
    outcomes: tuple[dict[str, Any], ...]
    requires_confirmation: bool = True


@dataclass(frozen=True)
class RestorePlan:
    adapter_id: str
    image_digest: str
    target_uri: str
    outcomes: tuple[dict[str, Any], ...]
    requires_confirmation: bool = True


@dataclass(frozen=True)
class MigrationPlan:
    source_image_digest: str
    source_harness: str
    target_uri: str
    outcomes: tuple[dict[str, Any], ...]
    requires_confirmation: bool = True


@dataclass(frozen=True)
class OperationReport:
    operation: str
    adapter_id: str
    inventory_count: int
    outcomes: tuple[dict[str, Any], ...]
    validated: bool
    portability: str


@dataclass(frozen=True)
class AdapterExport:
    manifest: dict[str, Any]
    payloads: dict[str, bytes]
    source_report: dict[str, Any]


class ProductionAdapter(Protocol):
    id: str
    version: str
    locator_prefix: str

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
