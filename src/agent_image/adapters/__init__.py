"""Harness adapters for the Open Agent Image Protocol reference implementation."""

from agent_image.adapters.dsh import DshAdapter
from agent_image.adapters.hermes import HermesAdapter
from agent_image.adapters.openclaw import OpenClawAdapter
from agent_image.adapters.vharness import VHarnessAdapter

__all__ = ["DshAdapter", "HermesAdapter", "OpenClawAdapter", "VHarnessAdapter"]
