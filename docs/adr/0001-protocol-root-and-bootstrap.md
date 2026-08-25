# ADR-0001: Independent protocol root and Python bootstrap

- Status: Accepted for bootstrap epoch
- Date: 2026-08-24

## Context

The workspace already contains Habitat and an untracked vHarness alpha tree.
Agent Image must remain harness-neutral. The active shell has Python 3.12 and
PyYAML, while Node/npm are not directly available. Hermes and OpenClaw are not
installed; DSH is visible; vHarness has source but only a replay/mock Guest.

## Decision

Create `agent-image/` as an independent Python 3.11+ package inside the current
workspace, without a nested Git repository. Use a deterministic tar+gzip `.aimg`
container, YAML manifests, JSON Schema, SHA-256, and no database. Keep all
harness-specific translation behind adapter interfaces.

The first adapter is `dev.agentimage.fixture`. It consumes an explicit inventory
and exists only to exercise Core acceptance tests. It is not a fifth production
harness and may not be cited as native-restore evidence.

Do not reuse vHarness OCI code or `HarnessImage` types in Core. A future vHarness
adapter may preserve its OCI layout as an opaque native layer and translate
confirmed semantic claims into Agent Image layers.

## Consequences

- Core can run and be tested in the current environment.
- The protocol does not inherit vHarness authority, state, or transport semantics.
- OCI remains a future transport option rather than a v0.1 premise.
- Real adapter claims remain blocked until pinned upstream contracts and live
  round-trip evidence exist.
- Project license selection remains unresolved; no release is authorized until a
  license is selected.

