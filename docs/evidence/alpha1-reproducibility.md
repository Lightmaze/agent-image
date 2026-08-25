# v0.1.0-alpha.1 Reproducibility Evidence

Date: 2026-08-24

The project now has an independent Git boundary, an Apache-2.0 license, a
locked Python environment, cross-platform CI configuration, standard wheel and
source distributions, and an installed-package smoke test that does not set
`PYTHONPATH`.

## Gate results

| Check | Result |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked --extra dev` | PASS |
| `uv run pytest` | PASS, 28/28 |
| mock governance | PASS, 5 points / 0 issues / 0 blockers |
| UTF-8/mojibake scan | PASS |
| `uv build` | PASS, wheel and sdist |
| fresh virtual environment CLI smoke | PASS |
| Hermes P1 evidence | PASS, inherited formal evidence |

The distribution digests are recorded in
`checksums/v0.1.0-alpha.1.sha256`. Build output is intentionally not committed.

## Claim boundary

This evidence supports a local alpha release candidate and the previously
proven Hermes P1 claim. It does not support OpenClaw, DSH, vHarness, P2, P3, or
trained-agent portability claims.
