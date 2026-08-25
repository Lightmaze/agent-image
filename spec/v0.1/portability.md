# Portability Levels

## P0 — Archive

The image is safe to inspect and verify. No executable restoration is claimed.

## P1 — Native Restore

The source and target use the same harness. The adapter restores declared core
state into a new target and validates harness-specific invariants. P1 need not be
byte-identical, but unsupported native state is blocking or explicitly reported.

## P2 — Semantic Migration

The target uses a different harness. A dry-run loss report precedes execution.
Portable identity, skills, selected memory, and selected workspace may be
preserved or transformed. Native state remains preserved-not-imported or
unsupported. No source secret or runtime authority is copied.

## P3 — Behavioral Portability

The restored/migrated agent passes a declared benchmark using an unchanged model
reference. P3 evidence names the suite, before/after results, environment, and
evidence status. P3 is not part of the v0.1 release gate.

