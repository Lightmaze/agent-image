#!/usr/bin/env python3
"""Inventory and validate machine-readable MOCK_POINT markers."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MARKER_RE = re.compile(r"MOCK_POINT\s+(\{.*\})")
MARKER_START_RE = re.compile(r"^\s*(?:(?://|#|--|/\*|\*|<!--)\s*)?MOCK_POINT\b")
REQUIRED_FIELDS = {
    "id", "type", "target", "replace_by", "owner", "status",
    "production_allowed", "reason",
}
ALLOWED_TYPES = {
    "ai_provider", "payment_provider", "license_provider", "entitlement_provider",
    "repository", "answer_safety_gate", "input_redaction", "clock", "random",
    "network", "config", "ui_prototype", "test_fixture",
}
ALLOWED_STATUSES = {"active", "replacing", "replaced", "accepted_test_only"}
PRODUCTION_BLOCKING_TYPES = ALLOWED_TYPES - {"test_fixture", "clock", "random"}
EXCLUDED_DIRS = {
    ".git", ".gradle", ".idea", ".pytest-tmp", ".tmp", ".vscode",
    "__pycache__", "build", "dist", "node_modules", ".venv", "venv",
}
EXCLUDED_FILES = {
    "scripts/scan_mock_points.py",
    "docs/engineering/MOCK_INVENTORY.generated.md",
}
BINARY_SUFFIXES = {".bin", ".dll", ".exe", ".ico", ".jpg", ".jpeg", ".png", ".zip", ".aimg"}


@dataclass(frozen=True)
class MockPoint:
    path: Path
    line: int
    data: dict[str, Any]


@dataclass(frozen=True)
class Issue:
    path: Path
    line: int
    message: str


def iter_files(root: Path):
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
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
            relative = path.relative_to(root)
            if relative.as_posix() in EXCLUDED_FILES or path.suffix.casefold() in BINARY_SUFFIXES:
                continue
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue


def validate(path: Path, line: int, data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        issues.append(Issue(path, line, f"Missing fields: {', '.join(missing)}."))
    if data.get("type") not in ALLOWED_TYPES:
        issues.append(Issue(path, line, f"Unknown type: {data.get('type')}."))
    if data.get("status") not in ALLOWED_STATUSES:
        issues.append(Issue(path, line, f"Unknown status: {data.get('status')}."))
    if not isinstance(data.get("production_allowed"), bool):
        issues.append(Issue(path, line, "production_allowed must be boolean."))
    for field in ("id", "target", "replace_by", "owner", "reason"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            issues.append(Issue(path, line, f"{field} must be a non-empty string."))
    if data.get("type") in PRODUCTION_BLOCKING_TYPES and data.get("production_allowed") is True:
        issues.append(Issue(path, line, f"{data['type']} mocks cannot be production_allowed."))
    return issues


def scan(root: Path) -> tuple[list[MockPoint], list[Issue]]:
    points: list[MockPoint] = []
    issues: list[Issue] = []
    for absolute in iter_files(root):
        relative = absolute.relative_to(root)
        try:
            text = absolute.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not MARKER_START_RE.search(line):
                continue
            match = MARKER_RE.search(line)
            if not match:
                issues.append(Issue(relative, line_number, "Marker requires single-line JSON."))
                continue
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as error:
                issues.append(Issue(relative, line_number, f"Invalid JSON: {error.msg}."))
                continue
            if not isinstance(data, dict):
                issues.append(Issue(relative, line_number, "Marker JSON must be an object."))
                continue
            point = MockPoint(relative, line_number, data)
            points.append(point)
            issues.extend(validate(relative, line_number, data))
    seen: dict[str, MockPoint] = {}
    for point in points:
        identifier = point.data.get("id")
        if not isinstance(identifier, str):
            continue
        if identifier in seen:
            first = seen[identifier]
            issues.append(Issue(point.path, point.line, f"Duplicate id {identifier}; first at {first.path}:{first.line}."))
        else:
            seen[identifier] = point
    return points, issues


def blockers(points: list[MockPoint]) -> list[MockPoint]:
    return [
        point for point in points
        if point.data.get("status") in {"active", "replacing"}
        and point.data.get("production_allowed") is False
        and point.data.get("type") in PRODUCTION_BLOCKING_TYPES
    ]


def markdown(points: list[MockPoint], issues: list[Issue]) -> str:
    type_counts = Counter(str(point.data.get("type")) for point in points)
    status_counts = Counter(str(point.data.get("status")) for point in points)
    blocked = blockers(points)
    lines = [
        "# Mock Inventory", "",
        "> Generated by `python scripts/scan_mock_points.py --root . --write docs/engineering/MOCK_INVENTORY.generated.md`.",
        "> Do not edit by hand.", "", "## Summary", "",
        f"- Total mock points: {len(points)}",
        f"- Issues: {len(issues)}",
        f"- Production blockers: {len(blocked)}", "",
        "## Counts", "", "| Dimension | Value | Count |", "|---|---|---:|",
    ]
    lines.extend(f"| Type | `{key}` | {count} |" for key, count in sorted(type_counts.items()))
    lines.extend(f"| Status | `{key}` | {count} |" for key, count in sorted(status_counts.items()))
    lines.extend(["", "## Mock Points", "", "| ID | Type | Status | Production | Location | Replace By | Target |", "|---|---|---|---|---|---|---|"])
    for point in sorted(points, key=lambda value: (value.path.as_posix(), value.line)):
        data = point.data
        values = [
            str(data.get("id", "")), str(data.get("type", "")), str(data.get("status", "")),
            str(data.get("production_allowed", "")), f"{point.path.as_posix()}:{point.line}",
            str(data.get("replace_by", "")), str(data.get("target", "")),
        ]
        lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    lines.extend(["", "## Issues", ""])
    lines.extend(["- None."] if not issues else [f"- `{issue.path}:{issue.line}` {issue.message}" for issue in issues])
    lines.extend(["", "## Production Blockers", ""])
    lines.extend(["- None."] if not blocked else [f"- `{point.data.get('id')}` at `{point.path}:{point.line}`" for point in blocked])
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--write")
    parser.add_argument("--fail-on-issues", action="store_true")
    parser.add_argument("--fail-on-production-blockers", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    points, issues = scan(root)
    blocked = blockers(points)
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown(points, issues), encoding="utf-8", newline="\n")
    print(f"Mock points: {len(points)}")
    print(f"Issues: {len(issues)}")
    print(f"Production blockers: {len(blocked)}")
    for issue in issues:
        print(f"- {issue.path}:{issue.line}: {issue.message}")
    if args.fail_on_issues and issues:
        return 1
    if args.fail_on_production_blockers and blocked:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
