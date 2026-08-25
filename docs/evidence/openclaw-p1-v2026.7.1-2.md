# OpenClaw P1 Gate Evidence

Verdict: **PASS for the pinned Windows contract**.

## Contract and runtime

- OpenClaw `2026.7.1-2` / tag `v2026.7.1-2` / CLI commit `0790d9f`
- Node `24.15.0`
- npm `11.12.1`
- isolated `OPENCLAW_STATE_DIR` and adapter-owned workspace root

The pinned npm package does not admit Node `24.13.0`; its Node 24 range starts
at `24.15.0`. The release smoke therefore used `24.15.0`, and the plan mismatch
is recorded as `NEEDS_DOC_FIX` rather than hidden.

## Round-trip

```text
official agents add source
-> inventory agent/workspace/session state
-> private source.aimg with typed native state
-> verify
-> official agents add restored4
-> restore newly owned state
-> official agents list --json recognition
-> source-inventory and layer reconciliation
```

The source inventory contained 15 items. Thirteen file items were preserved
byte-for-byte, registration was deliberately transformed through the official
CLI, and `.git` metadata was explicitly unsupported. All 12 image layers were
reconciled as preserved. The source agent digest after restore matched the
digest recorded during export.

Sessions were included only because this private smoke explicitly opted into
experience. Unit coverage proves that they are excluded by default. The target
scan covered 13 non-Git files and found no secret filename or structured secret
field.

## Failure learned during the smoke

An earlier validation failure used npm's Windows `.cmd` shim without an
explicit Node executable. Its rollback could not invoke `node`; the adapter
then swallowed the delete error, leaving host registration and an attestation
after deleting the workspace. The residual was detected with the official CLI
and removed through the official delete command.

The formal path now executes the official `openclaw.mjs` with an explicit Node
binary. Rollback verifies both host registration and workspace removal and
raises `E_ROLLBACK_FAILED` if either survives. Deterministic failure injection
is covered by tests. A later Epoch 4 smoke also created a target through the
real pinned Windows host, injected a post-create validation failure, and
verified official deletion plus complete workspace cleanup. Cross-platform
OpenClaw failure injection remains unclaimed.

## Claim boundary

This is P1 for one pinned OpenClaw version and tested Windows environment. It
does not prove later-version compatibility, whole-home portability, session
semantic migration, P3, or cross-platform OpenClaw rollback behavior.

The machine-readable record is
`docs/evidence/openclaw-p1-v2026.7.1-2.json`.
