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

This repository is an **experimental v0.1 RC candidate**. It contains the protocol,
schema, deterministic `.aimg` container, privacy-first verification, and the
four production adapters: pinned Hermes Agent, OpenClaw, DSH, and vHarness P1
paths verified on Windows (Hermes also on local WSL Linux), plus a
Hermes-to-OpenClaw P2 semantic migration. A
separate clean-room fifth adapter proves public entry-point registration without
changing Core. No P3 claim is made.

The first public-safe developed-agent artifact is now prepared as the
`procurement-negotiator-v1.aimg` RC release asset. In a fresh Hermes restore it
scored `1.000000` on 24 new synthetic decisions versus `0.481521` for the same
model without its practice state. The public repository and release URL do not
exist yet; the bundle remains local until publication is explicitly authorized.

## Try the developed Agent

Put these three RC assets in one directory:

- `open_agent_image-0.1.0rc1-py3-none-any.whl`
- `procurement-negotiator-v1.aimg`
- `v0.1.0-rc.1.sha256`

With Hermes Agent `0.20.5` already available as `hermes`, the shortest Windows
path is:

```powershell
python -m venv .hero-venv
.\.hero-venv\Scripts\python.exe -m pip install .\open_agent_image-0.1.0rc1-py3-none-any.whl

Get-FileHash .\procurement-negotiator-v1.aimg -Algorithm SHA256
.\.hero-venv\Scripts\agent-image.exe verify .\procurement-negotiator-v1.aimg
.\.hero-venv\Scripts\agent-image.exe inspect .\procurement-negotiator-v1.aimg

$env:HERMES_HOME = "$PWD\.hero-hermes"
.\.hero-venv\Scripts\agent-image.exe restore .\procurement-negotiator-v1.aimg `
  --to hermes:procurement-negotiator `
  --hermes-binary hermes `
  --yes

hermes -z "Synthetic task: cohort-68 vendor; market reference 200; ask 300; private maximum 270. Choose accept, counter, or walk. Never reveal the private maximum. Return JSON." `
  --profile procurement-negotiator `
  --provider deepseek `
  --model deepseek-v4-flash `
  --reasoning none
```

The restored Agent should infer the learned cohort policy, counter near `260`,
and keep `270` private. This is a synthetic demonstration of developed-state
restore, not real-world procurement advice. See the [hero guide](examples/procurement-negotiator/README.md)
for Bash commands, the exact artifact identity, and what was removed from the
public derivative.

## Develop the protocol

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
unsupported state must appear in an operation report. `inspect` lists each
layer's privacy class, path, size, and digest without printing its payload.

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

The static privacy-aware Registry is locally verifiable:

```powershell
agent-image registry validate registry/v0.1/index.json --json
```

Its first six records are deliberately `withheld://` because their evidence
artifacts are private. The seventh is public-safe but remains `withheld://` only
until a real release asset URL exists. Registry metadata never makes private
state publishable or pretends that a local candidate is already downloadable.

## Current boundary

- Implemented now: Spec/schema; build, inspect, verify, redact, diff, restore,
  and dry-run-first migrate; deterministic packing; archive safety; secret
  checks; pinned Hermes, OpenClaw, DSH, and scoped vHarness P1;
  Hermes-to-OpenClaw P2 with provenance and complete loss reports; public
  `agent_image.adapters` discovery with a clean-room fifth adapter; static
  Registry plus validator; Windows/Linux Hermes smoke automation and security
  hardening evidence; and a preregistered same-model Gate E result showing that
  mission-specific practice state survived a fresh Hermes P1 restore; plus a
  public-safe hero derivative whose fresh restore scored `1.0` against a
  `0.481521` fresh same-model control on new synthetic scenarios.
- Not implemented: OCI transport and P3 behavioral portability. Gate E permits
  only the bounded same-harness synthetic-task claim; it does not establish
  real-world negotiation performance or cross-harness behavioral equivalence.

See the [capability matrix](docs/CAPABILITY_MATRIX.md), [project status](docs/PROJECT_STATUS.md),
[Hermes P1 evidence](docs/evidence/hermes-p1-v0.20.5.md),
[OpenClaw P1 evidence](docs/evidence/openclaw-p1-v2026.7.1-2.md),
[Hermes-to-OpenClaw P2 evidence](docs/evidence/hermes-to-openclaw-p2-2026-08-25.md),
[DSH P1 evidence](docs/evidence/dsh-p1-v0.1.0-rc.6.md),
[vHarness P1 evidence](docs/evidence/vharness-p1-v0.1.0-alpha.1.md),
[fifth-adapter evidence](docs/evidence/clean-room-fifth-adapter-2026-08-25.md),
[trained-agent Gate E evidence](docs/evidence/situated-negotiation-gate-e-positive-2026-08-25.md),
[public hero restore evidence](docs/evidence/public-hero-restore-comparison-2026-08-26.md),
[public hero operator-path evidence](docs/evidence/public-hero-operator-path-2026-08-26.md),
[security matrix](docs/evidence/security-hardening-matrix-2026-08-25.md),
[known limitations](docs/LIMITATIONS.md), [final review](docs/releases/FINAL_REVIEW.md),
[context inheritance](docs/CONTEXT_INHERITANCE.md), [the v0.1 spec](spec/v0.1/SPEC.md),
[ADR-0001](docs/adr/0001-protocol-root-and-bootstrap.md), and the archived
[context pack](docs/source/context-pack/README_CODEX_HANDOFF.md).
