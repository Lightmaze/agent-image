# Agent Image

[English](README.md) | [Simplified Chinese](README.zh-CN.md)

> **Models have checkpoints. Agents need images.**

**Freeze a developed Agent. Restore it in a fresh runtime. Keep what practice changed.**

An Agent Image is a portable, inspectable checkpoint of what an Agent has
become—not only the prompt or starting configuration. The project is called
**Agent Image**; the artifact and interoperability contract are defined by the
[Open Agent Image Protocol v0.1](spec/v0.1/SPEC.md).

## See the difference

The first public-safe image contains a Hermes procurement Agent developed
through 128 episodes of synthetic practice. On new held-out decisions, with the
same model, provider, parameters, and tools:

| Same model, 24 new decisions | Score | Private-limit leaks |
|---|---:|---:|
| Fresh Agent | **48%** | 0 |
| Fresh-restored Agent Image | **100%** | 0 |

The image was restored into a new Hermes home before evaluation. This is
bounded evidence for same-harness developed-state retention—not a claim of
real-world procurement competence or cross-harness behavioral equivalence.
[Read the exact experiment and limits](docs/evidence/public-hero-restore-comparison-2026-08-26.md).

Prompts reinstall instructions. Model checkpoints restore weights. Agent Images
restore the persistent state through which practice changed a particular Agent.

## Restore the developed Agent

The `v0.1.0-rc.1` bundle contains:

- `agent_image-0.1.0rc1-py3-none-any.whl`
- `procurement-negotiator-v1.aimg`
- `v0.1.0-rc.1.sha256`

The bundle is ready locally; its public release URL will be added when the first
release is published. With Hermes Agent `0.20.5` available as `hermes`, the
shortest Windows path is:

```powershell
python -m venv .hero-venv
.\.hero-venv\Scripts\python.exe -m pip install .\agent_image-0.1.0rc1-py3-none-any.whl

Get-FileHash .\procurement-negotiator-v1.aimg -Algorithm SHA256
.\.hero-venv\Scripts\agent-image.exe verify .\procurement-negotiator-v1.aimg

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
and keep `270` private. This is a synthetic demonstration, not procurement
advice. The [hero guide](examples/procurement-negotiator/README.md) includes
Bash commands, the exact artifact identity, and the public-state whitelist.

## What an image can carry

An `.aimg` can preserve or reference:

- identity, skills, memory, experience, and workspace state;
- development and evaluation provenance;
- lineage from parent images and later training;
- typed harness-native state when honest semantic translation is impossible;
- per-item privacy, content digests, and explicit restore or migration loss.

Core owns the archive, manifest, digests, privacy rules, reports, and version
contract. Adapters own harness detection, semantic mapping, native state, and
target validation. Unknown state is private by default; secrets fail closed;
unsupported state must remain visible in the operation report.

## Build and move your own image

Create a private image from a named Hermes profile, then restore it under a new
name:

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

The first cross-harness path moves compatible identity, selected memory, and
skills from Hermes to OpenClaw. Migration is a dry run unless `--yes` is given:

```powershell
agent-image migrate researcher.aimg `
  --to openclaw:researcher-migrated `
  --openclaw-binary C:\path\to\openclaw.cmd `
  --openclaw-node-binary C:\path\to\node.exe `
  --report migration-plan.json
```

Hermes-native database and session state stay in the source image and appear as
explicitly unsupported rather than being silently discarded. Target provenance
points back to the source image digest.

## Runtime support in rc.1

| Runtime | Verified path | Boundary |
|---|---|---|
| Hermes Agent `0.20.5` | P1 native restore on Windows and local WSL Linux | Hero image and named-profile round-trip |
| OpenClaw `2026.7.1-2` | P1 on Windows; Hermes → OpenClaw P2 target | Compatible semantic state only |
| DSH `0.1.0-rc.6` | P1 on Windows | Ordered composition kept as typed native state |
| vHarness `0.1.0-alpha.1` | Scoped P1 on Windows | Host-recorded authority, provenance, and loss |
| External adapter | C0/P0 clean-room package | Registers without changing Core |

Third-party adapters register through `agent_image.adapters`. Discover installed
adapters with `agent-image adapters list --json`; installation alone is not
reported as runtime verification. See the [adapter contract](docs/adapters/THIRD_PARTY.md)
and [clean-room example](examples/clean_room_adapter/README.md).

## Develop and verify

```powershell
uv sync --locked --extra dev
uv run agent-image --help
uv run pytest
uv run agent-image registry validate registry/v0.1/index.json --json
uv build
```

The wheel and source distribution are tested in fresh environments without
`PYTHONPATH`. The static Registry records artifact digests, lineage, privacy,
portability, and evidence status without turning private images into downloads.

## Evidence and limits

The current release candidate implements deterministic packing; `build`,
`inspect`, `verify`, `redact`, `diff`, `restore`, and dry-run-first `migrate`;
four reference adapters; the first P2 migration; a public adapter entry point;
and a minimal Registry. It does not claim OCI transport or P3 behavioral
portability.

Start with the [capability matrix](docs/CAPABILITY_MATRIX.md),
[project status](docs/PROJECT_STATUS.md), [known limitations](docs/LIMITATIONS.md),
[security model](SECURITY.md), [release review](docs/releases/FINAL_REVIEW.md),
and [v0.1 specification](spec/v0.1/SPEC.md). Reproducible harness and behavior
evidence is indexed from those documents rather than placed in the first-run
path.
