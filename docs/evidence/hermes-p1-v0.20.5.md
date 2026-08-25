# Hermes P1 Gate Evidence

Verdict: **PASS for the pinned contract and tested Windows environment**.

## Runtime pin

- Hermes Agent `0.20.5`
- tag `v2026.8.19`
- commit `fcbd1076a93841fa88855acce810e342a5b78101`
- Python `3.12.13`

Hermes does not publish this release as a normal PyPI wheel and deliberately
rejects wheel/sdist builds. The test followed the upstream development path: a
shallow checkout of the pinned tag plus editable installation.

## Round-trip

```text
Hermes named profile: source
-> official profile export
-> second Agent Image secret/privacy pass
-> 7-layer .aimg
-> official profile import as restored-v2
-> Agent Image invariant validation
-> hermes profile show restored-v2
```

The source inventory contained nine files. Eight safe items were preserved and
`.env` was explicitly redacted. The source profile digest was identical before
and after export. The restored target contained the same eight safe files with
matching SHA-256 digests, one skill, a recognized `SOUL.md`, and no configured
`.env`.

All seven image layers—identity, skill, two memory layers, experience,
workspace, and typed native state—were reconciled as `preserved` in the restore
report. Hermes independently recognized the new target profile.

Machine-readable evidence is in
`docs/evidence/hermes-p1-v0.20.5.json`.

## Claim boundary

This proves P1 native restore for one pinned Hermes contract and platform. It
does not prove cross-harness P2 or same-model behavioral P3. The profile contains
representative persistent state, not evidence that a trained behavior survived.
