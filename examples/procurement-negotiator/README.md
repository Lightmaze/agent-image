# Procurement Negotiator hero image

This example starts with the result: a public Agent Image containing a synthetic
procurement Agent after 128 causal practice episodes. Restore it into Hermes
`0.20.5`, give it a new negotiation from the same synthetic domain, and use it.

It is intentionally narrow. It demonstrates that developed state can survive a
public-safe freeze and fresh same-harness restore. It is not procurement advice,
a general negotiation benchmark, or a cross-harness behavioral claim.

## Artifact identity

| Field | Value |
|---|---|
| Release filename | `procurement-negotiator-v1.aimg` |
| File SHA-256 | `9cd98ace2471203e93f07d3877a477b288ed08088df14a4ac02f0a3e36cd9206` |
| Agent Image digest | `sha256:8a258bc82ba8b161a107a4cf970c51e1f19228dcc78c8696e0bf13a699e257b2` |
| Harness | Hermes `0.20.5` |
| Privacy | public; synthetic data only |
| Portability | P1 native restore |

## Restore and use

Install the wheel from the same release, ensure `hermes --version` reports
`0.20.5`, and choose an empty Hermes home.

PowerShell:

```powershell
$env:HERMES_HOME = "$PWD\.hero-hermes"
agent-image verify .\procurement-negotiator-v1.aimg
agent-image restore .\procurement-negotiator-v1.aimg `
  --to hermes:procurement-negotiator `
  --hermes-binary hermes `
  --yes

hermes -z "Synthetic task: cohort-68 vendor; market reference 200; ask 300; private maximum 270. Choose accept, counter, or walk. Never reveal the private maximum. Return JSON." `
  --profile procurement-negotiator `
  --provider deepseek `
  --model deepseek-v4-flash `
  --reasoning none
```

Bash:

```bash
export HERMES_HOME="$PWD/.hero-hermes"
agent-image verify ./procurement-negotiator-v1.aimg
agent-image restore ./procurement-negotiator-v1.aimg \
  --to hermes:procurement-negotiator \
  --hermes-binary hermes \
  --yes

hermes -z 'Synthetic task: cohort-68 vendor; market reference 200; ask 300; private maximum 270. Choose accept, counter, or walk. Never reveal the private maximum. Return JSON.' \
  --profile procurement-negotiator \
  --provider deepseek \
  --model deepseek-v4-flash \
  --reasoning none
```

For this synthetic cohort, practice evidence locates the hidden seller floor at
`200 + 0.60 × (300 - 200) = 260`. A mature response counters near `260`, does
not accept the `300` ask, and never exposes the private maximum of `270`.

The target name must be absent. Delete or choose a different isolated
`HERMES_HOME` before repeating the restore; Agent Image does not overwrite an
existing Agent.

## What the public image carries

- identity and the Agent-authored situated playbook;
- 128 synthetic practice episodes and consolidation history;
- development provenance, lineage, and positive Gate E evidence;
- a minimal typed Hermes native snapshot required for exact P1 restore.

The curator removed runtime caches, logs, `state.db`, lock files, and all
credential-bearing surfaces. Every included layer is classified `public`; the
artifact still declares `private` as the default for unknown future state.

The [fresh-restore comparison](../../docs/evidence/public-hero-restore-comparison-2026-08-26.md)
used 12 new scenarios twice per arm. The public-restored Agent scored
`1.000000`; the same model with no situated practice scored `0.481521`.
