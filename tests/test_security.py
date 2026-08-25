from __future__ import annotations

import tempfile
import unittest
import gzip
import io
import tarfile
from pathlib import Path

from agent_image.container import pack_entries
from agent_image.errors import AgentImageError
from agent_image.scanner import secret_filename_reason
from agent_image.service import build_fixture_image, verify_image


ROOT = Path(__file__).resolve().parents[1]


class SecurityTests(unittest.TestCase):
    def test_hidden_credentials_filename_is_rejected(self) -> None:
        self.assertIsNotNone(secret_filename_reason("profile/.credentials.yaml"))

    def test_secret_filename_is_rejected(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "secret-file"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(AgentImageError) as raised:
                build_fixture_image(fixture, Path(temporary) / "bad.aimg", policy="private")
            self.assertEqual(raised.exception.code, "E_SECRET_DETECTED")

    def test_structured_secret_key_is_rejected(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "secret-key"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(AgentImageError) as raised:
                build_fixture_image(fixture, Path(temporary) / "bad.aimg", policy="private")
            self.assertEqual(raised.exception.code, "E_SECRET_DETECTED")

    def test_structured_yaml_secret_key_is_rejected(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "secret-yaml"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(AgentImageError) as raised:
                build_fixture_image(fixture, Path(temporary) / "bad.aimg", policy="private")
            self.assertEqual(raised.exception.code, "E_SECRET_DETECTED")

    def test_unsafe_archive_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "unsafe.aimg"
            pack_entries({"../../outside": b"no"}, image, validate_paths=False)
            with self.assertRaises(AgentImageError) as raised:
                verify_image(image)
            self.assertEqual(raised.exception.code, "E_UNSAFE_PATH")
            self.assertFalse((Path(temporary).parent / "outside").exists())

    def test_absolute_archive_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "absolute.aimg"
            pack_entries({"/absolute/path": b"no"}, image, validate_paths=False)
            with self.assertRaises(AgentImageError) as raised:
                verify_image(image)
            self.assertEqual(raised.exception.code, "E_UNSAFE_PATH")

    def test_duplicate_archive_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "duplicate.aimg"
            with image.open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                    with tarfile.open(fileobj=compressed, mode="w") as archive:
                        for content in (b"first", b"second"):
                            info = tarfile.TarInfo("same.txt")
                            info.size = len(content)
                            archive.addfile(info, io.BytesIO(content))
            with self.assertRaises(AgentImageError) as raised:
                verify_image(image)
            self.assertEqual(raised.exception.code, "E_IMAGE_CORRUPT")

    def test_symlink_archive_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "symlink.aimg"
            with image.open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                    with tarfile.open(fileobj=compressed, mode="w") as archive:
                        info = tarfile.TarInfo("layers/native/link")
                        info.type = tarfile.SYMTYPE
                        info.linkname = "../../outside"
                        archive.addfile(info)
            with self.assertRaises(AgentImageError) as raised:
                verify_image(image)
            self.assertEqual(raised.exception.code, "E_UNSAFE_PATH")


if __name__ == "__main__":
    unittest.main()
