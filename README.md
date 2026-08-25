# Open Agent Image Protocol

> **Models have checkpoints. Agents need images.**

> **We didn't train the model. We trained the agent.**
>
> **Don't ship only prompts. Ship what the agent has become.**

An Agent Image is a harness-neutral, inspectable checkpoint of what a developed
agent has become: runtime references, identity, skills, memory, experience,
development provenance, evaluation, lineage, privacy metadata, and explicitly
typed native state. It is not a prompt bundle, a skill pack, a model checkpoint,
or a renamed profile archive.

This repository is an **experimental v0.1 alpha**. It contains the protocol,
schema, deterministic `.aimg` container, privacy-first verification, and the
first production adapter: a pinned Hermes Agent P1 path verified against
Hermes `0.20.5` / `v2026.8.19` / `fcbd107` on Windows. OpenClaw, DSH, and
vHarness remain planned adapters; no P2 or P3 claim is made.

Create the reproducible development environment and verify the installed CLI:

```powershell
uv sync --locked --extra dev
uv run agent-image --help
uv run pytest
```

The repository ships standard wheel and source distributions; the release
smoke test installs the wheel into a fresh virtual environment without setting
`PYTHONPATH`.

The first real round-trip uses a named Hermes profile and a new target name:

```powershell
agent-image build `
  --from hermes:researcher `
  --output researcher.aimg `
  --policy private `
  --include-experience `
  --yes

agent-image inspect researcher.aimg
agent-image verify researcher.aimg

agent-image restore researcher.aimg `
  --to hermes:researcher-restored `
  --yes
```

The adapter calls Hermes' official profile export/import commands, performs a
second Agent Image secret pass, preserves the safe snapshot as typed native
state, validates restored file invariants, and asks Hermes to recognize the new
profile. The source profile is hashed before and after export.

Private builds may contain `private` items but never `secret` items. Public images
are created as new artifacts with `redact --policy public`; source images are not
modified. Unknown data is private by default, secret detection fails closed, and
unsupported state must appear in an operation report.

## Current boundary

- Implemented now: Spec/schema; build, inspect, verify, redact, and metadata
  diff; deterministic packing; archive safety; secret checks; pinned Hermes P1
  build/restore with source and target validation.
- Present but intentionally blocked: `migrate`, pending OpenClaw and the first
  real cross-harness loss report.
- Not started: production OpenClaw/DSH/vHarness adapters, trained-agent
  demonstration, registry, OCI transport, and P3 behavioral portability.

See the [capability matrix](docs/CAPABILITY_MATRIX.md), [project status](docs/PROJECT_STATUS.md),
[Hermes P1 evidence](docs/evidence/hermes-p1-v0.20.5.md),
[context inheritance](docs/CONTEXT_INHERITANCE.md), [the v0.1 spec](spec/v0.1/SPEC.md),
[ADR-0001](docs/adr/0001-protocol-root-and-bootstrap.md), and the archived
[context pack](docs/source/context-pack/README_CODEX_HANDOFF.md).
