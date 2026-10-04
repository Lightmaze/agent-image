# Native State Run 65 — Final Classification Boundary

Baseline before this checkpoint: `8f675598bad6d1ef22d0639814e20151f30b67f8`.

Run 65 removes a contradictory cumulative interpretation left over from Run 57:

- mixed **source** privacy may exist in a pre-publication structured-native staging capsule;
- the producer first identifies the atomic native restore unit;
- independently closed units may split; an inseparable unit may instead use conservative effective privacy (`unknown > private > public`);
- authoritative / preserved-derived payload bytes and digests remain unchanged by privacy promotion;
- the **finalized** capsule must have one embedded effective privacy class equal to the outer layer privacy;
- public policy removes an effective private/unknown unit whole; retaining a public subset requires a profile-specific projection with its own closure/loss/claim evidence.

Portability is not the privacy lattice. For `application/vnd.agent-image.native-capsule+tar` v0.1, the final outer **layer portability class** remains `adapter-specific`. A portable source/projection does not upgrade the whole native capsule; a cross-adapter portable view must be a separate layer with explicit semantics. Uninterpreted byte custody is opaque rather than a structured-native restore claim.

Local executable candidate centralizes these invariants in `native_classification.py` and reuses them from producer finalization and Core verification. Focused evidence: Run 65 lifecycle 8 PASS + Run 59 producer regression 12 PASS = 20 PASS; py_compile and post-Run64 patch application/equality PASS.

This checkpoint does **not** claim the Run 65 executable overlay is on GitHub, does not claim full repository/package CI, and does not promote MAGE P1.
