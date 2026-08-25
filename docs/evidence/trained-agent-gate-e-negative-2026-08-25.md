# Trained-Agent Gate E — Honest Negative Evidence

## Verdict

Gate E **failed** in the preregistered Hermes negotiation experiment. This run
does not authorize a trained-agent or behavioral portability claim.

| Point | Composite score | Change from before |
|---|---:|---:|
| Before practice | 0.790960 | — |
| After 48 practice episodes | 0.743703 | -0.047257 |
| Fresh restore | 0.710293 | -0.080667 |

The preregistered success threshold required an after-practice improvement of
at least 0.15 and retention of at least 75% of that gain after fresh restore.
Because practice produced no gain, retention is 0 and the gate remains red.

## What was actually exercised

- Hermes Agent 0.20.5, DeepSeek provider, `deepseek-v4-flash`, reasoning off.
- 48 synthetic procurement practice episodes.
- 20 disjoint held-out scenarios, evaluated twice before, after, and after a
  fresh native restore.
- 168 real provider calls, 168 usage records, and no resampling.
- Estimated provider cost: USD 0.04021738.
- Model weights, model identifier, provider client, reasoning setting, and
  harness tool configuration were unchanged across the three evaluations.

The experiment was preregistered at commit
`e3d34e35ed3d0c9edb0efbc87a77e755dbe81b48`. Its score weights and thresholds
were not changed after the result became visible.

## Artifact and restore evidence

Both images pass `agent-image verify`:

| Artifact | Manifest digest | Layers |
|---|---|---:|
| `before.aimg` | `sha256:f6ec9824cd414db557a8d9a072c8fc5c63f733503ae11163f0023220d82a8876` | 3 |
| `trained.aimg` | `sha256:8e0bb5aba1202befc073a0bfcf02029a12033920155af05b5ad6c7602a553faf` | 4 |

The source and restored copies of `SOUL.md`, `memories/MEMORY.md`,
`sessions/training-ground.jsonl`, and `config.yaml` are byte-identical by
SHA-256. The trained image contains identity, memory, experience, and typed
native layers; all four are private.

This narrows the finding: the checked persistent files survived the P1 native
round-trip, but the practice state stored in them did not produce the required
behavioral improvement. File preservation is not behavioral proof.

## Explicit evidence loss

One restored-evaluation call returned malformed JSON. The provider call and
usage record completed, but the runner version active at that instant had not
yet persisted raw stdout before parsing. The missing raw response was not
reconstructed and the call was not resampled. It is recorded as an invalid
structured response and contributes a zero score.

The runner now writes raw stdout before parsing and has a regression test for
accounting completed orphan calls without resampling. This repair did not alter
the preregistered score weights or success thresholds.

## Interpretation boundary

This run shows that this particular curriculum and append-only memory strategy
did not create the target capability on this model. It does not show that
contextual training is impossible. Plausible unresolved factors include a high
baseline, stochastic provider output, context dilution from accumulated
episodes, curriculum quality, and missing replay or consolidation. Those are
hypotheses, not conclusions from this run.

The machine-readable evidence, raw-file digests, privacy scan, restore hashes,
and limitations are in
`docs/evidence/trained-agent-gate-e-negative-2026-08-25.json`. Raw synthetic
records and private images remain in the ignored local run directory rather
than being silently promoted into a release artifact.
