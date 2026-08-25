# Project Status

## Objective

Create an open artifact protocol above agent harnesses that can save, audit,
publish, restore, and continue an agent's developed state without treating any
one harness as the semantic owner.

## Current stage

`Epoch 3 in progress` (Hermes, OpenClaw, and DSH P1 plus the first P2 path
verified; vHarness and fifth-adapter gates remain).

The current evidence proves pinned native round-trips for Hermes and OpenClaw
and the declared Hermes-to-OpenClaw semantic migration. It does not prove
developed-skill retention or behavioral portability.

## Gates

| Gate | Status | Evidence / blocker |
|---|---|---|
| Protocol | Alpha draft pass | `spec/v0.1/`, schema parse, Apache-2.0; external review pending |
| Core toolchain | Formal epoch pass | 46 tests; locked environment; wheel/sdist and installed CLI smoke; typed adapter SDK; production build/inspect/verify/redact/diff/restore/migrate and reports |
| Hermes | P1 pass, pinned | Hermes 0.20.5 / v2026.8.19 / fcbd107; Windows named-profile round-trip |
| OpenClaw | P1 and P2-consumer pass, pinned | 2026.7.1-2 / 0790d9f / Node 24.15.0; real Windows agent/workspace round-trip and Hermes migration |
| DSH | P1 pass, pinned | `@deepseek-ai/dsh@0.1.0-rc.6`; ordered in-box bundles and official dump round-trip on Windows; arbitrary external dependency reinstall not claimed |
| vHarness | Reconnaissance complete | Mapping exists; live Guest integration is absent |
| Security/privacy | Current pass with remaining hardening | 46 tests; both adapters fail closed on secrets; target scans clean; source immutability and loss accounting pass; real cross-platform rollback injection and Epoch 4 matrix pending |
| Trained-agent demonstration | Honest negative | 168 real calls; before 0.790960, after 0.743703, restored 0.710293; Gate E remains red |
| Registry | Not started | Depends on real adapters and evidence labels |

Release verdict: **LOCAL v0.1.0-alpha.1 CANDIDATE; HOLD v0.1.0.**

Current epistemic state: `EXTRACT:openclaw-p1-p2-evidence`.

The legacy EVC surface is maintained only as a knowledge capsule because the
local skill has been demoted. It has no implementation or lifecycle authority.

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

Implement DSH and vHarness against pinned real contracts, then prove a fifth
adapter can register through the public entry point without changing Core.
Gate E must be rerun successfully before a final `v0.1.0` tag is allowed.

## Source provenance

The bootstrap requirements came from `agent_image_v01_codex_docs.zip`, supplied
on 2026-08-24, SHA-256:

`17807012fe74fd040f9c46e55d51540cf9c2c689d6a7af5300dffd1514ff5933`

The inherited context came from `agent_image_v01_codex_context_pack.zip`,
supplied on 2026-08-24, SHA-256:

`0dcd610bb9759832d406026c99406c33899fdf75add86ec8cd6563677a66749a`
