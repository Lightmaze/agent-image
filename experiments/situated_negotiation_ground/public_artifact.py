from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent_image import __version__
from agent_image.adapter_contract import AdapterExport
from agent_image.adapters.hermes import (
    HERMES_NATIVE_MEDIA_TYPE,
    _media_type,
    _normalized_snapshot,
    _safe_snapshot,
)
from agent_image.canonical import sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import layer_root_digest, load_image, publish_image
from agent_image.scanner import secret_filename_reason, structured_secret_findings


SOURCE_IMAGE_DIGEST = "sha256:4a2f4093da97af32aa224374afe5a4a1b2e5ce8370f1fdf5527d8c893b3f3165"
POSITIVE_EVIDENCE_DIGEST = "sha256:6c3776e8ce8182f0f23ec974e521a664437b629d1d197005d6814c861ed2f487"
PUBLIC_IMAGE_NAME = "procurement-negotiator-v1"
PUBLIC_IMAGE_VERSION = "0.1.0"

PUBLIC_SEMANTIC_PATHS = {
    "layers/development/situated-development-index.json",
    "layers/experience/sessions/situated-consolidations.jsonl",
    "layers/experience/sessions/situated-training-ground.jsonl",
    "layers/identity/SOUL.md",
    "layers/memory/memories/MEMORY.md",
}

PUBLIC_NATIVE_PATHS = {
    ".no-bundled-skills",
    "SOUL.md",
    "config.yaml",
    "memories/MEMORY.md",
    "sessions/situated-consolidations.jsonl",
    "sessions/situated-training-ground.jsonl",
}


def _item_id(prefix: str, path: str) -> str:
    return f"{prefix}-{sha256_bytes(path.encode('utf-8'))[7:23]}"


def _scan_public_payload(path: str, data: bytes) -> None:
    filename = secret_filename_reason(path)
    findings = structured_secret_findings(path, _media_type(path), data)
    if filename or findings:
        raise AgentImageError(
            "E_SECRET_DETECTED",
            f"Public hero payload did not pass the secret scan: {path}",
            details={"filename": filename, "structured_keys": findings},
        )


def _public_layer(layer: Mapping[str, Any], *, source_digest: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(layer))
    result["privacy"] = "public"
    source = layer.get("source")
    public_source = {
        "origin": f"agent-image:{source_digest}",
        "reason": "synthetic-only layer curated for public distribution",
    }
    if isinstance(source, Mapping) and isinstance(source.get("path"), str):
        public_source["path"] = str(source["path"])
    result["source"] = public_source
    return result


def _score(value: Any) -> dict[str, float]:
    return {"score": float(value)}


