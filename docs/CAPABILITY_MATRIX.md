# Capability Matrix

Status after the 2026-08-25 OpenClaw P1 and Hermes-to-OpenClaw P2 gates.

| Producer / consumer | Contract | Archive | Native restore | Semantic migration | Behavioral portability |
|---|---:|---:|---:|---:|---:|
| Hermes Agent 0.20.5 | C0 verified | P0 verified | P1 verified on Windows | Not verified | Gate E failed; not demonstrated |
| OpenClaw 2026.7.1-2 | C0 verified | P0 verified | P1 verified on Windows | P2 consumer verified from Hermes | Not verified |
| DeepSeek Harness | Reconnaissance only | Not verified | Not verified | Not verified | Not verified |
| vHarness 0.1.0-alpha.1 | Mapping only | Not verified | Not verified | Not verified | Not verified |

The matrix reports evidence, not intent. A fixture, schema mapping, installed
package, or planned adapter does not raise a portability level.

Pinned Hermes P1, OpenClaw P1, and Hermes-to-OpenClaw P2 are backed by real CLI
evidence in `docs/evidence/`. The first trained-agent experiment remains an
honest negative: persistent files survived fresh restore, but after-practice
behavior did not improve. A positive Gate E result remains a final v0.1 release
blocker.
