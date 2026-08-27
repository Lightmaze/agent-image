"""Harness adapters for the Agent Image reference implementation."""

from agent_image.adapters.dsh import DshAdapter
from agent_image.adapters.hermes import HermesAdapter
from agent_image.adapters.openclaw import OpenClawAdapter
from agent_image.adapters.vharness import VHarnessAdapter

__all__ = ["DshAdapter", "HermesAdapter", "OpenClawAdapter", "VHarnessAdapter"]
