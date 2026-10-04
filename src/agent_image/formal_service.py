from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from agent_image.adapter_contract import ProductionAdapter
from agent_image.build_plan import create_build_plan
from agent_image.canonical import sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import load_image, publish_image
from agent_image.prepared_build import prepare_build_candidate, publish_prepared_candidate
from agent_image.prepared_workspace import (
    prepare_build_workspace,
    publish_prepared_workspace,
    recover_prepared_workspace,
)


def plan_build(
    adapter: ProductionAdapter,
    *,
    source: str,
    policy: str,
    include_experience: bool = False,
    include_workspace: bool = False,
) -> dict[str, Any]:
    return create_build_plan(
        adapter,
        source=source,
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
    )


def build_image(
    adapter: ProductionAdapter,
    *,
    source: str,
    output: Path,
    policy: str = "private",
    include_experience: bool = False,
    include_workspace: bool = False,
    approved_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    inspection = adapter.inspect_source(source)
    if inspection.get("structured_native") is not None:
        raise AgentImageError(
            "E_PREPARED_REQUIRED",
            "Structured-native publication requires prepare-build followed by publish-prepared.",
            details={
                "adapter": {"id": str(adapter.id), "version": str(adapter.version)},
                "approved_plan_supplied": approved_plan is not None,
            },
        )

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
        "publication_mode": "direct-legacy",
    }


def prepare_image(
    adapter: ProductionAdapter,
    *,
    source: str,
    prepared_path: Path,
    policy: str = "private",
    include_experience: bool = False,
    include_workspace: bool = False,
    approved_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = prepare_build_candidate(
        adapter,
        source=source,
        prepared_path=prepared_path,
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
        approved_plan=approved_plan,
    )
    return {
        "operation": "prepare-build",
        "prepared": str(prepared_path.resolve()),
        "receipt": receipt,
        "publication_mode": "prepared-exact-subject",
        "final_published": False,
    }


def publish_prepared_image(
    *,
    prepared_path: Path,
    receipt: Mapping[str, Any],
    output: Path,
) -> dict[str, Any]:
    return publish_prepared_candidate(prepared_path, receipt=receipt, output=output)


def prepare_image_workspace(
    adapter: ProductionAdapter,
    *,
    source: str,
    workspace: Path,
    policy: str = "private",
    include_experience: bool = False,
    include_workspace: bool = False,
    approved_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return prepare_build_workspace(
        adapter,
        source=source,
        workspace=workspace,
        policy=policy,
        include_experience=include_experience,
        include_workspace=include_workspace,
        approved_plan=approved_plan,
    )


def recover_prepared_image_workspace(*, workspace: Path) -> dict[str, Any]:
    return recover_prepared_workspace(workspace)


def publish_prepared_workspace_image(*, workspace: Path, output: Path) -> dict[str, Any]:
    return publish_prepared_workspace(workspace, output=output)


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
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "Source Agent Image changed during semantic migration.",
            details={"before": before, "after": after},
        )
    report["source_archive_digest_before"] = before
    report["source_archive_digest_after"] = after
    report["source_immutable"] = True
    return report
