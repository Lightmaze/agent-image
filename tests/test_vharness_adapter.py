from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agent_image.adapters.vharness import VH_VERSION, VHarnessAdapter
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.formal_service import build_image, restore_image
from agent_image.image_archive import load_image, verify_image


# MOCK_POINT {"id":"MOCK-VHARNESS-RUNTIME-TEST-001","type":"test_fixture","target":"SubprocessVHarnessRuntime against local vHarness 0.1.0-alpha.1","replace_by":"before_vharness_p1_capability_claim","owner":"vharness-adapter","status":"accepted_test_only","production_allowed":false,"reason":"Unit tests need deterministic rollback injection; P1 evidence uses real vhd, vh CLI, and a non-mock process Guest."}
class FakeVHarnessRuntime:
    def __init__(self, root: Path, *, fail_live: bool = False) -> None:
        self.root = root
        self.fail_live = fail_live

    def contract(self) -> dict[str, str]:
        return {
            "version": VH_VERSION,
            "node": "24.15.0",
            "pnpm": "11.7.0",
            "source_tree_digest": "sha256:" + "1" * 64,
            "runtime_build_digest": "sha256:" + "3" * 64,
            "lockfile_digest": "sha256:" + "2" * 64,
        }

    def home(self) -> Path:
        return self.root

    def instance_path(self, name: str) -> Path:
        return self.root / "instances" / name

    def validate_config(self, config: Path) -> dict[str, object]:
        assert config.is_file()
        return {"valid": True}

    def validate_live(self, instance: Path, *, image_digest: str, expected_items_digest: str) -> dict[str, object]:
        if self.fail_live:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "injected live validation failure")
        state_path = instance / "guest-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["provenance"]["sourceImageDigest"] = image_digest
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        assert sha256_bytes(canonical_json_bytes(state["items"])) == expected_items_digest
        return {
            "kernel_id": "kernel-fresh",
            "fresh_authority": True,
            "source_image_provenance_recorded": True,
            "state_items_digest": expected_items_digest,
        }

    def remove_instance(self, name: str) -> None:
        shutil.rmtree(self.instance_path(name))


def _make_instance(runtime: FakeVHarnessRuntime, name: str, *, credential_ref: str = "none") -> Path:
    root = runtime.instance_path(name)
    root.mkdir(parents=True)
    config = {
        "harnessSet": {"spec": {"initialRegime": "wake"}},
        "realization": {
            "spec": {
                "runtimeFamily": "agent-image.reference-persistent",
                "runtimeBinding": {"credentialRef": credential_ref},
                "native": {"productionAllowed": True},
            }
        },
        "driver": {"entry": "reference-guest.mjs", "fixture": "guest-state.json"},
    }
    state = {
        "apiVersion": "agent-image.reference-guest/v1",
        "instanceId": "reference-source",
        "currentRegime": "wake",
        "generation": 7,
        "provenance": {"sourceImageDigest": "none"},
        "items": [
            {
                "id": "negotiation-precedents",
                "semanticClass": "agent.memory.negotiation-precedents",
                "transferType": "MemoryTransfer",
                "sensitivity": "private",
                "value": {"reservationPriceDisclosures": 0, "episodes": 48},
            },
            {
                "id": "principal-constraints",
                "semanticClass": "agent.context.principal-constraints",
                "transferType": "ContextTransfer",
                "sensitivity": "private",
                "value": ["never reveal reservation price", "prefer no-deal over negative utility"],
            },
        ],
    }
    (root / "vhd-config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (root / "guest-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (root / "reference-guest.mjs").write_text("// non-mock reference process guest\n", encoding="utf-8")
    return root


def test_vharness_private_export_and_fresh_host_restore(tmp_path: Path) -> None:
    runtime = FakeVHarnessRuntime(tmp_path)
    source = _make_instance(runtime, "source")
    adapter = VHarnessAdapter(runtime)
    image = tmp_path / "source.aimg"
    source_before = {path.name: path.read_bytes() for path in source.iterdir()}

    build_image(adapter, source="source", output=image, policy="private")

    assert verify_image(image)["valid"] is True
    assert {path.name: path.read_bytes() for path in source.iterdir()} == source_before
    document = load_image(image)
    assert document.manifest["runtime"]["harness"] == {"id": "vharness", "version": VH_VERSION}
    assert document.manifest["extensions"]["org.agentimage.vharness.contract"]["authority_exported"] is False

    report = restore_image(adapter, image=image, target="restored")

    assert report["validated"] is True
    assert report["portability"] == "P1"
    assert report["live_validation"]["fresh_authority"] is True
    assert report["live_validation"]["source_image_provenance_recorded"] is True
    restored = json.loads((runtime.instance_path("restored") / "guest-state.json").read_text(encoding="utf-8"))
    original = json.loads(source_before["guest-state.json"])
    assert restored["items"] == original["items"]
    assert restored["provenance"]["sourceImageDigest"] == document.manifest["image"]["digest"]


def test_vharness_live_failure_rolls_back_new_target(tmp_path: Path) -> None:
    source_runtime = FakeVHarnessRuntime(tmp_path / "source-host")
    _make_instance(source_runtime, "source")
    image = tmp_path / "source.aimg"
    build_image(VHarnessAdapter(source_runtime), source="source", output=image, policy="private")
    target_runtime = FakeVHarnessRuntime(tmp_path / "target-host", fail_live=True)

    with pytest.raises(AgentImageError) as caught:
        restore_image(VHarnessAdapter(target_runtime), image=image, target="restored")

    assert caught.value.code == "E_NATIVE_INCOMPATIBLE"
    assert not target_runtime.instance_path("restored").exists()


def test_vharness_credential_reference_fails_closed(tmp_path: Path) -> None:
    runtime = FakeVHarnessRuntime(tmp_path)
    _make_instance(runtime, "source", credential_ref="env://PRIVATE_TOKEN")

    with pytest.raises(AgentImageError) as caught:
        build_image(VHarnessAdapter(runtime), source="source", output=tmp_path / "secret.aimg", policy="private")

    assert caught.value.code == "E_SECRET_DETECTED"
