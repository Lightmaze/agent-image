# Known v0.1 beta limitations

These are release boundaries, not implied future capability.

- Trained-agent Gate E is negative. Persistent files restored, but the
  preregistered behavioral improvement and retention thresholds did not pass.
  No portable-skill or P3 claim is permitted.
- P2 is implemented only for Hermes to OpenClaw. Native Hermes database and
  session state remain explicit unsupported loss rather than being translated.
- Adapters are pinned to exact tested harness contracts. Later versions are not
  assumed compatible.
- DSH P1 covers the shipped headless composition. Arbitrary external bundle
  installation and unresolved dependencies are not claimed.
- vHarness P1 covers a reference persistent process-Guest. Restored Host
  authority is fresh; kernel/journal/token authority is not transported, and
  strong isolation is not claimed.
- Real P1 evidence exists primarily on Windows; Hermes also passes local WSL
  Linux. Hosted Windows/Ubuntu CI and the macOS Core matrix are configured but
  have not been observed without an authorized remote push.
- Secret scanning is fail-closed and format-aware but is not universal DLP.
  Images may still contain sensitive private material and remain private by
  default.
- SHA-256 verifies content integrity, not publisher identity or trust. v0.1 has
  no signatures, trust store, encryption, OCI transport, or hosted Hub.
- v0.1 has no GUI, vHabitat, Team Image, universal RL system, or P3 behavioral
  portability implementation.
