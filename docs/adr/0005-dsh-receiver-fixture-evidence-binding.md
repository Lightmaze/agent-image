# ADR-0005: Bind Validated Receiver Fixtures Into DSH Transition Evidence

- Status: Candidate / proposed
- Date: 2026-09-27
- Depends on: DSH pinned contract, ADR-0004

## Context

The DSH continuation and witness-diagnostic lanes currently acquire the same
receiver runtime differently. The diagnostic lane has already succeeded with a
receiver-local cached installation, while the continuation lane most recently
failed before executing DSH during a global npm self-update.

The pinned contract already distinguishes receiver-runtime realization from
Agent identity and records a known-good package-identity projection:

```text
sha256:5d3de0bfbc06aae899246d27f2f32ae68b88241f8c1b4472688785b50f202e22
```

A validated receiver fixture is still insufficient if the continuation evidence
does not say which validated fixture actually interpreted the parent and child
state.

## Decision

DSH candidate lanes use one executable receiver-fixture validator. It emits a
receiver-fixture receipt that records:

- top-level DSH requirement;
- Node test profile;
- actual acquisition-tool provenance;
- package-lock resolution witness;
- package-identity projection;
- explicit proof boundaries.

The continuation and diagnostic scripts consume that receipt rather than
reconstructing receiver-runtime facts independently.

For continuation, the full validated fixture receipt is included in the exact
transition-evidence bytes before Continuation Binding construction.

Therefore:

```text
receiver fixture validated
-> receipt consumed by continuation
-> receipt embedded in transition evidence
-> Continuation Binding commits exact evidence bytes
```

The receipt remains execution evidence, not Agent identity, Harness Image, or a
runtime-tree digest.

## Non-goals

This ADR does not:

- relax raw P1 dump-config equality;
- make npm version an Agent identity field;
- claim the lockfile proves post-install runtime bytes;
- modify Agent Image v0.1;
- claim continuation success before a real run passes the fixture gate.

## Consequence

A future DSH continuation failure after fixture validation can be interpreted
against an exact receiver-resolution context. A success can bind the same
receiver realization into the continuation evidence without inventing a new
identity layer.
