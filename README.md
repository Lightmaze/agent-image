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

This repository is an **experimental v0.1 beta candidate**. It contains the protocol,
schema, deterministic `.aimg` container, privacy-first verification, and the
four production adapters: pinned Hermes Agent, OpenClaw, DSH, and vHarness P1
paths verified on Windows, plus a Hermes-to-OpenClaw P2 semantic migration. A
separate clean-room fifth adapter proves public entry-point registration without
changing Core. No P3 claim is made.

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

The first cross-harness path is dry-run first:

```powershell
agent-image migrate researcher.aimg `
  --to openclaw:researcher-migrated `
  --openclaw-binary C:\path\to\openclaw.cmd `
  --openclaw-node-binary C:\path\to\node.exe `
  --report migration-plan.json

agent-image migrate researcher.aimg `
  --to openclaw:researcher-migrated `
  --yes `
  --openclaw-binary C:\path\to\openclaw.cmd `
  --openclaw-node-binary C:\path\to\node.exe `
  --report migration.json
```

Only compatible identity, selected memory, and skills move. Native Hermes
database/session state remains in the source image with explicit loss status,
and target provenance points back to the source image digest.

Third-party adapters register through the public `agent_image.adapters`
entry-point group. `agent-image adapters list --json` reports built-in and
installed declarations without treating installation as runtime verification.
See the [third-party adapter contract](docs/adapters/THIRD_PARTY.md) and the
[clean-room package](examples/clean_room_adapter/README.md).

## Current boundary

- Implemented now: Spec/schema; build, inspect, verify, redact, diff, restore,
  and dry-run-first migrate; deterministic packing; archive safety; secret
  checks; pinned Hermes, OpenClaw, DSH, and scoped vHarness P1;
  Hermes-to-OpenClaw P2 with provenance and complete loss reports; public
  `agent_image.adapters` discovery with a clean-room fifth adapter.
- Not started: registry, OCI transport, and P3 behavioral portability. The
  first trained-agent Gate E run
  completed with an honest negative result; no behavioral claim is made.

See the [capability matrix](docs/CAPABILITY_MATRIX.md), [project status](docs/PROJECT_STATUS.md),
[Hermes P1 evidence](docs/evidence/hermes-p1-v0.20.5.md),
[OpenClaw P1 evidence](docs/evidence/openclaw-p1-v2026.7.1-2.md),
[Hermes-to-OpenClaw P2 evidence](docs/evidence/hermes-to-openclaw-p2-2026-08-25.md),
[DSH P1 evidence](docs/evidence/dsh-p1-v0.1.0-rc.6.md),
[vHarness P1 evidence](docs/evidence/vharness-p1-v0.1.0-alpha.1.md),
[fifth-adapter evidence](docs/evidence/clean-room-fifth-adapter-2026-08-25.md),
[context inheritance](docs/CONTEXT_INHERITANCE.md), [the v0.1 spec](spec/v0.1/SPEC.md),
[ADR-0001](docs/adr/0001-protocol-root-and-bootstrap.md), and the archived
[context pack](docs/source/context-pack/README_CODEX_HANDOFF.md).
