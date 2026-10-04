# Agent Image Integration Graduation — 2026-10-04

Status: active integration branch work; not merged to `main`.

## What is now repository code

Two stacked integration slices have moved core candidate mechanisms from chat/local overlays into the real repository.

### Slice 1 — structured-native producer + Core

Branch: `web/agent-image-integration-graduation`

Head at graduation: `454321db64ae5f0c6d6210c1dd3bccfbde7b1845`

Draft PR: #19

Implemented:

- safe, non-extracting `agent-image-native-capsule/v0.1` reader;
- native realization sidecar binding;
- atomic native privacy classification/planning;
- producer-side structured-native finalization between adapter export and image publication;
- Core structured-native envelope verification;
- metadata-only structured-native inspect and diff;
- whole-layer public redaction boundary;
- realization/profile and nested secret checks.

The existing Hermes/OpenClaw/DSH/vHarness native formats remain compatible. If an export does not contain the structured-native capsule media type, producer finalization is a no-op.

CI evidence:

- push run `37227682264`: success, 12/12 jobs;
- Linux/macOS/Windows × Python 3.11/3.12/3.13;
- repository pytest, mock-point scan, mojibake scan, registry validation, package build;
- installed-package smoke;
- real Hermes smoke on Ubuntu and Windows.

### Slice 2 — reviewed capture → exact prepared publication

Branch: `web/agent-image-prepared-publication-integration`

Head at graduation before this documentation commit: `00874d10608f059ceee9f3bf76d553025a109ae7`

Draft PR: #20, stacked on #19.

Implemented:

- `agent-image-build-plan/v0.1` reviewed pre-capture plan;
- source locator/state/intent binding;
- structured-native atomic-unit subject reconciliation;
- exact prepared Agent Image receipt;
- recoverable prepared workspace:
  - `seal.json`
  - `candidate.aimg`
  - `receipt.json`
- `prepare-build`, `recover-prepared`, `publish-prepared` CLI surfaces;
- source-free exact publication;
- one-step direct publication rejected for structured-native sources;
- legacy direct build retained for current non-structured adapters.

The publication API receives no source locator or adapter. Final publication consumes only an already captured candidate plus its receipt/workspace.

CI evidence:

- push run `37228042599`: success, 12/12 jobs;
- same full matrix and packaging/smoke gates as Slice 1;
- real Hermes regression additionally proves prepared publication emits the exact candidate bytes without reopening source state.

## Evidence boundary

These repository CI results establish the generic producer/Core/build-publication path.

They do **not** establish:

- MAGE P1 runtime restore;
- MAGE full `MageMemory load → query → write → flush/freeze → reload`;
- behavioral retention;
- causal learning continuity;
- generic cross-backend semantic migration.

## Candidate mechanisms intentionally not promoted yet

The following remain profile/candidate work until their next integration gate:

- MAGE realization preflight;
- coherent target-store re-embedding migration;
- typed native transition evidence;
- full process-observed MAGE capture/runtime continuation;
- generic staged native restore refactor beyond current production adapters.

The integration rule is now: land generic mechanisms only after they have a coherent product path and full repository CI; keep backend-specific semantics in the profile until a second independent backend justifies Core promotion.
