# Capability Matrix

Status after `v0.1.0-alpha.1` and the 2026-08-25 Gate E experiment.

| Producer / consumer | Contract | Archive | Native restore | Semantic migration | Behavioral portability |
|---|---:|---:|---:|---:|---:|
| Hermes Agent 0.20.5 | C0 verified | P0 verified | P1 verified on Windows | Not verified | Gate E failed; not demonstrated |
| OpenClaw | Not implemented | Not verified | Not verified | Not verified | Not verified |
| DeepSeek Harness | Reconnaissance only | Not verified | Not verified | Not verified | Not verified |
| vHarness 0.1.0-alpha.1 | Mapping only | Not verified | Not verified | Not verified | Not verified |

The matrix reports evidence, not intent. A fixture, schema mapping, installed
package, or planned adapter does not raise a portability level.

The only current capability claim is the pinned Hermes P1 path described in
`docs/evidence/hermes-p1-v0.20.5.md`. The first trained-agent experiment
produced an honest negative result: persistent files survived fresh restore,
but after-practice behavior did not improve. Hermes-to-OpenClaw P2 and a
positive Gate E result remain release blockers.
