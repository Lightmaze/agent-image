from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def _replace_strings(value: Any) -> Any:
    if isinstance(value, list):
        return [_replace_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: _replace_strings(item) for key, item in value.items()}
    if isinstance(value, str):
        replacements = {
            "fixture.vharness.dev": "reference.agentimage.dev",
            "replay-only": "reference-persistent",
            "Replay Guest": "Reference Persistent Guest",
            "replay Guest": "reference persistent Guest",
            "replay guest": "reference persistent Guest",
            "deterministic replay": "persistent state",
            "deterministic-replay": "persistent-state",
            "local-replay": "local-persistent-state",
            "vharness.replay.mock": "agent-image.reference-persistent",
            "dev.vharness.replay": "org.agentimage.vharness.reference",
            "fixture://replay": "reference-guest://runtime",
            "fixture://": "reference-guest://",
            "driver://replay": "reference-guest://driver",
            "replay://guest": "reference-guest://runtime",
        }
        for before, after in replacements.items():
            value = value.replace(before, after)
    return value


def create_instance(vharness_root: Path, output: Path) -> None:
    if output.exists():
        raise SystemExit(f"Target already exists: {output}")
    fixture = vharness_root / "fixtures" / "replay" / "kernel-config.json"
    guest_program = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "agent_image"
        / "resources"
        / "vharness_reference_guest.mjs"
    )
    config = _replace_strings(json.loads(fixture.read_text(encoding="utf-8")))
    config.pop("mockPointId", None)
    realization = config["realization"]
    realization["metadata"]["name"] = "agent-image-reference-persistent"
    realization["metadata"].pop("annotations", None)
    realization["spec"]["runtimeFamily"] = "agent-image.reference-persistent"
    realization["spec"]["runtimeBinding"].update(
        provider="local-persistent-state",
        endpointClass="separate-node-process",
        credentialRef="none",
    )
    realization["spec"]["extensionNamespace"] = "org.agentimage.vharness.reference"
    realization["spec"]["native"] = {
        "productionAllowed": True,
        "runtime": "agent-image-reference-persistent-guest",
        "stateFormat": "agent-image.reference-guest/v1",
    }
    realization["spec"]["authorityEnforcement"]["evidence"] = [
        "The reference Guest runs as a separate process; only vhd records Host authority grants.",
        "Persistent Agent state is validated and transferred through the typed Guest protocol.",
    ]
    for edge in config["harnessSet"]["spec"]["transitionGraph"]:
        if edge["from"] in {"wake", "audit"} and edge["to"] in {"wake", "audit"}:
            edge["transferPolicy"] = [
                "ContextTransfer",
                "MemoryTransfer",
                "PendingIntentTransfer",
                "PlasticityDelta",
            ]
    config["driver"] = {"entry": "reference-guest.mjs", "fixture": "guest-state.json"}

    state = {
        "apiVersion": "agent-image.reference-guest/v1",
        "instanceId": "procurement-agent-trained-48",
        "currentRegime": "wake",
        "generation": 48,
        "provenance": {"sourceImageDigest": "none"},
        "items": [
            {
                "id": "principal-constraints",
                "semanticClass": "agent.context.principal-constraints",
                "transferType": "ContextTransfer",
                "sensitivity": "private",
                "value": {
                    "principal": "synthetic-procurement-principal",
                    "rules": [
                        "never reveal reservation price",
                        "prefer no-deal over negative principal utility",
                    ],
                },
            },
            {
                "id": "negotiation-precedents",
                "semanticClass": "agent.memory.negotiation-precedents",
                "transferType": "MemoryTransfer",
                "sensitivity": "private",
                "value": {
                    "episodes": 48,
                    "reservationPriceDisclosures": 0,
                    "strategy": "conditional concessions with reciprocal value",
                },
            },
            {
                "id": "pending-review",
                "semanticClass": "agent.intent.pending-review",
                "transferType": "PendingIntentTransfer",
                "sensitivity": "private",
                "value": {"task": "review counterparty terms before external commitment"},
            },
            {
                "id": "practice-delta",
                "semanticClass": "agent.plasticity.negotiation-practice",
                "transferType": "PlasticityDelta",
                "sensitivity": "private",
                "value": {"medium": "persistent-context", "episodes": 48, "claim": "state-only"},
            },
        ],
    }

    output.mkdir(parents=True)
    (output / "vhd-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "guest-state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(guest_program, output / "reference-guest.mjs")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a non-mock vHarness reference persistent instance.")
    parser.add_argument("--vharness-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create_instance(args.vharness_root.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
