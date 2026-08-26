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
uv run agent-image registry validate registry/v0.1/index.json --json
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

## Documentation delivery declaration

Before adding or materially rewriting a plan, stage document, design note,
acceptance note, or major README section, register its delivery declaration in
`docs/DOCUMENT_DELIVERY_CHECKLIST.md`. Name the direct reader, the artifact or
decision being delivered, who receives each referenced object, the intended
result, and the role of evidence. Formal writing starts after the declaration
is marked `DECLARED`.
