# Capability Matrix

Status at `v0.1.0-alpha.1`.

| Producer / consumer | Contract | Archive | Native restore | Semantic migration | Behavioral portability |
|---|---:|---:|---:|---:|---:|
| Hermes Agent 0.20.5 | C0 verified | P0 verified | P1 verified on Windows | Not verified | Not verified |
| OpenClaw | Not implemented | Not verified | Not verified | Not verified | Not verified |
| DeepSeek Harness | Reconnaissance only | Not verified | Not verified | Not verified | Not verified |
| vHarness 0.1.0-alpha.1 | Mapping only | Not verified | Not verified | Not verified | Not verified |

The matrix reports evidence, not intent. A fixture, schema mapping, installed
package, or planned adapter does not raise a portability level.

The only current capability claim is the pinned Hermes P1 path described in
`docs/evidence/hermes-p1-v0.20.5.md`. The trained-agent demonstration and
Hermes-to-OpenClaw P2 path remain release blockers.
