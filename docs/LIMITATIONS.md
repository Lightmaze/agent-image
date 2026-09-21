# Known v0.1.0-alpha.2 limitations

These are release boundaries, not implied future capability.

- Trained-agent Gate E passed for one synthetic, mission-specific Hermes 0.20.5
  experiment. It does not establish real-world negotiation transfer,
  independent replication, delayed retention, other models or harnesses, or P3
  cross-harness behavioral portability. The earlier 48-episode append-only
  probe remains a valid negative result for that exact design.
- P2 is implemented only for Hermes to OpenClaw. Native Hermes database and
  session state remain explicit unsupported loss rather than being translated.
- Adapters are pinned to exact tested harness contracts. Later versions are not
  assumed compatible.
- DSH P1 covers the shipped headless composition. Arbitrary external bundle
  installation and unresolved dependencies are not claimed.
- vHarness P1 covers a reference persistent process-Guest. Restored Host
  authority is fresh; kernel/journal/token authority is not transported, and
  strong isolation is not claimed.
- At the alpha.2 release, Core CI passed on hosted Windows, Ubuntu, and macOS
  with Python 3.11–3.13; real Hermes smoke passed on hosted Windows and Ubuntu.
  Public-download Hermes restore on Windows and local WSL Linux is documented
  in the [publication evidence](evidence/publication-v0.1.0-alpha.2-2026-09-07.md).
  See the [12 successful release-tag CI jobs](https://github.com/Lightmaze/agent-image/actions/runs/34177445943).
  Other pinned native-runtime evidence remains primarily Windows-specific;
  macOS Core success does not establish macOS harness P1, and these historical
  results do not certify later harness versions or untested commits.
- Secret scanning is fail-closed and format-aware but is not universal DLP.
  Images may still contain sensitive private material and remain private by
  default.
- SHA-256 verifies content integrity, not publisher identity or trust. v0.1 has
  no signatures, trust store, encryption, OCI transport, or hosted Hub.
- v0.1 has no GUI, vHabitat, Team Image, universal RL system, or P3 behavioral
  portability implementation.
