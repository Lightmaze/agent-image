# OpenClaw real-host rollback evidence

Verdict: **PASS on Windows** for OpenClaw `2026.7.1-2` and Node `24.15.0`.

The rollback smoke restored the existing private test image to a new target
through the real official CLI. Immediately after official creation and
recognition it injected a deterministic validation exception. Production
rollback then used the official delete command and verified through the real
host that both registration and adapter-owned workspace were absent.

The source archive SHA-256 remained
`6dca01349783b33b20afd3b84ba4a70cfeb305df05f7f137148b3d9f4b2ca288`
before and after the failed operation.

The injected exception is a test-only fault point; target creation, deletion,
and residual-state checks are not mocked. This is Windows evidence and makes no
cross-platform OpenClaw rollback claim.
