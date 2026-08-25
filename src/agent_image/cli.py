from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from agent_image import __version__
from agent_image.errors import AgentImageError
from agent_image.service import (
    build_fixture_image,
    diff_images,
    inspect_image,
    plan_fixture_build,
    redact_image,
    verify_image,
)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--quiet", action="store_true", help="Suppress successful output.")
    parser.add_argument("--verbose", action="store_true", help="Reserved for diagnostic detail.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-image", description="Open Agent Image Protocol reference CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="Plan or build an Agent Image.")
    build.add_argument("--from", dest="locator", required=True, help="Source locator; bootstrap supports fixture:<path>.")
    build.add_argument("-o", "--output", type=Path, required=True)
    build.add_argument("--policy", choices=("private", "public"), default="private")
    build.add_argument("--yes", action="store_true", help="Accept the displayed plan and write the image.")
    _common(build)

    inspect = commands.add_parser("inspect", help="Inspect verified image metadata.")
    inspect.add_argument("image", type=Path)
    _common(inspect)

    verify = commands.add_parser("verify", help="Verify schema, paths, digests, privacy, and reports.")
    verify.add_argument("image", type=Path)
    _common(verify)

    redact = commands.add_parser("redact", help="Create a redacted image without modifying the source.")
    redact.add_argument("image", type=Path)
    redact.add_argument("--policy", choices=("public",), required=True)
    redact.add_argument("-o", "--output", type=Path, required=True)
    _common(redact)

    diff = commands.add_parser("diff", help="Compare layer and metadata changes without reading payloads aloud.")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    _common(diff)

    restore = commands.add_parser("restore", help="Restore through a production adapter (not yet implemented).")
    restore.add_argument("image", type=Path)
    restore.add_argument("--to", dest="target", required=True)
    _common(restore)

    migrate = commands.add_parser("migrate", help="Plan semantic migration (not yet implemented).")
    migrate.add_argument("image", type=Path)
    migrate.add_argument("--to", dest="target", required=True)
    migrate.add_argument("--yes", action="store_true")
    migrate.add_argument("--dry-run", action="store_true", default=True)
    _common(migrate)
    return parser


def _fixture_path(locator: str) -> Path:
    prefix = "fixture:"
    if not locator.startswith(prefix) or not locator[len(prefix):]:
        raise AgentImageError(
            "E_ADAPTER_NOT_FOUND",
            "Bootstrap build supports only fixture:<path>; production adapters are not installed.",
        )
    return Path(locator[len(prefix):])


def _emit(value: Any, args: argparse.Namespace) -> None:
    if args.quiet:
        return
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _run(args: argparse.Namespace) -> Any:
    if args.command == "build":
        source = _fixture_path(args.locator)
        if not args.yes:
            return plan_fixture_build(source, policy=args.policy)
        return build_fixture_image(source, args.output, policy=args.policy)
    if args.command == "inspect":
        return inspect_image(args.image)
    if args.command == "verify":
        return verify_image(args.image)
    if args.command == "redact":
        return redact_image(args.image, args.output, policy=args.policy)
    if args.command == "diff":
        return diff_images(args.before, args.after)
    if args.command in {"restore", "migrate"}:
        raise AgentImageError(
            "E_ADAPTER_NOT_FOUND",
            f"{args.command} requires a production target adapter; none is implemented in the bootstrap alpha.",
            details={"target": args.target},
        )
    raise AgentImageError("E_SPEC_INVALID", f"Unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
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

