# Agent Image Protocol v0.1 Final Review

Date: 2026-08-25

This review closes the semantic and engineering questions for the **protocol
substrate**. It does not claim that an external developer can already download
a public developed-agent image and independently complete the full install,
inspect, fresh-restore, and behavioral-comparison journey.

## Eight human questions

| # | Question | Verdict | Evidence |
|---:|---|---|---|
| 1 | Is this a protocol independent of vHarness? | Yes | Four built-ins plus a clean-room external wheel; vHarness types remain in its adapter/native layer. |
| 2 | Can Hermes, OpenClaw, DSH, and vHarness share one logical model? | Yes | Common semantic layers, privacy, provenance, digests, reports, and typed native escape hatch; no harness schema is Core-canonical. |
| 3 | Is untranslatable state honestly preserved as native or reported? | Yes | Typed native layers and `unsupported` outcomes are mandatory and reconciled. |
| 4 | Can a user see image privacy contents before publishing? | Yes | Build plans, per-layer inspect metadata, privacy summaries, and public redaction reports expose classification without payload. |
| 5 | Does native round-trip really work? | Yes | Pinned real P1 evidence for all four adapters; Hermes also passes local WSL Linux. |
| 6 | Does at least one semantic cross-harness migration really work? | Yes | Real Hermes-to-OpenClaw P2 with source immutability, target recognition, provenance, and loss report. |
| 7 | Was practice-induced behavioral state shown to survive freeze/restore? | Yes, bounded | The preregistered v0.2 run passed all nine checks; trained and fresh-restored scored 1.0, with identical state digests and zero action/offer/leak mismatches across 192 paired records. |
| 8 | Can a third party add a fifth harness without forking Core? | Yes | Separate clean-room wheel registers through `agent_image.adapters` and builds/verifies P0 in a fresh environment. |

All eight semantic acceptance questions are now Yes. The Gate E answer is
limited to one synthetic mission under same-harness P1 restore and does not
claim P3. Public release remains subject to observed remote CI and explicit
publication authorization.

All eight answers being Yes therefore means “the protocol is an honest local
release candidate,” not “the public adoption experience is complete.” The next
proof is a downloadable, public-safe hero image using the current protocol, not
a separate experience product or new Core mechanism.

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
Registry:              PASS
Third-party Adapter:   PASS

Critical Blockers:
- Hosted Windows/Linux/macOS CI is configured but not yet observed.
- Public repository creation, push, and tags are not authorized in this run.

Decision:
[ ] RELEASE v0.1.0
[x] PREPARE LOCAL v0.1.0-rc.1 CANDIDATE
[x] HOLD public push/tag and v0.1.0
```

Public repository creation, push, and tags require explicit user authorization
at the execution point. Gate E is no longer the release blocker.
