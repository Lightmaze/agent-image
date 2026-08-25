# Hermes to OpenClaw P2 Gate Evidence

Verdict: **PASS for the declared mappings on the pinned Windows contracts**.

## Flow

```text
Hermes 0.20.5 named profile
-> official Hermes profile export
-> verified private Agent Image
-> OpenClaw dry-run loss report
-> explicit --yes
-> official OpenClaw agents add
-> mapped state validation and provenance
```

The source profile contained a valid synthetic `state.db`, identity, selected
memory, one compatible skill, one session, workspace state, and `.env`. The
database is physically present as `source/state.db` in the typed Hermes native
layer.

The dry-run ran before target creation and accounted for all ten source items:
four transformed, one redacted, and five unsupported. The actual report matched
the plan. `SOUL.md`, `MEMORY.md`, `USER.md`, and the compatible `SKILL.md` were
byte-equal at the target. `.env`, `state.db`, and sessions were absent.

`state.db` is reported as unsupported and preserved-not-imported; it is not
silently discarded or falsely translated. The target provenance names the
source image digest, and the official OpenClaw CLI recognized the target. Both
the Hermes profile digest and source image archive SHA-256 remained unchanged.

## Claim boundary

This establishes one P2 path, not pairwise portability between all harnesses.
It does not import Hermes session/database semantics and does not make a P3
behavioral-equivalence claim.

The machine-readable record is
`docs/evidence/hermes-to-openclaw-p2-2026-08-25.json`.
