# Project Status

## Objective

Create an open artifact protocol above agent harnesses that can save, audit,
publish, restore, and continue an agent's developed state without treating any
one harness as the semantic owner.

## Current stage

`v0.1.0-alpha.2 public preview published` (all four adapters, the first
P2 path, fifth-adapter extension, Registry, local hardening, trained-agent gate,
public hero artifact, and operator-first release bundle are implemented).

The **open-source adoption experience** now closes from a public download:
[Agent Image](https://github.com/Lightmaze/agent-image) and the
[alpha.2 release](https://github.com/Lightmaze/agent-image/releases/tag/v0.1.0-alpha.2)
are live. Clean Windows environments installed the downloaded wheel and source
distribution as `agent-image==0.1.0a2`; Windows and WSL Linux verified and
fresh-restored the downloaded hero through real Hermes. The restored Agent
completed the README synthetic task with `counter 260`. All 12 release-tag CI
jobs passed. [Publication evidence](evidence/publication-v0.1.0-alpha.2-2026-09-07.md).

The current evidence proves pinned native round-trips for Hermes, OpenClaw,
DSH, and the scoped vHarness reference Guest, plus the declared
Hermes-to-OpenClaw semantic migration. A preregistered synthetic Hermes
experiment also proves bounded mission-specific developed-state retention
through fresh P1 restore. Cross-harness P3 behavioral portability remains
unverified.

## Gates

| Gate | Status | Evidence / blocker |
|---|---|---|
| Protocol | Alpha compatibility boundary | `spec/v0.1/`, immutable published artifacts, documented forward evolution, Apache-2.0 |
| Core toolchain | Formal epoch pass | 85 tests plus 11 subtests; locked environment; wheel/sdist installed CLI smoke; typed adapter SDK and public entry points; production build/inspect/verify/redact/diff/restore/migrate/registry and reports |
| Hermes | P1 pass, pinned | Hermes 0.20.5 / v2026.8.19 / fcbd107; hosted Windows/Ubuntu round-trip and public-package Windows/WSL restore |
| OpenClaw | P1 and P2-consumer pass, pinned | 2026.7.1-2 / 0790d9f / Node 24.15.0; real Windows agent/workspace round-trip and Hermes migration |
| DSH | P1 pass, pinned | `@deepseek-ai/dsh@0.1.0-rc.6`; ordered in-box bundles and official dump round-trip on Windows; arbitrary external dependency reinstall not claimed |
| vHarness | P1 pass, scoped and pinned | `0.1.0-alpha.1`; real vhd/vh and non-mock persistent process-Guest; fresh Host authority and Host-recorded provenance; strong isolation and DSH Guest are not claimed |
| Fifth adapter | C0/P0 extension pass | Separate wheel discovered through `agent_image.adapters` in a fresh offline venv; no Core schema fork |
| Security/privacy | Local hardening pass | path/symlink/structured-secret/privacy/no-overwrite/no-silent-loss matrix; malformed structured data fails closed; real OpenClaw rollback injection passes on Windows |
| Trained-agent demonstration | Gate E pass, bounded | Preregistered v0.2: 128 trained + 128 shuffled episodes; 64 held-out scenarios x3; trained 1.0 vs before 0.414455 and concurrent base 0.433951; fresh restored 1.0; 0 action/offer/leak mismatches across 192 paired records |
| Public hero | Public download-to-use pass | Seven public layers; fresh-restored score 1.0 vs 0.481521 fresh control; public-download restore returns `counter 260`; identical Windows/WSL verify, inspect, and P1 restore reports |
| Registry | Pass | six private evidence records plus one public-safe hero candidate; source harness, lineage, privacy, portability, and evidence digests validated locally |

Release verdict: **v0.1.0-alpha.2 PUBLISHED AND PUBLIC-DOWNLOAD VERIFIED.**

Current epistemic state: `PUBLIC_PREVIEW_PUBLISHED:v0.1.0-alpha.2`.

The legacy EVC surface is maintained only as a knowledge capsule because the
local skill has been demoted. It has no implementation or lifecycle authority.

Only the independently selected content kernel was requalified from the
bootstrap. Fixture-bound service/CLI code remains non-authoritative. Hermes P1
was built behind the adapter boundary and formalized from real gate evidence.

## Highest failure risks

1. Mistaking a rigorous transport protocol for the product itself.
2. Adapter-specific files leaking into the core schema.
3. Fixture success being described as real harness support.
4. Secrets or private state entering a public image.
5. Silent loss during export, restore, or migration.
6. Self-referential or non-deterministic archive digests.

## Next actions

Keep the published tag and six assets fixed. Continue development through new
commits and versions, preserving the working download-to-use path and keeping
new capability claims tied to observed results. The next design iteration does
not replace or invalidate this usable alpha release.

## Source provenance

The bootstrap requirements came from `agent_image_v01_codex_docs.zip`, supplied
on 2026-08-24, SHA-256:

`17807012fe74fd040f9c46e55d51540cf9c2c689d6a7af5300dffd1514ff5933`

The inherited context came from `agent_image_v01_codex_context_pack.zip`,
supplied on 2026-08-24, SHA-256:

`0dcd610bb9759832d406026c99406c33899fdf75add86ec8cd6563677a66749a`
