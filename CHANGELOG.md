# Changelog

## Unreleased

## 0.1.0-rc.1 — 2026-08-26

- Prepared the first publishable developed-agent release asset,
  `procurement-negotiator-v1.aimg`, from an explicit synthetic-only whitelist;
  runtime caches, logs, databases, locks, and credentials are absent.
- Preregistered and ran a 48-call public-restore comparison on new held-out
  scenarios. The public-restored Agent scored `1.000000` versus `0.481521` for
  the same-model fresh control, with zero reservation-price leaks and exact
  restored-state layer digests.
- Replaced the planned live private-parent arm before any provider call: model
  credits do not authorize sending private Agent state to an external provider.
- Added the operator-first hero path, publishable Registry record, and local
  `v0.1.0-rc.1` release bundle.
- Added a strict static Registry schema, five private/withheld initial records,
  digest-bound evidence validation, and `agent-image registry validate`.
- Added full per-layer privacy metadata to `inspect` without exposing payloads.
- Hardened structured-secret scanning for JSON, YAML, JSONL, and TOML; malformed
  declared structured content now fails closed with `E_SECRET_SCAN_FAILED`.
- Added Windows/UNC/POSIX path-form tests, private-payload diff coverage, and
  unknown-privacy public-redaction coverage.
- Verified Hermes P1 on Windows and local WSL Linux with equal paths, sizes, and
  layer digests after eliminating CRLF/LF fixture drift.
- Added a real pinned OpenClaw Windows post-create failure injection that proves
  official host registration and adapter workspace rollback.
- Expanded the installed-package gate to install both wheel and sdist in fresh
  environments and exercise inspect, verify, redact, diff, and Registry flows.
- Pinned hosted Hermes CI source checkout to a full upstream commit.

- Added the vHarness adapter pinned to local `0.1.0-alpha.1`, Node `24.15.0`,
  pnpm `11.7.0`, source-tree digest, runtime-build digest, and lockfile digest.
- Verified vHarness P1 through a fresh vhd authority domain and a live non-mock
  persistent process-Guest; Host authority is regenerated, source provenance
  is journaled, and four Agent-state items survive a typed round-trip.
- Added public `agent_image.adapters` entry-point discovery with collision and
  contract validation.
- Built and installed a separate clean-room fifth-adapter wheel in a fresh
  offline venv; it registered and produced a verified P0 image without changing
  Core.

- Added the production DSH adapter pinned to `@deepseek-ai/dsh@0.1.0-rc.6`.
  It preserves ordered bundles, dependency metadata, profile patches, unknown
  safe profile files, and official `--dump-config` output in typed native
  state without inventing a universal plugin graph.
- Verified a real Windows DSH P1 round-trip for the shipped headless profile;
  unresolved dependencies fail loudly and roll back under fault injection.
- Extended secret filename handling to reject hidden `.credentials.*` files.
- Added the production OpenClaw adapter pinned to `2026.7.1-2`, including
  detection, complete inventory, privacy-safe export, typed native restore,
  target recognition, explicit Node execution on Windows, and fail-loud
  rollback verification.
- Verified a real OpenClaw P1 round-trip on Windows with 15 source items and 12
  image layers fully reconciled.
- Implemented dry-run-first Hermes-to-OpenClaw migration and verified the first
  P2 path: identity, two selected memories, and one skill migrated; `.env` was
  redacted; `state.db`, sessions, and unmapped state remained explicit loss.
- Added typed public adapter SDK records, `adapters list --json`, and generic
  `--report` output for CLI operations.
- Recorded the Node plan drift: pinned OpenClaw requires Node `24.15.0` or
  later in the Node 24 line, so `24.13.0` is not a valid contract runtime.
- Preregistered and ran the 168-call same-model Hermes negotiation Training
  Ground against a real provider.
- Recorded an honest negative Gate E result: after-practice and fresh-restore
  scores were below the before-practice baseline, so behavioral portability is
  not demonstrated.
- Verified the before and trained images and byte equality for four restored
  persistent-state surfaces.
- Added cost limits, resumable checkpoints, raw-response-before-parse capture,
  and zero-score accounting for invalid structured output without resampling.

## 0.1.0-alpha.1 — 2026-08-24

- Established an independent repository boundary under Apache-2.0.
- Added a locked Python development environment, cross-platform CI, wheel and
  source distribution builds, and a fresh-venv installed CLI smoke test.
- Added an evidence-only capability matrix and alpha release verdict.
- Added a production Hermes adapter pinned to Hermes Agent 0.20.5 / tag
  v2026.8.19 / commit fcbd107.
- Added official profile export/import, typed native preservation, semantic
  layer mapping, source immutability checks, transactional target validation,
  and complete build/restore reports.
- Verified a real Windows named-profile P1 round-trip; no P2 or P3 claim.
- Made experience and workspace inclusion apply to the opaque native snapshot,
  not only to logical layers.

## 0.1.0-alpha.0 — 2026-08-24

- Bootstrapped the harness-neutral v0.1 spec and schema.
- Added a fixture-only executable Core acceptance path.
- Recorded vHarness reconnaissance without claiming adapter support.
