# Contributing

The project is in protocol bootstrap. Changes should begin from a written
acceptance case. Harness-specific paths and state types belong in adapters, not
the core manifest. Unsupported or dropped state must be reported explicitly.

Run the local checks from this directory:

```powershell
uv sync --locked --extra dev
uv run pytest
uv run python scripts/scan_mock_points.py --root . --fail-on-issues
uv run python scripts/scan_mojibake.py .
uv build
```

The installed-package smoke test must also pass without setting `PYTHONPATH`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/installed-package-smoke.ps1
```

Do not use real home directories or credentials in tests. Fixtures must be
synthetic and must state whether they are mock/test-only.

Harness capability claims require a pinned public contract and real target
validation. Fixture success is never sufficient for P1 or P2.
