# Run 60 — Build Plan Subject Binding

Status: engineering checkpoint; candidate, not merged implementation evidence.

## Decision

Structured-native publication should not treat a previously displayed plan and a later build as the same execution subject by convention.

The current CLI exposes a concrete mismatch: the non-`--yes` build-plan path passes only `source` and `policy` to `plan_build()`, while the executed `--yes` path also honors `--include-experience` and `--include-workspace`.

Run 60 therefore introduces a candidate `agent-image-build-plan/v0.1` artifact that binds:

- adapter id/version;
- source locator digest and source state digest;
- policy, include-experience, and include-workspace;
- exact structured-native atomic-unit subject digest, when present;
- a canonical self digest.

The persisted plan does not contain native payload bytes or the raw source locator.

## Two drift gates

```text
saved/reviewed plan
→ fresh source preflight
→ adapter capture/export
→ exact pre-publication capsule subject check
→ privacy finalization
→ publish
```

The native-unit subject is a canonical digest of `role + id + path + media_type + digest + size + source privacy`, so content, membership, path, media-type, size, or privacy drift invalidates the plan.

For structured-native exports:
- missing approved plan → `E_PLAN_REQUIRED`;
- plan/intent/source/capsule drift → `E_PLAN_STALE`.

The four current production adapter media types remain outside this structured-native requirement, preserving the existing direct build path during staged rollout.

## Evidence this checkpoint does and does not carry

Focused local candidate tests: 9 PASS; compile and Draft 2020-12 schema/example validation PASS.

This checkpoint does not claim a full repository regression, executable GitHub CI for Run 60, merge, MAGE runtime P1, capture consistency, profile closure, semantic migration, or behavioral retention.

The next integration gate is a clean-checkout composition of Run 57 Core envelope support + Run 59 producer finalization + Run 60 plan binding, followed by full repository regression and a real CLI saved-plan smoke.
