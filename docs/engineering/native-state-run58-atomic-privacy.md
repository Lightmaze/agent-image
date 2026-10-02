# Native State Run 58 — Atomic Privacy Planning

Baseline branch head before this checkpoint: `0dec47cecf98e96858f263a30fb9bd3089b10173`.

Run 58 corrects an overly strict producer-side interpretation from Run 57:

- frozen v0.1 still requires different **effective** privacy / portability classes to use separate layer descriptors;
- an inseparable structured-native restore unit may conservatively promote lower-sensitivity source items to one effective class without rewriting authoritative payload bytes;
- `secret` remains reject; `unknown` remains unresolved;
- public export keeps an all-public atomic unit or removes a non-public atomic unit whole;
- partial public native state requires a profile-specific projection with its own closure/loss/claim evidence.

MAGE differential using the existing whole-store validator:

- `nodes-public / nodes-private / edges / hyperedges / events` -> rejected because the authoritative object set changed;
- unchanged `nodes / edges / hyperedges / events` with conservative effective privacy -> structurally profile-valid.

This checkpoint does **not** claim production adapter integration, overlay CI, or MAGE runtime P1.
