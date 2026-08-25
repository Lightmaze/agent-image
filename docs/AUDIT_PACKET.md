# v0.1 Short Audit Packet

Date: 2026-08-24

This packet closes context inheritance and opens implementation. It is not a
fourth architecture document.

## A. Spec Consistency Report

`CONSISTENT`

The context pack changes how ambiguous requirements are interpreted; it does
not conflict with the PRD, engineering design, or acceptance criteria. The one
terminology difference (`lost` versus the acceptance-defined operation outcome
set) is resolved in `docs/CONTEXT_INHERITANCE.md` without changing the release
gate.

## B. Bootstrap Drift Report

| Drift | Status | Evidence | Required correction |
|---|---|---|---|
| profile-tarball | PASS | `spec/v0.1/layers.md`; `tests/test_manifest.py` | Keep semantic layers, provenance, privacy, lineage, native state, and reports mandatory. |
| vHarness-canonical | PASS | `docs/CONTEXT_INHERITANCE.md`; Core import scan | Keep every harness dependency behind an adapter. |
| fixture-only | RISK | `src/agent_image/adapters/fixture.py`; no Hermes executable was present | Complete a pinned real Hermes P1 smoke test before any P1 claim. |
| privacy | RISK | `tests/test_security.py`; real Hermes snapshot untested | Apply a second Agent Image secret/privacy pass after official export and fail closed. |
| silent-loss | RISK | fixture reports reconcile; no real adapter report yet | Reconcile source inventory, official snapshot, image layers, and restore outcomes. |

No current item is `FAIL`. The three `RISK` items all collapse into the same
next module: a real Hermes adapter with a real round-trip gate.

## C. Implementation Delta

| Current state | v0.1 acceptance | Missing | Next module |
|---|---|---|---|
| P0 fixture-verified archive | Hermes H1-H3 / P1 | real detect, export, native restore, target validation, loss report | `hermes-p1` |
| test-only adapter contract | C0 common contract | production capabilities, preflight, transactional target | `adapter-runtime` |
| CLI restore fails honestly | native restore command | adapter dispatch and Hermes target locator | `formal-cli` |
| no behavioral claim | Gate E | practice/evaluation/fresh-restore evidence | later `trained-agent-proof` epoch |

Implementation order from here is fixed for the current epoch:

```text
pinned Hermes contract
-> acceptance tests
-> Hermes export/restore implementation
-> real named-profile smoke test
-> evidence-backed P1 claim or explicit blocker
```
