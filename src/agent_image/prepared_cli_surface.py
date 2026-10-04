from __future__ import annotations

from argparse import Namespace, _SubParsersAction
import os
from pathlib import Path
from typing import Any, Callable

from agent_image.build_plan import load_build_plan
from agent_image.errors import AgentImageError
from agent_image.formal_service import (
    prepare_image_workspace,
    publish_prepared_workspace_image,
    recover_prepared_image_workspace,
)


def register_prepared_build_commands(
    commands: _SubParsersAction,
    common: Callable[[Any], None],
) -> None:
    prepare = commands.add_parser(
        "prepare-build",
        help="Capture one reviewable candidate into a recoverable prepared workspace.",
    )
    prepare.add_argument("--from", dest="locator", required=True)
    prepare.add_argument("--workspace", type=Path, required=True)
    prepare.add_argument("--plan", type=Path, help="Approved pre-capture build plan JSON.")
    prepare.add_argument("--policy", choices=("private", "public"), default="private")
    prepare.add_argument("--include-experience", action="store_true")
    prepare.add_argument("--include-workspace", action="store_true")
    prepare.add_argument("--yes", action="store_true")
    prepare.add_argument("--hermes-binary", default=os.environ.get("AGENT_IMAGE_HERMES_BIN", "hermes"))
    prepare.add_argument("--dsh-binary", default=os.environ.get("AGENT_IMAGE_DSH_BIN", "dsh"))
    prepare.add_argument("--dsh-node-binary", default=os.environ.get("AGENT_IMAGE_DSH_NODE_BIN"))
    prepare.add_argument("--dsh-home", type=Path)
    prepare.add_argument("--openclaw-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_BIN", "openclaw"))
    prepare.add_argument("--openclaw-node-binary", default=os.environ.get("AGENT_IMAGE_OPENCLAW_NODE_BIN"))
    prepare.add_argument("--openclaw-workspace-root", type=Path)
    prepare.add_argument("--vharness-source-root", type=Path, default=os.environ.get("AGENT_IMAGE_VHARNESS_ROOT"))
    prepare.add_argument("--vharness-node-binary", default=os.environ.get("AGENT_IMAGE_VHARNESS_NODE_BIN"))
    prepare.add_argument("--vharness-home", type=Path)
    common(prepare)

    recover = commands.add_parser(
        "recover-prepared",
        help="Recover a prepared receipt from an already captured workspace without reopening source state.",
    )
    recover.add_argument("--workspace", type=Path, required=True)
    common(recover)

    publish = commands.add_parser(
        "publish-prepared",
        help="Publish exact reviewed prepared bytes from a workspace without reopening the source harness.",
    )
    publish.add_argument("--workspace", type=Path, required=True)
    publish.add_argument("-o", "--output", type=Path, required=True)
    publish.add_argument("--yes", action="store_true")
    common(publish)


def execute_prepare_build(args: Namespace, adapter: Any, *, source: str) -> dict[str, Any]:
    if not args.yes:
        raise AgentImageError(
            "E_CAPTURE_REQUIRES_CONFIRMATION",
            "prepare-build requires explicit --yes after reviewing the capture scope.",
        )
    approved_plan = load_build_plan(args.plan) if args.plan is not None else None
    return prepare_image_workspace(
        adapter,
        source=source,
        workspace=args.workspace,
        policy=args.policy,
        include_experience=args.include_experience,
        include_workspace=args.include_workspace,
        approved_plan=approved_plan,
    )


def execute_recover_prepared(args: Namespace) -> dict[str, Any]:
    return recover_prepared_image_workspace(workspace=args.workspace)


def execute_publish_prepared(args: Namespace) -> dict[str, Any]:
    if not args.yes:
        raise AgentImageError(
            "E_PUBLICATION_REQUIRES_CONFIRMATION",
            "publish-prepared requires explicit --yes after reviewing the exact prepared subject.",
        )
    return publish_prepared_workspace_image(workspace=args.workspace, output=args.output)
