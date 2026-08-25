from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent_image.adapter_registry import discover_adapters
from agent_image.errors import AgentImageError


class _Adapter:
    id = "org.example.clean"
    version = "1.0.0"
    locator_prefix = "clean"

    def capabilities(self):
        return {
            "archive": True,
            "native_restore": False,
            "semantic_migration": False,
            "portability_level": "P0",
            "pinned_harness": {"version": "1"},
        }

    def inspect_source(self, source):
        raise NotImplementedError

    def export(self, source, policy, *, include_experience=False, include_workspace=False):
        raise NotImplementedError

    def native_restore(self, image, target):
        raise NotImplementedError


@dataclass
class _EntryPoint:
    name: str
    value: str = "example:create_adapter"

    def load(self):
        return _Adapter


def test_entry_point_discovery_accepts_public_contract(monkeypatch) -> None:
    monkeypatch.setattr("agent_image.adapter_registry.metadata.entry_points", lambda **kwargs: [_EntryPoint("clean")])

    discovered = discover_adapters()

    assert discovered["clean"].id == "org.example.clean"


def test_entry_point_name_must_equal_locator_prefix(monkeypatch) -> None:
    monkeypatch.setattr("agent_image.adapter_registry.metadata.entry_points", lambda **kwargs: [_EntryPoint("different")])

    with pytest.raises(AgentImageError) as caught:
        discover_adapters()

    assert caught.value.code == "E_ADAPTER_NOT_FOUND"
