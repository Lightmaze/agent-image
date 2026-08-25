from __future__ import annotations

import os
import sys
from pathlib import Path


TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml"}
MARKERS = ("\ufffd", "Ã", "Â", "â€", "ä¸", "ï¼")
EXCLUDED_DIRS = {
    ".git",
    ".pytest-tmp",
    ".tmp",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


def candidates(target: Path):
    try:
        if target.is_file():
            yield target
            return
    except OSError:
        return
    for current, directories, files in os.walk(target, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in directories:
            candidate = current_path / name
            if name in EXCLUDED_DIRS or name.startswith(".venv") or name.endswith(".egg-info"):
                continue
            try:
                if candidate.is_symlink():
                    continue
            except OSError:
                continue
            kept_directories.append(name)
        directories[:] = kept_directories
        for name in files:
            path = current_path / name
            if path.suffix.casefold() in TEXT_SUFFIXES:
                yield path


def main(argv: list[str]) -> int:
    targets = [Path(argument) for argument in argv] or [Path(".")]
    findings = 0
    for target in targets:
        for path in candidates(target):
            if path.resolve() == Path(__file__).resolve():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="strict")
            except (OSError, UnicodeDecodeError) as error:
                print(f"{path}: unreadable as UTF-8: {error}")
                findings += 1
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if any(marker in line for marker in MARKERS):
                    print(f"{path}:{number}: suspicious mojibake marker")
                    findings += 1
    if findings:
        print(f"mojibake scan failed: {findings} finding(s)")
        return 1
    print("mojibake scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
