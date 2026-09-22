# DSH no-op refreeze — producer provenance vs native state

Date: 2026-09-22

Status: **PASS as a diagnostic boundary test; NOT continuation-ready.**

This experiment applies the continuation-ready adapter profile to the third existing P1 backend without introducing a new portability level or protocol schema.

## Contract

The run used the canonical Agent Image DSH adapter against:

- `@deepseek-ai/dsh@0.1.0-rc.6`
- Node `24.15.0`
- npm `11.12.1`
- hosted Windows
- isolated `DSH_HOME`

No model/provider call and no intended profile mutation occurred after restore.

GitHub Actions run: `35759470300`

Job: `real-dsh-noop-refreeze`

## Experiment

```text
shipped headless profile
→ build parent Agent Image
→ fresh P1 restore as continued
→ immediate refreeze with no intended state mutation
→ compare parent/no-op child
→ inspect native tar member delta
```

The parent restore validated as P1.

## Observed result

The receiver profile state was unchanged, but the generic state projection reported:

```text
state_changed:
  dsh-native-profile
```

The native member inventory was identical. Exactly one native member changed:

```text
meta/profile.json
```

Observed metadata:

```json
parent: {
  "source_name": "headless",
  "bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-headless"],
  "dependencies": {}
}

child: {
  "source_name": "continued",
  "bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-headless"],
  "dependencies": {}
}
```

Metadata digests:

```text
parent sha256:b60a9e126464385b0d2cc26b2a11d5570533021d6203bf3cb0a3de0dddee3203
child  sha256:5eb06737764a90b4006e02a62d3e61d35b18b23d3f0187680e410e03077450b8
```

After removing `source_name`, the metadata objects were equal.

The job therefore reported:

```text
producer_identity_inside_native_bytes = true
receiver_state_changed = false
current_raw_native_digest_truthful_for_noop = false
```

## Interpretation

The current DSH native capsule contains three semantic classes:

1. `profile/*` — receiver-materialized profile state;
2. `meta/profile.json.{bundles,dependencies}` and `meta/dump-config.yml` — restore-validation witness;
3. `meta/profile.json.source_name` — capture/producer provenance.

`native_restore()` writes only `profile/*`. It uses bundle/dependency metadata and the expected dump to validate the restored composition, but it does not materialize or validate `source_name` as target state.

Therefore:

```text
raw native capsule digest
!=
truthful no-op continuation-state commitment
```

for the current writer.

This is a third implementation shape supporting the same higher-level boundary previously exposed through Hermes coordination files and the pre-normalization OpenClaw producer envelope: bytes captured near a runtime are not automatically developed Agent state.

## Design consequence

The smallest v0.1-compatible correction is adapter-local:

```text
new meta/profile.json = {bundles, dependencies}
```

while the legacy reader continues accepting old metadata that also contains `source_name`.

The restore witnesses should remain integrity-bound in the native layer for now. Moving them into ordinary v0.1 manifest extensions merely to make the native layer state-pure would weaken the current binding because released v0.1 Image identity is still the layer payload-root.

This refines the native boundary to:

```text
receiver-materialized state
restore-validation witness
capture / producer provenance
```

Capture provenance must not perturb no-op continuation state delta. Restore witness may remain co-committed in v0.1 when it is deterministic for the pinned P1 contract and there is no separate committed witness channel.

## Claim boundary

This result revalidates pinned DSH P1 and establishes a no-op state-boundary defect in the current native writer.

It does **not** establish:

- DSH positive continuation;
- causal developmental lineage;
- learning;
- behavioral retention;
- P3;
- cross-version compatibility;
- authority transfer.

`continuation_ready` remains false until producer provenance is normalized and a real profile-state mutation survives independent child restore and exact continuation binding.

## Next acceptance

Tracked in issue #12:

1. remove `source_name` from new writer metadata while preserving legacy read compatibility;
2. require rename-only no-op refreeze to produce `state_changed == []`;
3. perform a semantically valid profile-owned `cordis.patch.yml` mutation observable through `--dump-config`;
4. delete the live continuation profile before child restore;
5. verify inherited + post-restore state and the existing Continuation Evidence Binding.
