from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_image import (
    AdapterExport,
    AgentImageError,
    canonical_json_bytes,
    layer_root_digest,
    sha256_bytes,
)


class CleanRoomAdapter:
    id = "org.agentimage.example.cleanroom"
    version = "0.1.0"
    locator_prefix = "cleanroom"

    def capabilities(self) -> dict[str, Any]:
        return {
            "archive": True,
            "native_restore": False,
            "semantic_migration": False,
            "portability_level": "P0",
            "pinned_harness": {"id": "clean-room-json", "version": "1"},
        }

    def inspect_source(self, source: str) -> dict[str, Any]:
        path, data = self._source(source)
        return {
            "adapter": {"id": self.id, "version": self.version},
            "source_harness": {"id": "clean-room-json", "version": "1"},
            "source": {"path": str(path), "digest": sha256_bytes(data)},
            "inventory_count": 1,
            "capabilities": self.capabilities(),
        }

    def export(
        self,
        source: str,
        policy: str,
        *,
        include_experience: bool = False,
        include_workspace: bool = False,
    ) -> AdapterExport:
        del include_experience, include_workspace
        if policy not in {"private", "public"}:
            raise AgentImageError("E_SPEC_INVALID", f"Unsupported policy: {policy}")
        path, data = self._source(source)
        layers: list[dict[str, Any]] = []
        payloads: dict[str, bytes] = {}
        if policy == "private":
            layer_path = "layers/other/clean-room-state.json"
            payloads[layer_path] = data
            layers.append(
                {
                    "id": "clean-room-state",
                    "kind": "other",
                    "media_type": "application/json",
                    "path": layer_path,
                    "digest": sha256_bytes(data),
                    "size": len(data),
                    "privacy": "private",
                    "portability": "adapter-specific",
                    "source": {"path": str(path), "reason": "clean-room extension proof"},
                }
            )
        action = "preserved" if policy == "private" else "redacted"
        report = {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "build",
            "adapter": {"id": self.id, "version": self.version},
            "inventory_count": 1,
            "outcomes": [
                {
                    "id": "source-state",
                    "source": str(path),
                    "action": action,
                    "reason": "stored as an adapter-specific layer" if action == "preserved" else "private by default",
                }
            ],
        }
        manifest = {
            "spec": "agent-image/v0.1",
            "image": {
                "name": path.stem,
                "version": "0.1.0",
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "digest": layer_root_digest(layers),
                "description": "Clean-room entry-point adapter proof",
            },
            "runtime": {
                "harness": {"id": "clean-room-json", "version": "1"},
                "adapter": {"id": self.id, "version": self.version},
            },
            "layers": layers,
            "privacy": {"default": "private", "public_build": policy == "public", "unresolved_items": 0},
            "provenance": {
                "source_harness": "clean-room-json",
                "source_adapter": self.id,
                "export_tool_version": "public-sdk",
                "source_uri": f"cleanroom:{path}",
            },
        }
        return AdapterExport(manifest=manifest, payloads=payloads, source_report=report)

    def native_restore(self, image: Any, target: str) -> dict[str, Any]:
        del image, target
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", "The clean-room skeleton declares P0 only.")

    @staticmethod
    def _source(source: str) -> tuple[Path, bytes]:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise AgentImageError("E_SOURCE_NOT_FOUND", f"Clean-room JSON source was not found: {path}")
        data = path.read_bytes()
        try:
            value = json.loads(data.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Clean-room source must be UTF-8 JSON.") from error
        if not isinstance(value, dict) or value.get("apiVersion") != "clean-room-state/v1":
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Clean-room source apiVersion is invalid.")
        canonical = canonical_json_bytes(value) + b"\n"
        return path, canonical


def create_adapter() -> CleanRoomAdapter:
    return CleanRoomAdapter()
