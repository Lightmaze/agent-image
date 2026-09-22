# OpenClaw continuation state — second-backend challenge

Date: 2026-09-22

Status: **PASS for native persistent-state continuation and exact evidence binding; FAIL for the stronger assumption that the current raw native-layer digest is a provenance-free state commitment.**

This experiment challenges the Hermes-derived continuation mechanism on the repository's already supported pinned OpenClaw lane. It does not upgrade OpenClaw, call a model, or claim learning or behavioral retention.

## Pinned contract

The run uses the existing adapter contract unchanged:

- OpenClaw `2026.7.1-2`, tag `v2026.7.1-2`, adapter pin commit `0790d9f`;
- Node `24.15.0`;
- npm `11.12.1`;
- Windows hosted runner;
- isolated `OPENCLAW_STATE_DIR` and adapter-owned workspace root.

The existing P1 evidence for this pin is Windows-scoped. The continuation experiment therefore adds only a Windows real-runtime job and does not widen the platform claim.

OpenClaw documents the agent workspace as persistent Agent state and names `MEMORY.md` / `memory/**` as durable memory surfaces. The transition in this test is a direct file update to that documented surface. No model/provider call or credentials are involved.

## Experiment

The CI path is:

```text
source agent
  -> parent private Agent Image
  -> fresh P1 restore as `continued`
  -> immediate no-op refreeze control
  -> update `workspace/MEMORY.md`
  -> child private Agent Image
  -> delete live `continued` registration
  -> independent P1 restore as `child-restored`
  -> truthful state/metadata diff
  -> Continuation Evidence Binding
  -> JSON round-trip + verification
```

Both parent and child builds check that the source inventory digest is unchanged during the read-only export. The child restore occurs only after the live continuation registration has been removed, and the restored memory must contain both inherited parent content and the post-restore update.

## Observed result

Workflow run `35679162443`, head `eb98453acc4664b9f878caf53ea5ac5f0298809f`, completed successfully. All 15 jobs passed, including the existing Core/package/Hermes matrix and the new `real-openclaw-continuation` job.

The real changed transition produced:

```text
state_changed:
  openclaw-memory-03e39a6aa2ff
  openclaw-native-agent

metadata_changed:
  openclaw-identity-c278cbbf0209
  openclaw-identity-ddc76a1ccedd
  openclaw-memory-334793f55d0a
  openclaw-workspace-127985d1fa9a
  openclaw-workspace-45cb0d30baf8
  openclaw-workspace-7073a7d840a7
  openclaw-workspace-b64df4e7fbd4

added: []
removed: []
```

The semantic `MEMORY.md` layer and the typed native layer therefore both reflect the durable memory update. The independent child restore validates P1 and contains both inherited and new memory.

The Continuation Binding also verifies:

```text
binding_digest:
  sha256:5f7765524b4a36b33c0cada2e637e65155d03a530e796d7c700e61c13c788361
state_delta_digest:
  sha256:43744c2cd0ed178c91f36b697eab48e01edd6ec0b1a0d70e445410f9d4df79d6
transition_evidence_digest:
  sha256:d90db2342c0563fc421603cfa8508e47707d94df488a5b92aff3002a54735517
```

The generic verifier continues to return `causal_transition_verified=false` and `behavioral_retention_verified=false`.

## No-op control: a real state-boundary failure

The immediate no-op refreeze, before any intended Agent-state mutation, produced:

```text
state_changed:
  openclaw-native-agent
```

while unchanged semantic layers were correctly classified as metadata-only changes caused by producer-instance provenance.

The native false positive is explained by the current adapter implementation. `_native_archive(source_agent, entries)` inserts this capture record inside the typed native payload:

```json
{"source_agent":"<producer instance name>","contract":"v2026.7.1-2"}
```

at `meta/agent.json`. During restore, the adapter removes `meta/agent.json` before interpreting or materializing workspace, agent, and session state. The `source_agent` value therefore changes native payload bytes but has no receiver-state semantics.

This yields a concrete counterexample to a hidden assumption in `agent-image-layer-state-projection/v0.1`:

> For an opaque/native layer, the raw layer digest is not automatically a truthful state commitment merely because the layer is restorable.

A capsule may contain capture/provenance metadata that the receiver discards before materialization.

## Design correction: Native State Commitment Boundary

Until this is corrected, the continuation mechanism should be described more narrowly:

- the **Continuation Evidence Binding** has now survived a second real backend: it can bind exact parent/child artifacts, recomputed delta, and runtime observation on both Hermes and OpenClaw;
- the current **layer-state projection is not yet backend-neutral for opaque native layers**, because a raw native payload digest may include capture-only metadata.

For native state to participate in developmental delta or a future Authoritative State Commitment, the adapter must provide one of these guarantees:

1. the native payload bytes contain only receiver-materialized/restorable state; or
2. the adapter defines a versioned native-state projection/commitment that excludes capture-only provenance, rebuildable material, receiver-local authority, and other bytes not interpreted as restored Agent state.

For the current OpenClaw adapter, the smallest correction is to stop putting producer instance identity inside newly generated native payload bytes. Producer identity already belongs in manifest provenance and operation evidence. Legacy images that contain `meta/agent.json` must remain readable/restorable; the current restore path already ignores that member before materialization.

This correction is tracked in issue #9. It does not require redefining the published v0.1 `image.digest`, changing old release assets, or weakening legacy restore compatibility.

## Claim boundary

This experiment supports only the following bounded statement:

> On the pinned Windows OpenClaw `2026.7.1-2` contract, a freshly restored Agent's documented persistent workspace memory can be changed, refrozen, independently restored, and exactly bound to the observed parent/child delta and runtime evidence.

It does **not** establish:

- learning;
- causal developmental-transition proof;
- behavioral retention or P3;
- later OpenClaw compatibility;
- cross-platform OpenClaw continuation;
- that every opaque/native layer digest is an authoritative Agent-state commitment.

The negative no-op control is part of the result rather than a test nuisance: it identifies the next adapter/Core boundary that must be fixed before stronger lineage semantics are justified.
