# ADR-0002: External Operation Evidence Receipts

- Status: Proposed for the continuation/evidence epoch
- Date: 2026-09-26

## Context

Agent Image already has several evidence surfaces, but they answer different
questions.

- v0.1 operation reports reconcile source inventory outcomes. They explain what
  was preserved, transformed, redacted, unsupported, or dropped.
- capability evidence under `docs/evidence/` records historical P0-P3 claims.
- `agent-image-continuation-binding/v0.1` binds exact parent/child artifacts,
  their state delta, and opaque transition-evidence bytes, but deliberately does
  not assert that the transition evidence is truthful.
- adapter-specific CI currently emits additional runtime, receiver, diagnostic,
  and cleanup facts that are not represented by one reusable object.

The DSH continuation work made this gap concrete. A top-level harness version was
not enough to identify the realized runtime; package-manager acquisition
provenance was not runtime identity; semantic diagnostics could explain a raw
P1 failure but could not redefine acceptance; and rollback/receiver-residue
outcomes mattered to the validity of the experiment. Hermes and OpenClaw
continuation experiments independently showed that state-delta and runtime
observations need to remain separate from Image identity.

Without a common execution-evidence object, each adapter can keep inventing a
different JSON blob, and a published capability claim can accidentally blur
artifact integrity, runtime realization, operation success, diagnostics, and
claim scope.

## Decision

Introduce a candidate external object:

```text
agent-image-operation-evidence/v0.1-candidate
```

It is an **operation evidence receipt**, not a new Image layer and not a new
portable identity field.

A receipt records, at minimum:

```text
subject
operation
adapter
runtime_requirement
runtime_realization
acceptance
cleanup
diagnostics
attachments
claim_boundary
```

### Subject

For operations over one Image, the subject SHOULD bind the exact verified
artifact using the existing verified-entry-set construction rather than only the
v0.1 layer-root `image.digest`.

For a continuation transition, the receipt MAY itself become the canonical
transition-evidence bytes consumed by
`agent-image-continuation-binding/v0.1`; the existing binding remains
responsible for parent/child/delta association.

### Runtime requirement and realization

`runtime_requirement` says what contract must be satisfied.

`runtime_realization` says what the receiver actually materialized or
observed. Adapter-specific realization details MAY be represented as typed
attachments identified by media type, digest, and size.

Neither field is Agent identity.

Receiver credentials, authority grants, access tokens, secret environment
values, or host-private paths MUST NOT be copied into a receipt. If a useful
realization artifact cannot be safely represented inline, the receipt SHOULD
contain only its sanitized digest-bearing attachment descriptor.

### Acceptance

The receipt MUST name the acceptance relation that produced its verdict.

For example, current DSH P1 uses raw `--dump-config` byte equality. A semantic
witness comparator can appear in `diagnostics`, but it MUST NOT silently become
an additional or substitute acceptance relation.

This makes diagnostic non-interference explicit:

```text
acceptance decides PASS/FAIL
diagnostics explain the result
diagnostic failure cannot replace the primary result
```

### Cleanup

A failed restore or migration receipt MUST record whether the staging/target
state was removed, quarantined, or left incomplete. A capability claim MUST NOT
treat an operation as a clean failure if cleanup itself failed.

### Attachments

Attachments are external evidence payloads referenced by:

```text
kind
media_type
digest
size
privacy
```

Examples include a sanitized runtime-resolution receipt, runner envelope,
structural diff, or benchmark result.

The receipt does not embed arbitrary logs by default.

### Claim boundary

The receipt carries explicit booleans or bounded statements for claims such as:

```text
archive_integrity_verified
native_restore_verified
semantic_migration_verified
behavioral_retention_verified
causal_development_verified
runtime_tree_bytes_verified
```

A missing or false stronger claim MUST NOT be inferred from a weaker successful
operation.

## Evidence stack

The intended relationship is:

```text
operation report
    = inventory accounting

operation evidence receipt
    = one execution's subject/runtime/acceptance/cleanup evidence

continuation binding
    = exact artifact/delta/evidence association

capability evidence
    = published claim backed by one or more receipts/bindings

audit/release packet
    = higher-level synthesis
```

These objects may reference one another by digest but do not collapse into one
identity object.

## Verification boundary

A generic Core verifier may verify:

- schema and canonical structure;
- exact Image subject binding;
- attachment digests and sizes when the attachment bytes are supplied;
- internal consistency of claim fields.

Generic verification MUST NOT upgrade an adapter-specific runtime observation
into truth, causal-development proof, or behavioral-retention proof.

A harness-specific verifier may validate stronger runtime semantics, but its
authority and version must be explicit.

## Compatibility

This ADR does not redefine the frozen v0.1 Image container, `image.digest`,
layer identity, P0-P3 definitions, or the existing continuation-binding schema.

The candidate receipt remains external until at least two real adapters emit it
without requiring harness-specific Core logic.

## Consequences

- DSH runtime-realization work gets a stable place to record resolution,
  materialization policy, raw acceptance, failure-only diagnostics, and rollback
  outcome without turning them into Agent identity.
- Hermes/OpenClaw continuation evidence can adopt the same receipt without
  rewriting their native-state formats.
- MAGE or another graph/hypergraph backend can later attach checkpoint,
  relation-closure, event-log, and derived-index evidence without forcing those
  structures into a universal Core schema.
- Existing historical evidence files remain valid historical records; they are
  not retroactively rewritten into receipts.
- A receipt is evidence of an observed operation, not a portable authority token
  and not a proof that the represented development was causal.
