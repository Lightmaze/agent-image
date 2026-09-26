# ADR-0004: Evidence Cut and Acyclic Continuation Binding

- Status: Candidate / proposed
- Date: 2026-09-26
- Depends on: ADR-0002, ADR-0003

## Context

Turning Operation Evidence Receipt from a post-hoc projection into a native
producer exposes a dependency-order problem.

For continuation, the evidence chain is:

```text
operation evidence receipt
  -> canonical transition-evidence bytes
  -> Continuation Binding
  -> binding verification
  -> CI/capability reporting
```

A receipt consumed as `transition_evidence` cannot truthfully contain the
statement "this Continuation Binding verified." The binding digest depends on
the receipt bytes, so that claim would create a logical cycle.

GitHub Actions run `36238409885`, job `108394318194`, completed the real
pinned OpenClaw continuation successfully on commit
`f6d94d078286530e3f8031ae7f55fb7c560b7052`: no-op refreeze had no
state-changing layers, both parent and child restores validated P1, and the
Continuation Binding verified.

## Decision

A native receipt is finalized after authoritative operation acceptance and
operation-scoped cleanup, but before any object that consumes the receipt bytes
is built or verified:

```text
parent P1 restore
-> no-op control
-> persistent-memory mutation
-> child build
-> delete live continuation source
-> independent child P1 restore
-> finalize operation receipt
--- EVIDENCE CUT ---
-> build Continuation Binding from exact receipt bytes
-> verify binding
-> emit CI/capability report
-> outer test teardown
```

Receipt resource outcomes describe state at this cut. Later CI teardown is test
hygiene, not continuation semantics.

A native receipt used as continuation transition evidence MUST NOT claim facts
produced after its bytes are fixed, including binding verification. A post-hoc
receipt MAY cite a historically verified binding when persisted source evidence
already contains that result.

Exact parent/child/delta/evidence association remains the responsibility of
`agent-image-continuation-binding/v0.1`.

## Cross-object semantic link

A verified Continuation Binding proves that exact receipt bytes were bound, but
it does not parse those bytes. A higher-level evidence verifier therefore MUST
also check that the receipt's exact parent subject matches the binding's
`parent` subject.

For a native continuation receipt, the composite verifier checks:

```text
sha256(receipt bytes) == binding.transition_evidence.digest
receipt.subject.spec == binding.parent.spec
receipt.subject.image_digest == binding.parent.image_digest
receipt.subject.verified_entry_set == binding.parent.verified_entry_set
receipt.operation.kind == continue_step
receipt exact-binding claim == not_claimed at the evidence cut
```

Only after those checks and `verify_continuation_binding(...)` succeed may an
outer report assert that the receipt, exact parent/child artifacts, state delta,
and transition evidence were associated by the binding.

This semantic-link verification is deliberately outside the receipt bytes, so
the evidence graph remains acyclic.

## Consequences

- Receipt bytes are stable binding input.
- Binding verification cannot become self-referential.
- Operation resource state is not confused with outer CI teardown.
- Binding-byte integrity and receipt-subject semantics are both checked.
- OpenClaw can become the second real adapter producer without adding
  harness-specific fields to Agent Image Core.
- DSH can reuse the same evidence cut once its continuation path is ready.
