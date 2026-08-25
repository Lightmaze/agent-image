# Capability Matrix

Status after the 2026-08-25 Epoch 3 adapter-neutrality gates.

| Producer / consumer | Contract | Archive | Native restore | Semantic migration | Behavioral portability |
|---|---:|---:|---:|---:|---:|
| Hermes Agent 0.20.5 | C0 verified | P0 verified | P1 verified on Windows | Not verified | Gate E failed; not demonstrated |
| OpenClaw 2026.7.1-2 | C0 verified | P0 verified | P1 verified on Windows | P2 consumer verified from Hermes | Not verified |
| DSH 0.1.0-rc.6 | C0 verified | P0 verified | P1 verified on Windows for shipped headless profile | Not verified | Not verified |
| vHarness 0.1.0-alpha.1 | C0 verified | P0 verified | P1 verified on Windows for the reference persistent process-Guest | Not verified | Not verified |
| Clean-room JSON example 1 | C0 verified through entry point | P0 verified in fresh venv | Declared unsupported | Not verified | Not verified |

The matrix reports evidence, not intent. A fixture, schema mapping, installed
package, or planned adapter does not raise a portability level.

Pinned Hermes, OpenClaw, DSH, and scoped vHarness P1 plus
Hermes-to-OpenClaw P2 are backed by real CLI evidence in `docs/evidence/`. The
clean-room package independently proves a fifth adapter can register and build
without a Core fork. The first trained-agent experiment remains an
honest negative: persistent files survived fresh restore, but after-practice
behavior did not improve. A positive Gate E result remains a final v0.1 release
blocker.
