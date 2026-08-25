#!/usr/bin/env python3
"""Exercise production rollback against the real pinned OpenClaw CLI.

The injected failure occurs only after the official CLI has created and
recognized a target. Cleanup and residual verification both use the real host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from agent_image.adapters.openclaw import OpenClawAdapter, OpenClawAgent, SubprocessOpenClawCLI
from agent_image.errors import AgentImageError
from agent_image.formal_service import restore_image


# MOCK_POINT {"id":"MOCK-OPENCLAW-POST-CREATE-FAULT-001","type":"test_fixture","target":"OpenClaw post-create validation failure","replace_by":"never; deterministic failure injection remains test-only","owner":"openclaw-adapter","status":"accepted_test_only","production_allowed":false,"reason":"The exception is synthetic, while target creation, rollback, and residual verification use the real pinned OpenClaw CLI."}
class PostCreateFaultCLI:
    def __init__(self, real: SubprocessOpenClawCLI) -> None:
        self.real = real
        self.armed = False

    def version(self) -> str:
        return self.real.version()

    def list_agents(self) -> list[OpenClawAgent]:
        return self.real.list_agents()

    def show_agent(self, name: str) -> OpenClawAgent:
        if self.armed:
            self.armed = False
            raise AgentImageError("E_FAULT_INJECTED", "Deterministic post-create validation failure.")
        return self.real.show_agent(name)

    def target_workspace(self, name: str) -> Path:
        return self.real.target_workspace(name)

    def add_agent(self, name: str, workspace: Path) -> OpenClawAgent:
        agent = self.real.add_agent(name, workspace)
        self.armed = True
        return agent

    def delete_agent(self, name: str) -> None:
        self.real.delete_agent(name)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_report(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Report already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--openclaw-binary", required=True)
    parser.add_argument("--node-binary", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--target", default="rollback-probe")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    image = args.image.resolve(strict=True)
    state_dir = args.state_dir.resolve(strict=True)
    workspace_root = args.workspace_root.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    environment = {"OPENCLAW_STATE_DIR": str(state_dir)}
    real = SubprocessOpenClawCLI(
        binary=args.openclaw_binary,
        node_binary=args.node_binary,
        environment=environment,
        workspace_root=workspace_root,
    )
    if any(agent.id == args.target for agent in real.list_agents()):
        raise AgentImageError("E_TARGET_EXISTS", f"Probe target already exists: {args.target}")
    target_workspace = real.target_workspace(args.target)
    if target_workspace.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Probe workspace already exists: {target_workspace}")

    before = _sha256(image)
    observed_error: AgentImageError | None = None
    try:
        restore_image(OpenClawAdapter(PostCreateFaultCLI(real)), image=image, target=args.target)
    except AgentImageError as error:
        observed_error = error
    if observed_error is not None and observed_error.code == "E_ROLLBACK_FAILED":
        raise observed_error
    if observed_error is None or observed_error.code != "E_FAULT_INJECTED":
        raise AgentImageError(
            "E_NATIVE_INCOMPATIBLE",
            "Rollback smoke did not surface the expected injected failure.",
            details={"observed": None if observed_error is None else observed_error.as_dict()},
        )

    registered = any(agent.id == args.target for agent in real.list_agents())
    workspace_exists = target_workspace.exists()
    after = _sha256(image)
    report = {
        "evidence_version": "agent-image-failure-injection/v0.1",
        "operation": "openclaw-native-restore-rollback",
        "contract": {"openclaw": real.version()},
        "fault": {"code": observed_error.code, "point": "post-create target validation"},
        "rollback": {
            "official_host_registration_absent": not registered,
            "workspace_absent": not workspace_exists,
            "complete": not registered and not workspace_exists,
        },
        "source": {
            "archive_sha256_before": before,
            "archive_sha256_after": after,
            "immutable": before == after,
        },
    }
    if not report["rollback"]["complete"] or not report["source"]["immutable"]:
        raise AgentImageError("E_ROLLBACK_FAILED", "Real OpenClaw rollback smoke left residual state.", details=report)
    if args.report:
        _write_report(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except AgentImageError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
