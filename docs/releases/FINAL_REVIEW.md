# Agent Image Protocol v0.1 Final Review

Updated: 2026-09-07 (America/New_York)

This review closes the semantic, engineering, and public first-use questions
for the [v0.1.0-alpha.2 preview](https://github.com/Lightmaze/agent-image/releases/tag/v0.1.0-alpha.2).
The public repository and six downloadable assets are live. Fresh environments
can install, verify, inspect, restore, and use the public hero image.

## Eight human questions

| # | Question | Verdict | Evidence |
|---:|---|---|---|
| 1 | Is this a protocol independent of vHarness? | Yes | Four built-ins plus a clean-room external wheel; vHarness types remain in its adapter/native layer. |
| 2 | Can Hermes, OpenClaw, DSH, and vHarness share one logical model? | Yes | Common semantic layers, privacy, provenance, digests, reports, and typed native escape hatch; no harness schema is Core-canonical. |
| 3 | Is untranslatable state honestly preserved as native or reported? | Yes | Typed native layers and `unsupported` outcomes are mandatory and reconciled. |
| 4 | Can a user see image privacy contents before publishing? | Yes | Build plans, per-layer inspect metadata, privacy summaries, and public redaction reports expose classification without payload. |
| 5 | Does native round-trip really work? | Yes | Pinned real P1 evidence for all four adapters; Hermes also passes local WSL Linux. |
| 6 | Does at least one semantic cross-harness migration really work? | Yes | Real Hermes-to-OpenClaw P2 with source immutability, target recognition, provenance, and loss report. |
| 7 | Was practice-induced behavioral state shown to survive freeze/restore? | Yes, bounded | Private Gate E passed all nine checks; the public-safe derivative then scored 1.0 versus a 0.481521 fresh control on new scenarios and returned the expected `counter 260` after release-bundle restore. |
| 8 | Can a third party add a fifth harness without forking Core? | Yes | Separate clean-room wheel registers through `agent_image.adapters` and builds/verifies P0 in a fresh environment. |

All eight semantic acceptance questions are Yes. The hero path additionally
passes from the alpha.2 wheel and artifact on Windows, while Windows and WSL Linux
produce identical verify, inspect, and P1 restore reports. The behavior answer
remains limited to one synthetic mission under same-harness P1 and does not
claim P3.

The public adoption path is complete: anonymous downloads passed checksum
verification, clean Windows wheel/sdist installation, and real Windows/WSL
Hermes restore. The downloaded Agent returned `counter 260` on the README task.
All 12 hosted release-tag CI jobs passed. See
[publication evidence](../evidence/publication-v0.1.0-alpha.2-2026-09-07.md).

## Release verdict

```text
Protocol:              PASS (alpha compatibility boundary)
Core Toolchain:        PASS (local and hosted Windows/Linux/macOS)
Hermes Adapter:        P1
OpenClaw Adapter:      P1 + P2 consumer
DSH Adapter:           P1 (shipped headless scope)
vHarness Adapter:      P1 (reference process-Guest scope)
Cross-Harness Demo:    PASS
Security:              PASS (local matrix; claim limits apply)
Privacy:               PASS
Trained-Agent Demo:    PASS (bounded same-harness synthetic mission)
Public Hero:           PASS (public download; Windows use; Windows + WSL P1)
Registry:              PASS (public HTTPS hero asset; private records withheld)
Third-party Adapter:   PASS

External publication:
- Public repository, alpha.2 tag, prerelease, and six assets are live.
- Twelve hosted CI jobs passed; anonymous download/install/restore/use passed.

Decision:
[ ] RELEASE v0.1.0
[x] RELEASE v0.1.0-alpha.2 PUBLIC PREVIEW
[x] HOLD final v0.1.0
```

Publication was explicitly authorized. This completes the current alpha release,
not the later final v0.1.0 development scope.
