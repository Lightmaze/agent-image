"""Agent Image reference implementation."""

__version__ = "0.1.0-alpha.2"

from agent_image.adapter_contract import (
    AdapterCapabilities,
    AdapterExport,
    ExportPlan,
    MigrationPlan,
    OperationReport,
    ProductionAdapter,
    RestorePlan,
    SourceInventory,
    SourceInventoryItem,
)
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import layer_root_digest

__all__ = [
    "AdapterCapabilities",
    "AdapterExport",
    "AgentImageError",
    "ExportPlan",
    "MigrationPlan",
    "OperationReport",
    "ProductionAdapter",
    "RestorePlan",
    "SourceInventory",
    "SourceInventoryItem",
    "canonical_json_bytes",
    "layer_root_digest",
    "sha256_bytes",
]
