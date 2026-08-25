from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_image.adapter_contract import ProductionAdapter
from agent_image.canonical import sha256_bytes
from agent_image.image_archive import load_image, publish_image


def plan_build(adapter: ProductionAdapter, *, source: str, policy: str) -> dict[str, Any]:
    inspection = adapter.inspect_source(source)
    return {
        "operation": "build-plan",
        "adapter": inspection["adapter"],
        "source_harness": inspection["source_harness"],
        "source": inspection["source"],
        "inventory_count": inspection["inventory_count"],
        "policy": policy,
        "capabilities": inspection["capabilities"],
        "requires_confirmation": True,
    }


def build_image(
    adapter: ProductionAdapter,
    *,
    source: str,
    output: Path,
    policy: str = "private",
    include_experience: bool = False,
    include_workspace: bool = False,
) -> dict[str, Any]:
    exported = adapter.export(
        source,
        policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
    )
    publish_image(exported, output)
    return {
        "operation": "build",
        "adapter": {"id": adapter.id, "version": adapter.version},
        "output": str(output.resolve()),
        "image_digest": exported.manifest["image"]["digest"],
        "layers": len(exported.manifest["layers"]),
        "verified": True,
        "portability": "P0",
    }


def restore_image(adapter: ProductionAdapter, *, image: Path, target: str) -> dict[str, Any]:
    document = load_image(image)
    return adapter.native_restore(document, target)


def plan_migration(adapter: Any, *, image: Path, target: str) -> dict[str, Any]:
    document = load_image(image)
    return adapter.migration_plan(document, target)


def migrate_image(adapter: Any, *, image: Path, target: str) -> dict[str, Any]:
    before = sha256_bytes(image.read_bytes())
    document = load_image(image)
    report = adapter.semantic_migrate(document, target)
    after = sha256_bytes(image.read_bytes())
    if before != after:
        from agent_image.errors import AgentImageError

        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "Source Agent Image changed during semantic migration.",
            details={"before": before, "after": after},
        )
    report["source_archive_digest_before"] = before
    report["source_archive_digest_after"] = after
    report["source_immutable"] = True
    return report
