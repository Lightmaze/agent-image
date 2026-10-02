# Run 61 — Reviewed Build Plan Execution Binding

Status: engineering checkpoint; candidate, not merged implementation evidence.

## Decision

Run 60's reviewed build plan is now treated as an execution subject rather than a display-only preview.

Candidate `agent-image-build-plan/v0.1` binds:
- adapter id/version;
- hashed source locator (never raw locator);
- fresh source-state digest;
- policy, include-experience, include-workspace;
- exact pre-finalization structured-native atomic-unit subject;
- canonical plan self digest.

Execution uses two drift gates:

```text
approved plan
→ fresh inspect_source/source+intent check
→ adapter capture/export
→ recompute actual structured-native object subject
→ privacy finalization
→ publish
```

Missing approved plan for structured-native publication is `E_PLAN_REQUIRED`. Source, intent, adapter, payload, membership, path, media-type, size, or source-privacy drift is `E_PLAN_STALE`.

The native object subject binds `role + id + path + media_type + digest + size + source_privacy` and is checked before Run 59 privacy promotion, so legitimate capsule-control rewriting does not masquerade as source drift.

Legacy Hermes/OpenClaw/DSH/vHarness native media types remain on the direct build path during staged rollout.

## Evidence

Focused local candidate suite: 13 PASS. Draft 2020-12 schema/example validation and py_compile PASS.

This checkpoint does not claim full repository regression, executable Run 61 GitHub CI, merge, MAGE runtime P1, capture consistency, profile closure, migration equivalence, or behavioral retention.
