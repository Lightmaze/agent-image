# Agent Image Protocol v0.1 Final Review

Date: 2026-08-26

This review closes the semantic, engineering, and local first-use questions for
the `v0.1.0-rc.1` candidate. A clean release-wheel environment can verify,
inspect, fresh-restore, and use the public hero image. It does not claim that a
public download URL or hosted release already exists.

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
passes from the rc.1 wheel and artifact on Windows, while Windows and WSL Linux
produce identical verify, inspect, and P1 restore reports. The behavior answer
remains limited to one synthetic mission under same-harness P1 and does not
claim P3.

The local adoption experience is complete. What remains is external state: a
real public destination, release asset URL, observed hosted CI, and a download
rerun from that URL.

## Release verdict

```text
Protocol:              PASS (beta schema freeze)
Core Toolchain:        PASS (local)
Hermes Adapter:        P1
OpenClaw Adapter:      P1 + P2 consumer
DSH Adapter:           P1 (shipped headless scope)
vHarness Adapter:      P1 (reference process-Guest scope)
Cross-Harness Demo:    PASS
Security:              PASS (local matrix; claim limits apply)
Privacy:               PASS
Trained-Agent Demo:    PASS (bounded same-harness synthetic mission)
Public Hero:           PASS (local Windows use; Windows + WSL P1)
Registry:              PASS (hero withheld until real URL exists)
Third-party Adapter:   PASS

Critical Blockers:
- Public repository destination, push, rc.1 tag/release, and asset upload are
  not yet authorized.
- Hosted Windows/Linux/macOS CI is configured but cannot be observed before the
  repository is pushed.

Decision:
[ ] RELEASE v0.1.0
[x] PREPARE LOCAL v0.1.0-rc.1 CANDIDATE
[x] HOLD public push/tag and v0.1.0
```

Public repository creation, push, and tags require explicit user authorization
at the execution point. Gate E is no longer the release blocker.
