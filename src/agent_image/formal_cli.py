from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from agent_image import __version__
from agent_image.adapters.hermes import HermesAdapter, SubprocessHermesCLI
from agent_image.adapters.openclaw import OpenClawAdapter, SubprocessOpenClawCLI
from agent_image.errors import AgentImageError
from agent_image.formal_service import (
    build_image,
    migrate_image,
    plan_build,
    plan_migration,
    restore_image,
)
from agent_image.image_archive import diff_images, inspect_image, redact_image, verify_image


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--quiet", action="store_true", help="Suppress successful output.")
    parser.add_argument("--verbose", action="store_true", help="Emit adapter diagnostics when available.")
    parser.add_argument("--report", type=Path, help="Write the operation result as UTF-8 JSON without overwriting.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-image", description="Open Agent Image Protocol reference CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Plan or build an Agent Image through a production adapter.")
    build.add_argument("--from", dest="locator", required=True)
    build.add_argument("-o", "--output", type=Path, required=True)
    build.add_argument("--policy", choices=("private", "public"), default="private")
    build.add_argument("--include-experience", action="store_true")
    build.add_argument("--include-workspace", action="store_true")
    build.add_argument("--yes", action="store_true")
    build.add_argument("--hermes-binary", default=os.environ.get("AGENT_IMAGE_HERMES_BIN", "hermes"))
    build.add_argument("--openclaw-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_BIN", "openclaw"))
    build.add_argument("--openclaw-node-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_NODE_BIN"))
    build.add_argument("--openclaw-workspace-root", type=Path)
    _common(build)
    inspect = commands.add_parser("inspect", help="Inspect verified image metadata without printing payloads.")
    inspect.add_argument("image", type=Path)
    _common(inspect)
    verify = commands.add_parser("verify", help="Verify schema, paths, digests, privacy, and reports.")
    verify.add_argument("image", type=Path)
    _common(verify)
    redact = commands.add_parser("redact", help="Create a public image without modifying the source.")
    redact.add_argument("image", type=Path)
    redact.add_argument("--policy", choices=("public",), required=True)
    redact.add_argument("-o", "--output", type=Path, required=True)
    _common(redact)
    diff = commands.add_parser("diff", help="Compare manifests and layer metadata.")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    _common(diff)
    restore = commands.add_parser("restore", help="Perform a pinned P1 native restore.")
    restore.add_argument("image", type=Path)
    restore.add_argument("--to", dest="target", required=True)
    restore.add_argument("--yes", action="store_true")
    restore.add_argument("--hermes-binary", default=os.environ.get("AGENT_IMAGE_HERMES_BIN", "hermes"))
    restore.add_argument("--openclaw-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_BIN", "openclaw"))
    restore.add_argument("--openclaw-node-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_NODE_BIN"))
    restore.add_argument("--openclaw-workspace-root", type=Path)
    _common(restore)
    migrate = commands.add_parser("migrate", help="Plan semantic migration.")
    migrate.add_argument("image", type=Path)
    migrate.add_argument("--to", dest="target", required=True)
    migrate.add_argument("--yes", action="store_true")
    migrate.add_argument("--dry-run", action="store_true")
    migrate.add_argument("--openclaw-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_BIN", "openclaw"))
    migrate.add_argument("--openclaw-node-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_NODE_BIN"))
    migrate.add_argument("--openclaw-workspace-root", type=Path)
    _common(migrate)
    adapters = commands.add_parser("adapters", help="Inspect installed adapter declarations.")
    adapter_commands = adapters.add_subparsers(dest="adapter_command", required=True)
    adapter_list = adapter_commands.add_parser("list", help="List built-in and discovered adapters.")
    _common(adapter_list)
    return parser


def _split(locator: str, expected: str | None = None) -> tuple[str, str]:
    adapter_id, separator, value = locator.partition(":")
    if not separator or not value or (expected is not None and adapter_id != expected):
        raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Unsupported adapter locator: {locator}")
    return adapter_id, value


def _hermes(binary: str) -> HermesAdapter:
    return HermesAdapter(cli=SubprocessHermesCLI(binary=binary))


def _openclaw(binary: str, node_binary: str | None, workspace_root: Path | None) -> OpenClawAdapter:
    return OpenClawAdapter(
        cli=SubprocessOpenClawCLI(
            binary=binary,
            node_binary=node_binary,
            workspace_root=workspace_root,
        )
    )


def _emit(value: Any, args: argparse.Namespace) -> None:
    report = getattr(args, "report", None)
    if report is not None:
        if report.exists():
            raise AgentImageError("E_TARGET_EXISTS", f"Report already exists: {report}")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    if not args.quiet:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _run(args: argparse.Namespace) -> Any:
    if args.command == "build":
        adapter_id, source = _split(args.locator)
        if adapter_id == "hermes":
            adapter = _hermes(args.hermes_binary)
        elif adapter_id == "openclaw":
            adapter = _openclaw(args.openclaw_binary, args.openclaw_node_binary, args.openclaw_workspace_root)
        else:
            raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Production adapter is not implemented: {adapter_id}")
        if not args.yes:
            return plan_build(adapter, source=source, policy=args.policy)
        return build_image(
            adapter,
            source=source,
            output=args.output,
            policy=args.policy,
            include_experience=args.include_experience,
            include_workspace=args.include_workspace,
        )
    if args.command == "inspect":
        return inspect_image(args.image)
    if args.command == "verify":
        return verify_image(args.image)
    if args.command == "redact":
        return redact_image(args.image, args.output)
    if args.command == "diff":
        return diff_images(args.before, args.after)
    if args.command == "restore":
        if not args.yes:
            raise AgentImageError(
                "E_MIGRATION_LOSS_REQUIRES_CONFIRMATION",
                "Native restore requires explicit --yes after reviewing image metadata.",
                details={"target": args.target},
            )
        adapter_id, target = _split(args.target)
        if adapter_id == "hermes":
            adapter = _hermes(args.hermes_binary)
        elif adapter_id == "openclaw":
            adapter = _openclaw(args.openclaw_binary, args.openclaw_node_binary, args.openclaw_workspace_root)
        else:
            raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Production adapter is not implemented: {adapter_id}")
        return restore_image(adapter, image=args.image, target=target)
    if args.command == "migrate":
        adapter_id, target = _split(args.target)
        if adapter_id != "openclaw":
            raise AgentImageError("E_ADAPTER_NOT_FOUND", "v0.1 migration target must be openclaw:<agent>.")
        adapter = _openclaw(args.openclaw_binary, args.openclaw_node_binary, args.openclaw_workspace_root)
        if not args.yes or args.dry_run:
            return plan_migration(adapter, image=args.image, target=target)
        return migrate_image(adapter, image=args.image, target=target)
    if args.command == "adapters" and args.adapter_command == "list":
        adapters = [HermesAdapter(), OpenClawAdapter()]
        return {
            "adapters": [
                {
                    "id": adapter.id,
                    "version": adapter.version,
                    "capabilities": adapter.capabilities(),
                    "runtime_verified": False,
                }
                for adapter in adapters
            ]
        }
    raise AgentImageError("E_SPEC_INVALID", f"Unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _emit(_run(args), args)
        return 0
    except AgentImageError as error:
        if getattr(args, "json", False):
            print(json.dumps(error.as_dict(), ensure_ascii=False, sort_keys=True), file=sys.stderr)
        else:
            print(f"{error.code}: {error.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
