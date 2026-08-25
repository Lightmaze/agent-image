from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from agent_image.errors import AgentImageError
from agent_image.manifest import load_yaml, validate_manifest


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_example_manifest_is_valid(self) -> None:
        manifest = load_yaml(ROOT / "spec" / "v0.1" / "manifest.example.yaml")
        validate_manifest(manifest)

    def test_missing_spec_fails(self) -> None:
        manifest = load_yaml(ROOT / "spec" / "v0.1" / "manifest.example.yaml")
        invalid = copy.deepcopy(manifest)
        del invalid["spec"]
        with self.assertRaises(AgentImageError) as raised:
            validate_manifest(invalid)
        self.assertEqual(raised.exception.code, "E_SPEC_INVALID")

    def test_illegal_layer_kind_fails(self) -> None:
        manifest = load_yaml(ROOT / "spec" / "v0.1" / "manifest.example.yaml")
        invalid = copy.deepcopy(manifest)
        invalid["layers"][0]["kind"] = "harness-profile"
        with self.assertRaises(AgentImageError):
            validate_manifest(invalid)

    def test_schema_is_json_schema_2020_12(self) -> None:
        schema = json.loads((ROOT / "spec" / "v0.1" / "manifest.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["spec"]["const"], "agent-image/v0.1")

    def test_date_without_time_fails(self) -> None:
        manifest = load_yaml(ROOT / "spec" / "v0.1" / "manifest.example.yaml")
        invalid = copy.deepcopy(manifest)
        invalid["image"]["created_at"] = "2026-08-24"
        with self.assertRaises(AgentImageError):
            validate_manifest(invalid)


if __name__ == "__main__":
    unittest.main()
