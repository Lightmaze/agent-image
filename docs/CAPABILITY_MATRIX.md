# Capability Matrix

Status at the September 7, 2026 public `v0.1.0-alpha.2` release.

| Producer / consumer | Contract | Archive | Native restore | Semantic migration | Behavioral portability |
|---|---:|---:|---:|---:|---:|
| Hermes Agent 0.20.5 | C0 verified | P0 verified | P1 verified on Windows, hosted Ubuntu, and local WSL Linux | Not verified | Gate E verified for one synthetic same-harness mission; P3 not verified |
| OpenClaw 2026.7.1-2 | C0 verified | P0 verified | P1 verified on Windows | P2 consumer verified from Hermes | Not verified |
| DSH 0.1.0-rc.6 | C0 verified | P0 verified | P1 verified on Windows for shipped headless profile | Not verified | Not verified |
| vHarness 0.1.0-alpha.1 | C0 verified | P0 verified | P1 verified on Windows for the reference persistent process-Guest | Not verified | Not verified |
| Clean-room JSON example 1 | C0 verified through entry point | P0 verified in fresh venv | Declared unsupported | Not verified | Not verified |

The matrix reports evidence, not intent. A fixture, schema mapping, installed
package, or planned adapter does not raise a portability level.

Pinned Hermes, OpenClaw, DSH, and scoped vHarness P1 plus
Hermes-to-OpenClaw P2 are backed by real CLI evidence in `docs/evidence/`. The
clean-room package independently proves a fifth adapter can register and build
without a Core fork. The first 48-episode trained-agent probe remains an honest
negative for that exact append-only design. The preregistered v0.2 experiment
subsequently passed Gate E with concurrent-base, handbook, coherent-shuffled,
and fresh-restore controls. This permits a bounded same-Hermes mission-specific
state-retention claim, not P3 behavioral portability.

Core tests passed on hosted Windows, Ubuntu, and macOS with Python 3.11–3.13.
The real Hermes smoke passed on hosted Windows and Ubuntu. Anonymous release
downloads also passed fresh installation and real Hermes restore on Windows
and WSL Linux, with identical verify, inspect, and restore reports. See the
[publication evidence](evidence/publication-v0.1.0-alpha.2-2026-09-07.md) and
[12 passing release-tag CI jobs](https://github.com/Lightmaze/agent-image/actions/runs/34177445943).
