from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_image.continuation_files import _write_json_exclusive
from agent_image.errors import AgentImageError
from agent_image.formal_cli import main
from agent_image.image_archive import redact_image
from agent_image.service import build_fixture_image


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal"


def test_exclusive_writer_refuses_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "binding.json"
    output.write_text("keep-me", encoding="utf-8")
    with pytest.raises(AgentImageError) as error:
        _write_json_exclusive({"schema": "synthetic"}, output)
    assert error.value.code == "E_TARGET_EXISTS"
    assert output.read_text(encoding="utf-8") == "keep-me"


def test_exclusive_writer_round_trips_exact_json(tmp_path: Path) -> None:
    output = tmp_path / "binding.json"
    value = {"schema": "synthetic", "nested": {"b": 2, "a": 1}}
    _write_json_exclusive(value, output)
    assert json.loads(output.read_text(encoding="utf-8")) == value


def test_formal_cli_bind_verify_and_evidence_mismatch(tmp_path: Path, capsys) -> None:
    parent = tmp_path / "parent.aimg"
    child = tmp_path / "child.aimg"
    evidence = tmp_path / "evidence.json"
    binding = tmp_path / "binding.json"

    build_fixture_image(FIXTURE, parent, policy="private")
    redact_image(parent, child, policy="public")
    evidence.write_text(
        '{"schema":"agent-image-test-structural-evidence/v0.1","structural_only":true}',
        encoding="utf-8",
    )

    assert main([
        "continuation", "bind",
        "--parent", str(parent),
        "--child", str(child),
        "--evidence", str(evidence),
        "--kind", "agent-image-test-structural-evidence",
        "--media-type", "application/json",
        "--output", str(binding),
        "--json",
    ]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["valid"] is True
    assert created["causal_transition_verified"] is False
    assert created["behavioral_retention_verified"] is False

    assert main([
        "continuation", "verify", str(binding),
        "--parent", str(parent),
        "--child", str(child),
        "--evidence", str(evidence),
        "--json",
    ]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["valid"] is True

    original = binding.read_bytes()
    assert main([
        "continuation", "bind",
        "--parent", str(parent),
        "--child", str(child),
        "--evidence", str(evidence),
        "--kind", "agent-image-test-structural-evidence",
        "--media-type", "application/json",
        "--output", str(binding),
        "--json",
    ]) == 1
    error = json.loads(capsys.readouterr().err)
    assert error["error"]["code"] == "E_TARGET_EXISTS"
    assert binding.read_bytes() == original

    evidence.write_text('{"tampered":true}', encoding="utf-8")
    assert main([
        "continuation", "verify", str(binding),
        "--parent", str(parent),
        "--child", str(child),
        "--evidence", str(evidence),
        "--json",
    ]) == 1
    mismatch = json.loads(capsys.readouterr().err)
    assert mismatch["error"]["code"] == "E_DIGEST_MISMATCH"
