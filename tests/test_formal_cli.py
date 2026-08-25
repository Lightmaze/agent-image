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
