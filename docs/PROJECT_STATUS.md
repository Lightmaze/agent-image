# Project Status

## Objective

Create an open artifact protocol above agent harnesses that can save, audit,
publish, restore, and continue an agent's developed state without treating any
one harness as the semantic owner.

## Current stage

`P1 alpha 工程闭环` (formal architecture anchored; first real adapter gated;
standalone reproducibility gate in progress).

The current epoch proves a native round-trip for a real named Hermes profile
against a pinned official contract. It does not prove cross-harness migration,
developed-skill retention, or behavioral portability.

## Gates

| Gate | Status | Evidence / blocker |
|---|---|---|
| Protocol | Alpha draft pass | `spec/v0.1/`, schema parse, Apache-2.0; external review pending |
| Core toolchain | Formal epoch pass | 28 tests; locked environment; wheel/sdist and installed CLI smoke; production build/inspect/verify/redact/diff plus adapter-dispatched restore |
| Hermes | P1 pass, pinned | Hermes 0.20.5 / v2026.8.19 / fcbd107; Windows named-profile round-trip |
| OpenClaw | Not started | CLI/runtime unavailable in current environment |
| DSH | Reconnaissance only | CLI visible; current public contract must be pinned before implementation |
| vHarness | Reconnaissance complete | Mapping exists; live Guest integration is absent |
| Security/privacy | Current pass | 28 tests, second-pass Hermes scanning, opt-in native experience/workspace, encoding and mock scans; external audit pending |
| Demonstration/registry | Not started | Depends on real adapters |

Release verdict: **LOCAL v0.1.0-alpha.1 CANDIDATE; HOLD v0.1.0.**

Current epistemic state: `FORMALIZE:hermes-p1`.

Only the independently selected content kernel was requalified from the
bootstrap. Fixture-bound service/CLI code remains non-authoritative. Hermes P1
was built behind the adapter boundary and formalized from real gate evidence.

## Highest failure risks

1. Adapter-specific files leaking into the core schema.
2. Fixture success being described as real harness support.
3. Secrets or private state entering a public image.
4. Silent loss during export, restore, or migration.
5. Self-referential or non-deterministic archive digests.

## Next release gate

Complete the preregistered same-model trained-agent experiment before schema
freeze. If real model access is unavailable or the result is negative, preserve
that evidence honestly and continue with OpenClaw P1 plus the required
Hermes-to-OpenClaw P2 loss-report path without making a behavioral claim.

## Source provenance

The bootstrap requirements came from `agent_image_v01_codex_docs.zip`, supplied
on 2026-08-24, SHA-256:

`17807012fe74fd040f9c46e55d51540cf9c2c689d6a7af5300dffd1514ff5933`

The inherited context came from `agent_image_v01_codex_context_pack.zip`,
supplied on 2026-08-24, SHA-256:

`0dcd610bb9759832d406026c99406c33899fdf75add86ec8cd6563677a66749a`
