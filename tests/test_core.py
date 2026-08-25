from __future__ import annotations

import shutil
import tempfile
import unittest
import hashlib
import json
from pathlib import Path

from agent_image.container import pack_entries, read_entries
from agent_image.errors import AgentImageError
from agent_image.service import (
    build_fixture_image,
    diff_images,
    inspect_image,
    redact_image,
    verify_image,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "minimal"


class CoreToolchainTests(unittest.TestCase):
    def test_build_is_deterministic_and_self_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.aimg"
            second = Path(temporary) / "second.aimg"
            build_fixture_image(FIXTURE, first, policy="private")
            build_fixture_image(FIXTURE, second, policy="private")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertTrue(verify_image(first)["valid"])

    def test_build_does_not_modify_source_and_report_reconciles(self) -> None:
        before = {
            path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "agent.aimg"
            build_fixture_image(FIXTURE, image, policy="private")
            entries = read_entries(image)
            report = json.loads(entries["meta/source-report.json"])
            self.assertEqual(report["inventory_count"], len(report["outcomes"]))
            self.assertNotIn(b".agent-image-", image.read_bytes())
        after = {
            path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_inspect_exposes_metadata_not_private_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "agent.aimg"
            build_fixture_image(FIXTURE, image, policy="private")
            result = inspect_image(image)
            rendered = str(result)
            self.assertIn("memory", rendered)
            self.assertEqual(
                {item["privacy"] for item in result["layers"]["items"]},
                {"public", "private"},
            )
            self.assertNotIn("greenhouse observation", rendered)

    def test_public_redaction_creates_new_verified_image(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            private_image = Path(temporary) / "private.aimg"
            public_image = Path(temporary) / "public.aimg"
            build_fixture_image(FIXTURE, private_image, policy="private")
            original = private_image.read_bytes()
            result = redact_image(private_image, public_image, policy="public")
            self.assertEqual(private_image.read_bytes(), original)
            self.assertEqual(result["removed"], ["memory-main"])
            entries = read_entries(public_image)
            self.assertNotIn("layers/memory/MEMORY.md", entries)
            self.assertIn("meta/redaction-report.json", entries)
            self.assertTrue(verify_image(public_image)["valid"])

    def test_public_build_excludes_private_items_and_reports_them(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "public.aimg"
            build_fixture_image(FIXTURE, image, policy="public")
            entries = read_entries(image)
            self.assertNotIn("layers/memory/MEMORY.md", entries)
            report = json.loads(entries["meta/source-report.json"])
            actions = {item["id"]: item["action"] for item in report["outcomes"]}
            self.assertEqual(actions["memory-main"], "redacted")
            self.assertTrue(verify_image(image)["valid"])

    def test_missing_privacy_defaults_to_unknown_and_public_export_redacts_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "unknown-privacy"
            shutil.copytree(FIXTURE, fixture)
            inventory = fixture / "inventory.yaml"
            content = inventory.read_text(encoding="utf-8")
            inventory.write_text(content.replace("    privacy: private\n", "", 1), encoding="utf-8", newline="\n")
            image = root / "public.aimg"

            build_fixture_image(fixture, image, policy="public")

            entries = read_entries(image)
            report = json.loads(entries["meta/source-report.json"])
            outcomes = {item["id"]: item for item in report["outcomes"]}
            self.assertEqual(outcomes["memory-main"]["privacy"], "unknown")
            self.assertEqual(outcomes["memory-main"]["action"], "redacted")
            self.assertNotIn("layers/memory/MEMORY.md", entries)
            self.assertTrue(verify_image(image)["valid"])

    def test_diff_is_empty_for_equal_content_and_reports_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unchanged_a = root / "a.aimg"
            unchanged_b = root / "b.aimg"
            build_fixture_image(FIXTURE, unchanged_a, policy="private")
            build_fixture_image(FIXTURE, unchanged_b, policy="private")
            self.assertTrue(diff_images(unchanged_a, unchanged_b)["empty"])

            changed_fixture = root / "changed"
            shutil.copytree(FIXTURE, changed_fixture)
            (changed_fixture / "SOUL.md").write_text("# Changed fixture\n", encoding="utf-8")
            changed = root / "changed.aimg"
            build_fixture_image(changed_fixture, changed, policy="private")
            result = diff_images(unchanged_a, changed)
            self.assertFalse(result["empty"])
            self.assertEqual(result["layers"]["modified"], ["identity-main"])

    def test_diff_reports_private_metadata_without_private_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = root / "before.aimg"
            after = root / "after.aimg"
            build_fixture_image(FIXTURE, before, policy="private")
            changed_fixture = root / "changed-private"
            shutil.copytree(FIXTURE, changed_fixture)
            private_text = "private payload must never appear in diff output"
            (changed_fixture / "MEMORY.md").write_text(private_text, encoding="utf-8", newline="\n")
            build_fixture_image(changed_fixture, after, policy="private")

            result = diff_images(before, after)

            self.assertEqual(result["layers"]["modified"], ["memory-main"])
            self.assertNotIn(private_text, json.dumps(result))

    def test_tampered_payload_fails_digest_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "agent.aimg"
            tampered = Path(temporary) / "tampered.aimg"
            build_fixture_image(FIXTURE, image, policy="private")
            entries = read_entries(image)
            entries["layers/identity/SOUL.md"] += b"tampered"
            pack_entries(entries, tampered)
            with self.assertRaises(AgentImageError) as raised:
                verify_image(tampered)
            self.assertEqual(raised.exception.code, "E_DIGEST_MISMATCH")

    def test_undeclared_payload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "agent.aimg"
            modified = Path(temporary) / "undeclared.aimg"
            build_fixture_image(FIXTURE, image, policy="private")
            entries = read_entries(image)
            entries["layers/other/undeclared.txt"] = b"unexpected"
            pack_entries(entries, modified)
            with self.assertRaises(AgentImageError) as raised:
                verify_image(modified)
            self.assertEqual(raised.exception.code, "E_IMAGE_CORRUPT")

    def test_missing_payload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "agent.aimg"
            modified = Path(temporary) / "missing.aimg"
            build_fixture_image(FIXTURE, image, policy="private")
            entries = read_entries(image)
            del entries["layers/memory/MEMORY.md"]
            pack_entries(entries, modified)
            with self.assertRaises(AgentImageError) as raised:
                verify_image(modified)
            self.assertEqual(raised.exception.code, "E_IMAGE_CORRUPT")

    def test_existing_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "existing.aimg"
            output.write_bytes(b"owner data")
            with self.assertRaises(AgentImageError) as raised:
                build_fixture_image(FIXTURE, output, policy="private")
            self.assertEqual(raised.exception.code, "E_TARGET_EXISTS")
            self.assertEqual(output.read_bytes(), b"owner data")


if __name__ == "__main__":
    unittest.main()
