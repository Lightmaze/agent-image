# ADR-0003: Operation Evidence Reconstruction Rules

- Status: Proposed
- Date: 2026-09-26
- Depends on: ADR-0002

## Context

Applying the operation-receipt candidate to existing real evidence exposed two
problems in the first draft.

First, projection time and evidence strength are independent. The Hermes
continuation run was recorded before receipts existed, but its persisted
Continuation Binding already contains an exact verified-entry-set subject.
A post-hoc receipt may preserve that exact binding without inventing new
evidence.

Second, a continuation has multiple receiver resources. The live continuation
source can be deleted while the independently restored child remains active.
One unscoped cleanup target cannot represent that truthfully.

The same replay also found that the historical DSH P1 JSON records a
`manifest_digest`, not the v0.1 layer-root `image.digest`. That value must
not be relabeled as an Image digest merely to fit the receipt shape.

## Decision

1. Replace `legacy_projection` with `posthoc_projection`.
2. A post-hoc projection MAY be exactly artifact-bound only when its persisted
   source evidence already carried the exact subject binding. Provenance must
   name that source evidence.
3. If a historical record does not preserve a trustworthy Image subject
   binding, it remains capability evidence and is not forced into a receipt.
4. Cleanup is resource-scoped.
5. Replace the fixed receipt claim-boolean bag with an extensible claim ledger:
   `id`, `status`, and `basis`.
6. Positive claims must cite receipt observation, attachment, or persisted
   source-evidence ids. Diagnostics remain non-authoritative.
7. For continuation, the receipt binds the parent subject; the existing
   `agent-image-continuation-binding/v0.1` continues to bind parent, child,
   state delta, and receipt bytes.

## Consequences

The Hermes Ubuntu continuation can be reconstructed as an exact post-hoc
receipt because the original workflow log preserves its parent Image digest,
verified-entry-set digest, and verified Continuation Binding.

The historical DSH P1 record cannot currently be reconstructed as a conforming
receipt without replay or another preserved source that exposes the actual
v0.1 Image subject. Its existing capability evidence remains valid.

The historical OpenClaw continuation result remains valid capability evidence,
but the public persisted output available now does not expose enough exact
subject material to reconstruct the parent receipt subject. Replay is preferred
over inventing that missing binding.
