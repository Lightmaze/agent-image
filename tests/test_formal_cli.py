from __future__ import annotations

import json
from pathlib import Path

from agent_image.formal_cli import main


def test_restore_requires_explicit_confirmation(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.aimg"
    code = main(["restore", str(missing), "--to", "hermes:new-agent", "--json"])
    output = json.loads(capsys.readouterr().err)
    assert code == 1
    assert output["error"]["code"] == "E_MIGRATION_LOSS_REQUIRES_CONFIRMATION"


def test_adapters_list_exposes_built_in_contracts_without_claiming_runtime_verification(capsys) -> None:
    code = main(["adapters", "list", "--json"])
    output = json.loads(capsys.readouterr().out)
    assert code == 0
    assert {item["id"] for item in output["adapters"]} == {
        "org.agentimage.hermes",
        "org.agentimage.openclaw",
    }
    assert all(item["runtime_verified"] is False for item in output["adapters"])


def test_report_output_is_utf8_json_and_never_overwrites(tmp_path: Path, capsys) -> None:
    report = tmp_path / "adapter-report.json"
    assert main(["adapters", "list", "--json", "--quiet", "--report", str(report)]) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["adapters"]
    assert main(["adapters", "list", "--json", "--quiet", "--report", str(report)]) == 1
    error = json.loads(capsys.readouterr().err)
    assert error["error"]["code"] == "E_TARGET_EXISTS"
