# Agent Image Protocol v0.1

Status: Draft for implementation

Identifier: `agent-image/v0.1`

## 1. Definition

An Agent Image is a portable, inspectable checkpoint of a developed agent. It
describes and may carry the agent's runtime references, identity, skills,
memory, experience, workspace artifacts, development provenance, evaluations,
lineage, and native harness state under explicit privacy and portability rules.

An Agent Image is not:

- a model checkpoint: model weights are referenced, not redefined;
- a prompt bundle: identity is only one layer;
- a skill pack: skills are only one layer;
- a profile archive: every payload is classified, hashed, and reported;
- a new agent framework: harnesses remain responsible for execution.

## 2. Conformance language

The terms MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative. A conforming
implementation MUST fail or warn according to the compatibility table; it MUST
NOT guess the meaning of an unsupported version or harness-native object.

## 3. Logical image model

An image consists of a manifest, zero or more declared payload layers, an index,
and operation reports. The logical layer kinds are:

| Kind | Meaning |
|---|---|
| `identity` | Role, persona, behavioral instructions, bootstrap surfaces |
| `skills` | Executable or descriptive skill resources |
| `memory` | Persistent semantic, episodic, user, procedural, or imported knowledge |
| `experience` | Sessions, transcripts, trajectories, episodes, and replay evidence |
| `workspace` | Explicitly selected work products, notes, plans, and artifacts |
| `development` | Structured evidence of how the agent reached this state |
| `evaluation` | Before/after or point-in-time evaluation evidence |
| `native` | Typed harness-specific state that Core cannot safely interpret |
| `other` | Extension content whose semantics are defined outside v0.1 |

Memory and experience are distinct: memory is a persistent representation formed
from experience; experience is the event or auditable trace itself. A native
layer is the protocol's required escape hatch. Honest opacity is preferred to
incorrect normalization.

The `skills` layer contains skill artifacts such as instructions, scripts, and
tool packages. Its presence does not prove acquired skill state. Acquired state
may be distributed across memory, experience, development evidence, runtime or
native state, and is only behaviorally supported by an evaluation that survives
fresh restore.

Experience summaries are derived views, not original history. A producer MAY
include summaries for runtime efficiency, but MUST NOT present them as raw
experience and SHOULD preserve or reference the causal/temporal source evidence
needed for later audit or replay.

Every layer descriptor MUST include an id, kind, media type, archive path,
SHA-256 digest, byte size, privacy class, and portability class. Layer ids and
paths MUST be unique.

## 4. Runtime and model references

The optional `runtime` object identifies the source harness, producing adapter,
and model reference. Model provider, family, id, and immutable digest are
optional observations. Missing facts MUST remain absent or explicitly unknown;
implementations MUST NOT infer a model digest from its display name.

Runtime credentials, access tokens, API keys, and authority grants are never
portable runtime metadata.

## 5. Development provenance

`development` is a first-class object rather than README prose. It may identify
method (`habitat`, `self_play`, `human_coaching`, `rl`, `sft`, `mixed`, or
`unknown`), start/end times, duration, episode count, habitat reference, notes,
and evidence descriptors. Claims SHOULD point to hashed or externally addressable
evidence.

## 6. Evaluation

Evaluation records MUST distinguish `self_reported`, `reproduced`, and
`third_party` evidence status. A consumer MUST NOT render a self-reported score
as certification. Before/after comparisons are claims until their referenced
evidence is verified.

## 7. Lineage

`lineage` may name base and parent images by URI and digest and may record a fork
reason. v0.1 supports directed parentage but does not define merge semantics.
Image lineage never imports runtime authority.

## 8. Privacy

Each item has one privacy class:

- `public`: eligible for a public image;
- `private`: retained only by an explicit private policy;
- `secret`: forbidden from all v0.1 images;
- `unknown`: treated as private and blocks public inclusion by default.

Sessions and user/profile memory default to private. Unknown data defaults to
private. Filename deny rules and structured key scanning are minimum controls,
not universal DLP. See [privacy.md](privacy.md).

## 9. Portability

Images and adapter capabilities use four levels:

- P0 Archive: inspect and verify only.
- P1 Native Restore: source harness A → image → new target in harness A.
- P2 Semantic Migration: selected portable layers from A → B with a loss report.
- P3 Behavioral Portability: post-migration behavior passes a declared benchmark.

P3 is not a v0.1 release blocker. Details are in
[portability.md](portability.md).

## 10. Container

The v0.1 reference container is deterministic tar+gzip with extension `.aimg`:

```text
manifest.yaml
index.json
layers/<kind>/...
meta/checksums.txt
meta/source-report.json
meta/redaction-report.json       # when redacted
meta/migration-report.json       # when migrated
```

Archive paths use `/`, are relative, and MUST NOT contain empty, `.`, or `..`
segments, backslashes, drive prefixes, symlinks, devices, or duplicate entries.
All layer payloads MUST be declared; undeclared payloads are invalid. Restore
MUST validate into a staging directory before atomically activating a target.

The manifest `image.digest` is the SHA-256 of canonical JSON containing the
sorted layer descriptors (`path`, `digest`, `size`, and `media_type`). It is not
a hash of the compressed archive and therefore has no self-reference cycle.

## 11. Operations and reports

The reference CLI defines `build`, `inspect`, `verify`, `redact`, `diff`,
`restore`, and `migrate`. Build MUST reopen and verify its output. Redact MUST
produce a new image. Migration defaults to dry-run. Restore refuses an existing
target unless an explicit safe replacement policy exists.

Every source inventory item MUST finish as exactly one of:

`preserved`, `transformed`, `redacted`, `unsupported`, or `dropped_by_user`.

Reports MUST allow item-count reconciliation. Silent loss is non-conforming.

## 12. Adapter boundary

Core owns manifests, schema/version checks, paths, digests, archives, privacy
policy, generic diff, and operation-report invariants. Adapters own source
detection, source inventory, semantic mapping, native state, target preflight,
materialization, and target validation. Core MUST NOT import a production
harness package. See [adapter-contract.md](adapter-contract.md).

## 13. Version compatibility

| Loader | Image | Required behavior |
|---|---|---|
| v0.1 | `agent-image/v0.1` | Load and validate |
| v0.1 | unknown `agent-image/v0.x` | Fail unless an explicit compatibility rule is published |
| v0.1 | unknown major/family | Fail |

Adapter versions are independent of the spec version.

## 14. v0.1 non-goals

v0.1 does not require cross-harness byte or token equivalence, a new model format,
a hosted hub, a Habitat runtime, a preferred training method, universal DLP,
encryption, OCI transport, team images, delta images, merge semantics, or P3.

## 15. Conformance summary

A conforming producer emits schema-valid manifests, declares and hashes every
payload, rejects secret state, reports every inventory outcome, and verifies its
own output. A conforming consumer validates version, paths, entry types, digests,
privacy consistency, and target capability before materialization. Capability
claims MUST be backed by the named P0–P3 gate.

Successful packing, file restoration, or presence of a `skills` layer MUST NOT
be described as trained-agent portability. Such a claim requires an unchanged
model reference, recorded practice/development provenance, fresh restore, the
same evaluation, and retained behavior.
