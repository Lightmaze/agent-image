from __future__ import annotations

import re
from importlib import metadata
from typing import Any, Iterable

from agent_image.adapter_contract import ProductionAdapter
from agent_image.errors import AgentImageError


ENTRY_POINT_GROUP = "agent_image.adapters"
LOCATOR_PREFIX = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
REQUIRED_METHODS = ("capabilities", "inspect_source", "export", "native_restore")


def validate_adapter(adapter: Any, *, origin: str) -> ProductionAdapter:
    adapter_id = getattr(adapter, "id", None)
    version = getattr(adapter, "version", None)
    prefix = getattr(adapter, "locator_prefix", None)
    if not isinstance(adapter_id, str) or not adapter_id or not isinstance(version, str) or not version:
        raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Adapter from {origin} lacks a stable id or version.")
    if not isinstance(prefix, str) or not LOCATOR_PREFIX.fullmatch(prefix):
        raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Adapter {adapter_id} has an invalid locator_prefix.")
    missing = [name for name in REQUIRED_METHODS if not callable(getattr(adapter, name, None))]
    if missing:
        raise AgentImageError(
            "E_ADAPTER_NOT_FOUND",
            f"Adapter {adapter_id} is missing public contract methods: {', '.join(missing)}.",
        )
    capabilities = adapter.capabilities()
    if not isinstance(capabilities, dict) or not {
        "archive", "native_restore", "semantic_migration", "portability_level", "pinned_harness"
    }.issubset(capabilities):
        raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Adapter {adapter_id} capabilities are incomplete.")
    return adapter


def discover_adapters(*, disabled: Iterable[str] = ()) -> dict[str, ProductionAdapter]:
    disabled_set = set(disabled)
    discovered: dict[str, ProductionAdapter] = {}
    try:
        entry_points = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:
        entry_points = metadata.entry_points().select(group=ENTRY_POINT_GROUP)
    for entry_point in sorted(entry_points, key=lambda item: (item.name, item.value)):
        if entry_point.name in disabled_set:
            continue
        try:
            loaded = entry_point.load()
            candidate = loaded() if callable(loaded) else loaded
        except Exception as error:
            raise AgentImageError(
                "E_ADAPTER_NOT_FOUND",
                f"Could not load adapter entry point {entry_point.name}: {error}",
            ) from error
        adapter = validate_adapter(candidate, origin=f"entry-point:{entry_point.name}")
        prefix = adapter.locator_prefix
        if prefix != entry_point.name:
            raise AgentImageError(
                "E_ADAPTER_NOT_FOUND",
                f"Entry point {entry_point.name} must match adapter locator_prefix {prefix}.",
            )
        if prefix in discovered:
            raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Duplicate adapter locator prefix: {prefix}")
        discovered[prefix] = adapter
    return discovered
