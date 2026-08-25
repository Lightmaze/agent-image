from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from agent_image import __version__
from agent_image.adapters.hermes import HermesAdapter, SubprocessHermesCLI
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, plan_build, restore_image
from agent_image.image_archive import diff_images, inspect_image, redact_image, verify_image


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--quiet", action="store_true", help="Suppress successful output.")
    parser.add_argument("--verbose", action="store_true", help="Emit adapter diagnostics when available.")


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
    _common(restore)
    migrate = commands.add_parser("migrate", help="Plan semantic migration.")
    migrate.add_argument("image", type=Path)
    migrate.add_argument("--to", dest="target", required=True)
    migrate.add_argument("--yes", action="store_true")
    migrate.add_argument("--dry-run", action="store_true", default=True)
    _common(migrate)
    return parser


def _split(locator: str, expected: str | None = None) -> tuple[str, str]:
    adapter_id, separator, value = locator.partition(":")
    if not separator or not value or (expected is not None and adapter_id != expected):
        raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Unsupported adapter locator: {locator}")
    return adapter_id, value


def _hermes(binary: str) -> HermesAdapter:
    return HermesAdapter(cli=SubprocessHermesCLI(binary=binary))


def _emit(value: Any, args: argparse.Namespace) -> None:
    if not args.quiet:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _run(args: argparse.Namespace) -> Any:
    if args.command == "build":
        adapter_id, source = _split(args.locator)
        if adapter_id != "hermes":
            raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Production adapter is not implemented: {adapter_id}")
        adapter = _hermes(args.hermes_binary)
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
        _, target = _split(args.target, expected="hermes")
        return restore_image(_hermes(args.hermes_binary), image=args.image, target=target)
    if args.command == "migrate":
        raise AgentImageError("E_ADAPTER_NOT_FOUND", "Semantic migration is not implemented in the Hermes P1 epoch.")
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
