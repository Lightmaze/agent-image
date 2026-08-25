# Agent Image Protocol v0.1 Final Review

Date: 2026-08-25

## Eight human questions

| # | Question | Verdict | Evidence |
|---:|---|---|---|
| 1 | Is this a protocol independent of vHarness? | Yes | Four built-ins plus a clean-room external wheel; vHarness types remain in its adapter/native layer. |
| 2 | Can Hermes, OpenClaw, DSH, and vHarness share one logical model? | Yes | Common semantic layers, privacy, provenance, digests, reports, and typed native escape hatch; no harness schema is Core-canonical. |
| 3 | Is untranslatable state honestly preserved as native or reported? | Yes | Typed native layers and `unsupported` outcomes are mandatory and reconciled. |
| 4 | Can a user see image privacy contents before publishing? | Yes | Build plans, per-layer inspect metadata, privacy summaries, and public redaction reports expose classification without payload. |
| 5 | Does native round-trip really work? | Yes | Pinned real P1 evidence for all four adapters; Hermes also passes local WSL Linux. |
| 6 | Does at least one semantic cross-harness migration really work? | Yes | Real Hermes-to-OpenClaw P2 with source immutability, target recognition, provenance, and loss report. |
| 7 | Was practice-induced behavioral state shown to survive freeze/restore? | **No** | The preregistered 168-call Gate E run was negative; after and restored scores were below baseline. |
| 8 | Can a third party add a fifth harness without forking Core? | Yes | Separate clean-room wheel registers through `agent_image.adapters` and builds/verifies P0 in a fresh environment. |

Because question 7 is No, the acceptance rule forbids `v0.1.0`.

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
Trained-Agent Demo:    FAIL
Registry:              PASS
Third-party Adapter:   PASS

Critical Blockers:
- Gate E lacks positive behavioral improvement and fresh-restore retention.
- Hosted Windows/Linux/macOS CI is configured but not yet observed.

Decision:
[ ] RELEASE v0.1.0
[x] KEEP v0.1.0-beta.1 CANDIDATE
[x] HOLD rc.1, public push/tag, and v0.1.0
```

Public repository creation, push, and tags also require explicit user
authorization at the execution point. That authority would not override Gate E.