def build_public_hero_image(
    source: Path,
    evidence: Path,
    output: Path,
    *,
    expected_source_digest: str = SOURCE_IMAGE_DIGEST,
    expected_evidence_digest: str = POSITIVE_EVIDENCE_DIGEST,
) -> dict[str, Any]:
    if output.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Output already exists: {output}")
    document = load_image(source)
    source_digest = str(document.manifest["image"]["digest"])
    if source_digest != expected_source_digest:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "The hero curator accepts only the pinned positive Gate E source image.",
            details={"actual": source_digest, "expected": expected_source_digest},
        )
    try:
        evidence_bytes = evidence.read_bytes()
    except OSError as error:
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"Cannot read public Gate E evidence: {evidence}") from error
    evidence_digest = sha256_bytes(evidence_bytes)
    if evidence_digest != expected_evidence_digest:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "The public Gate E evidence digest does not match the pinned source.",
            details={"actual": evidence_digest, "expected": expected_evidence_digest},
        )
    _scan_public_payload(evidence.name, evidence_bytes)
    try:
        evidence_value = json.loads(evidence_bytes.decode("utf-8", errors="strict"))
        scores = evidence_value["scores"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", f"Invalid positive Gate E evidence: {error}") from error

    source_layers = {str(layer["path"]): layer for layer in document.manifest["layers"]}
    missing_semantic = sorted(PUBLIC_SEMANTIC_PATHS - set(source_layers))
    if missing_semantic:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "Pinned Gate E source is missing required public semantic state.",
            details={"missing": missing_semantic},
        )

    layers: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    source_outcomes: list[dict[str, Any]] = []
    redaction_outcomes: list[dict[str, Any]] = []

    for path, layer in sorted(source_layers.items()):
        outcome_id = f"layer-{layer['id']}"
        if path in PUBLIC_SEMANTIC_PATHS:
            data = document.entries[path]
            _scan_public_payload(path, data)
            payloads[path] = data
            layers.append(_public_layer(layer, source_digest=source_digest))
            action = "transformed"
            reason = "synthetic-only payload curated and reclassified public"
        elif layer["kind"] == "native":
            action = "transformed"
            reason = "native layer rebuilt from an explicit public-state whitelist"
        else:
            action = "redacted"
            reason = "layer is not required by the public hero artifact"
        source_outcomes.append({"id": outcome_id, "action": action, "reason": reason})
        redaction_outcomes.append({"id": outcome_id, "action": action, "reason": reason})

    native_layers = [
        layer
        for layer in document.manifest["layers"]
        if layer["kind"] == "native" and layer["media_type"] == HERMES_NATIVE_MEDIA_TYPE
    ]
    if len(native_layers) != 1:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "Pinned Gate E source must contain one Hermes native layer.")
    native_layer = native_layers[0]
    native_root, native_entries = _safe_snapshot(document.entries[native_layer["path"]])
    missing_native = sorted(PUBLIC_NATIVE_PATHS - set(native_entries))
    if missing_native:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "Pinned Gate E native state is missing required public members.",
            details={"missing": missing_native},
        )
    public_native: dict[str, bytes] = {}
    for path, data in sorted(native_entries.items()):
        outcome_id = _item_id("native", path)
        if path in PUBLIC_NATIVE_PATHS:
            _scan_public_payload(path, data)
            public_native[path] = data
            action = "transformed"
            reason = "member preserved in the minimal public Hermes snapshot"
        else:
            action = "redacted"
            reason = "runtime cache, log, database, lock, or nonessential state removed from public distribution"
        source_outcomes.append({"id": outcome_id, "action": action, "reason": reason})
        redaction_outcomes.append({"id": outcome_id, "action": action, "reason": reason})

    native_payload = _normalized_snapshot(native_root, public_native)
    native_path = "layers/native/hermes-profile.tar.gz"
    payloads[native_path] = native_payload
    layers.append(
        {
            "id": "hermes-native-profile",
            "kind": "native",
            "media_type": HERMES_NATIVE_MEDIA_TYPE,
            "path": native_path,
            "digest": sha256_bytes(native_payload),
            "size": len(native_payload),
            "privacy": "public",
            "portability": "opaque",
            "source": {
                "origin": f"agent-image:{source_digest}",
                "reason": "minimal Hermes snapshot rebuilt from an explicit synthetic-state whitelist",
            },
        }
    )

    public_evidence_path = "layers/evaluation/situated-gate-e-positive.json"
    payloads[public_evidence_path] = evidence_bytes
    layers.append(
        {
            "id": "situated-gate-e-public-evidence",
            "kind": "evaluation",
            "media_type": "application/json",
            "path": public_evidence_path,
            "digest": evidence_digest,
            "size": len(evidence_bytes),
            "privacy": "public",
            "portability": "portable",
            "source": {
                "origin": "repository:docs/evidence/situated-negotiation-gate-e-positive-2026-08-25.json",
                "reason": "public machine-readable evidence for the bounded state-retention claim",
            },
        }
    )
    evidence_outcome = {
        "id": "public-gate-e-evidence",
        "action": "preserved",
        "reason": "pinned public evidence embedded unchanged",
    }
    source_outcomes.append(evidence_outcome)
    redaction_outcomes.append(evidence_outcome)

    layers.sort(key=lambda item: item["path"])
    base_digest = None
    source_lineage = document.manifest.get("lineage", {})
    if isinstance(source_lineage, dict):
        parent = source_lineage.get("parent")
        if isinstance(parent, dict):
            base_digest = parent.get("digest")
        legacy_parents = source_lineage.get("parents")
        if base_digest is None and isinstance(legacy_parents, list) and legacy_parents:
            candidate = legacy_parents[0]
            if isinstance(candidate, dict):
                base_digest = candidate.get("digest")

    development_layer = next(layer for layer in layers if layer["kind"] == "development")
    manifest: dict[str, Any] = {
        "spec": "agent-image/v0.1",
        "image": {
            "name": PUBLIC_IMAGE_NAME,
            "version": PUBLIC_IMAGE_VERSION,
            "created_at": str(document.manifest["image"]["created_at"]),
            "digest": layer_root_digest(layers),
            "description": "Public synthetic procurement negotiator developed through 128 causal practice episodes.",
        },
        "runtime": copy.deepcopy(document.manifest["runtime"]),
        "layers": layers,
        "development": {
            "method": "habitat",
            "episodes": 128,
            "habitat": {"id": "situated-negotiation-training-ground", "version": "0.2"},
            "notes": "Model weights were unchanged; development used synthetic causal practice and consolidation.",
            "evidence": [
                {
                    "kind": "log",
                    "path": development_layer["path"],
                    "digest": development_layer["digest"],
                }
            ],
        },
        "evaluations": [
            {
                "id": "situated-negotiation-gate-e-v0.2",
                "status": "self_reported",
                "before": _score(scores["before"]),
                "after": _score(scores["fresh_restored"]),
                "evidence": {
                    "kind": "evaluation",
                    "path": public_evidence_path,
                    "digest": evidence_digest,
                },
            }
        ],
        "lineage": {
            **({"base": {"digest": str(base_digest)}} if base_digest else {}),
            "parent": {"digest": source_digest},
            "fork_reason": "public-safe distribution derivative of the positive Gate E checkpoint",
        },
        "privacy": {"default": "private", "public_build": True, "unresolved_items": 0},
        "provenance": {
            "source_harness": "hermes",
            "source_adapter": "org.agentimage.hermes",
            "export_tool_version": __version__,
            "source_uri": f"agent-image:{source_digest}",
        },
        "extensions": {
            "org.agentimage.publication": {
                "profile": "procurement-negotiator-v1",
                "source_image_digest": source_digest,
                "synthetic_data_only": True,
                "native_whitelist": sorted(PUBLIC_NATIVE_PATHS),
            }
        },
    }
    source_report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "curate-public-hero",
        "inventory_count": len(source_outcomes),
        "outcomes": source_outcomes,
    }
    redaction_report = {
        "report_version": "agent-image-operation-report/v0.1",
        "operation": "redact",
        "inventory_count": len(redaction_outcomes),
        "outcomes": redaction_outcomes,
    }
    export = AdapterExport(manifest=manifest, payloads=payloads, source_report=source_report)
    publish_image(export, output, redaction_report=redaction_report)
    published = load_image(output)
    return {
        "operation": "curate-public-hero",
        "source_image_digest": source_digest,
        "image_digest": published.manifest["image"]["digest"],
        "file_digest": sha256_bytes(output.read_bytes()),
        "output": str(output.resolve()),
        "layers": len(published.manifest["layers"]),
        "native_members": sorted(public_native),
        "verified": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the public procurement-negotiator Agent Image")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_public_hero_image(args.source, args.evidence, args.output)
    except AgentImageError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
