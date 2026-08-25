# Situated Negotiation Gate E — Formal Positive Evidence

Date: 2026-08-25

Gate E **passed** in the preregistered
`agent-image-situated-negotiation-ground-v0.2` experiment. Under the pinned
Hermes 0.20.5 and `deepseek-v4-flash` contract, mission-specific state formed
through causal practice survived an Agent Image freeze and fresh P1 native
restore.

This is a bounded positive result. The seller world and principal data are
synthetic. It does not establish real-world procurement performance,
cross-harness P3 portability, or a general law of contextual training.

## Design

- The model, provider, reasoning mode, tools, and harness were unchanged across
  arms. Model weights were not changed.
- The trained and coherent-shuffled controls each owned 128 causal practice
  episodes in eight 16-episode blocks, with reflection and agent-authored block
  consolidation.
- Evaluation used 64 disjoint held-out scenarios, three repetitions, and five
  post arms in a globally seeded interleaving: concurrent base, handbook,
  trained, coherent shuffled, and fresh restored.
- The frozen preregistration is commit
  `bc25913011b7fc982592f6fccb5802f5367b5bd8`, digest
  `sha256:ccd9d9c7bf99a2e91ca2822e5c33360a885cb6e500db8a40015441151fa88da8`.
- A Windows transport amendment compacted the consolidation prompt after the
  first formal consolidation hit the command-line limit. It changed no sample,
  arm, seed, score, or threshold and was committed before resume as
  `0ec844ecca73c4e664e959cefdd68842c554773b`.

## Scores

| Arm | Score | Scenarios | Records | Reservation leaks |
|---|---:|---:|---:|---:|
| Before | 0.414455 | 64 | 192 | 0 |
| Concurrent base | 0.433951 | 64 | 192 | 0 |
| Handbook | 0.463964 | 64 | 192 | 0 |
| Trained | 1.000000 | 64 | 192 | 0 |
| Coherent shuffled | 0.672950 | 64 | 192 | 0 |
| Fresh restored | 1.000000 | 64 | 192 | 0 |

Observed effects:

- pre to trained: `+0.585545` (required `>= +0.15`);
- trained minus concurrent base: `+0.566049` (required `>= +0.15`);
- paired bootstrap 95% lower bound: `+0.520932` (required `>= +0.10`);
- trained minus handbook: `+0.536036` (required `>= +0.10`);
- trained minus coherent shuffled: `+0.327050` (required `>= +0.10`);
- concurrent base drift: `0.019496` (required `<= 0.05`);
- fresh-restore retention: `1.0` (required `>= 0.8`);
- restored score drop: `0.0` (required `<= 0.05`).

All nine preregistered checks passed.

## Artifact and restore evidence

The trained image verifies as `agent-image/v0.1` with seven private layers:
identity, memory, two experience layers, development, evaluation, and a typed
opaque Hermes native layer. Its manifest digest is
`sha256:4a2f4093da97af32aa224374afe5a4a1b2e5ce8370f1fdf5527d8c893b3f3165`;
its file SHA-256 is
`cc8f5a414975b14f6683e18f10dc2feec0ddbefdf9bd95639f35bbe55c786007`.

The source archive hash was unchanged by restore. Trained and restored memory,
128-episode practice history, and eight consolidations have identical digests.
Across all 192 paired held-out records, trained and fresh-restored action,
offer, and reservation-leak fields had zero mismatches. The restore report
honestly marks the two evidence-index layers unsupported by the native target;
it does not pretend they were imported into Hermes runtime state.

## Privacy and provenance

All image layers remain private and the artifact is withheld. The source
inventory reconciles 19 items: 17 preserved and `.env` plus `auth.json`
explicitly redacted. No `eval-NNN` held-out identifier appears in trained
memory, practice history, or consolidation history. Raw provider responses and
synthetic trajectories remain only under the ignored local evidence directory.

The run made 1,687 actual API calls for 1,680 planned model invocations; seven
provider retries were counted. Total usage was 4,281,964 tokens with an
estimated cost of USD 0.28428757, below all hard limits.

Machine-readable evidence and raw-ledger digests are in
`docs/evidence/situated-negotiation-gate-e-positive-2026-08-25.json`. The
earlier append-only 48-episode negative result remains preserved as valid
evidence for that exact design; it has not been erased or rewritten.
