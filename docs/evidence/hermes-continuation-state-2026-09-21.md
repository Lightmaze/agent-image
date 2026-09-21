# Hermes continuation-state round trip — 2026-09-21

Result: **PASS for the pinned same-Hermes persistent-state continuation claim** on hosted Windows and Ubuntu.

This evidence closes one narrow question from the R1–R20 reconciliation: can an
Agent Image be restored into a fresh Hermes runtime, undergo a real persistent
state update through Hermes itself, be frozen again, and then carry both inherited
and newly formed persistent state into another fresh runtime?

It does **not** establish learning, skill acquisition, behavioral retention,
causal developmental lineage, cross-harness portability, or cross-platform
byte-identical images.

## Pinned contract

- Agent Image branch under review: `web/continuation-binding-20260921`
- Hermes Agent: `0.20.5`
- Hermes source commit: `fcbd1076a93841fa88855acce810e342a5b78101`
- Existing Agent Image adapter: `org.agentimage.hermes` `0.1.0`
- Continuation + exact evidence-binding CI evidence:
  [35656310081](https://github.com/Lightmaze/agent-image/actions/runs/35656310081)

The experiment uses synthetic local state only and performs no model/provider API
call. The post-restore mutation is executed through pinned upstream
`tools.memory_tool.MemoryStore.add`, the persistent memory path used by Hermes'
memory tool, rather than by Agent Image directly editing `MEMORY.md`.

## Procedure

```text
synthetic Hermes parent profile
    -> production Agent Image build
    -> verify
    -> fresh Hermes native P1 restore as `continued`
    -> upstream MemoryStore.add(post-restore memory)
    -> production Agent Image child build
    -> verify + diff
    -> delete the live `continued` profile
    -> independent Hermes native P1 restore as `child-restored`
    -> verify inherited parent memory + post-restore memory
    -> bind exact verified parent + exact verified child + state delta + runtime observation
    -> round-trip binding JSON and verify all bindings again
```

The parent and child source profiles are also hashed immediately before and after
each build. The CI rejects any source mutation during the supposedly read-only
build interval.

## Observed result

Both `real-hermes-continuation (ubuntu-latest)` and
`real-hermes-continuation (windows-latest)` completed the continuation script
successfully. The complete PR run passed all 14 jobs: the nine Core OS/Python
matrix jobs, installed-package smoke, the two existing real-Hermes smoke jobs,
and the two real continuation jobs.

On Ubuntu, the parent layer-root Image digest was
`sha256:bfb488ca70bcb798b81aeb1042ee18dc81bc45ea10a80a076ec676b940903902`
and the corrected child digest was
`sha256:ca99831bc71e2d7af47a6abbb53654a693da908ee82005cc392636a881bf8de9`.
The child fresh restore validated as P1, retained the parent memory, and retained
the post-restore memory.

On Windows, the parent digest was
`sha256:9661c84d1300d726bc5c0d5f39a5027a8be6008e41c16cf5d5143560cac04102`
and the corrected child digest was
`sha256:d2f06980a7f9ae667035f6790e141d502cd0feafdd9d714641323df278cf27f6`.
The same inherited/new-memory checks and fresh child P1 validation passed.

The Windows and Ubuntu Image digests differ, so this result must not be rendered
as cross-platform byte equivalence.

## Runtime-coordination artifact discovered by the experiment

The first successful continuation run exposed an adapter classification error.
Pinned Hermes `MemoryStore.add` takes a file lock using a sibling lock path such
as `memories/MEMORY.md.lock`. The existing Agent Image Hermes adapter classified
all `memories/*` files as semantic `memory`, so the first child Image acquired an
extra layer whose id was `hermes-memory-0ed28635b105`; that id resolves to the
path `memories/MEMORY.md.lock` under the adapter's path-derived layer-id rule.
The same file also entered the normalized native snapshot.

That lock is synchronization state, not authored or developed Agent state. Its
presence therefore made a runtime implementation detail affect Image identity,
semantic diff, and restored native payload.

### Engineering correction

The Hermes adapter now excludes only the two coordination paths currently
justified by the pinned upstream memory implementation:

```text
memories/MEMORY.md.lock
memories/USER.md.lock
```

They remain in source inventory and source-profile hashing, so source custody and
read-only-build checks still see the real filesystem. During export they are:

- reported as `unsupported`, with an explicit runtime-coordination reason;
- excluded from portable semantic layers;
- excluded from the typed native profile snapshot;
- absent after fresh restore.

The implementation deliberately does **not** introduce a generic `*.lock`
exclusion: an arbitrary lock-named file in another state surface could be real
user or Agent data. The allowlist is tied to the exact pinned Hermes contract and
must be revisited when that contract changes.

A focused unit regression, `tests/test_hermes_runtime_coordination.py`, checks both
the operation report and the native tar payload. The real continuation CI also
asserts that the upstream lock file genuinely appears after `MemoryStore.add`, is
reported rather than carried by the child Image, and is absent from the fresh
child restore.

After the correction, `diff` reports no added layer from the lock file and both
parent and child contain seven layers in the continuation fixture.

## Diff classification correction

The same experiment exposed that the former `diff_images` surface compared full
layer descriptor dictionaries. That comparison is still useful as an artifact
descriptor diff, but it is too noisy to stand in for a developmental-state delta:
a byte-identical payload can appear changed merely because capture-instance
provenance such as `source.origin` moves from `hermes:source` to
`hermes:continued`.

The formal CLI diff now preserves the existing `layers.changed` list for
compatibility and adds a separately versioned state view:

```text
agent-image-layer-state-projection/v0.1
fields = kind, media_type, digest, size
```

For a layer id present in both Images, `state_changed` means that this projection
changed. `metadata_changed` means the complete layer descriptor changed while the
state projection stayed equal. The two lists are disjoint and their union equals
the legacy `changed` list. `added` and `removed` keep their existing identity
semantics. This is a report interpretation only: it does not redefine v0.1
`image.digest`, layer identity, archive bytes, or restore behavior.

The real Hermes parent -> continuation -> child experiment is now an executable
acceptance test for that distinction. On both Windows and Ubuntu the observed
classification was the same:

```text
state_changed:
  hermes-memory-d3f72f2c5b9b    # memories/MEMORY.md
  hermes-native-profile          # typed native profile contains the durable update

metadata_changed:
  hermes-experience-e7ba902847a4
  hermes-identity-bde0ac766bf0
  hermes-memory-2ddbb58fbbac     # unchanged USER memory
  hermes-skills-59dcdc7d5364
  hermes-workspace-d06347a55550

added: []
removed: []
```

This result gives future lineage work a cleaner empirical input: the experiment
can now say which carried state actually changed without mistaking a different
producer profile name for Agent development. It is still **not** an
authoritative-state commitment and does not prove that a particular development
process caused the delta.

## Continuation evidence binding

The next missing layer was not another lineage field. The experiment already had
a real parent, real child, truthful state delta, and runtime observation, but
those objects were not cryptographically bound to one another. A copied report
could therefore be displayed beside the wrong parent or child without the generic
Core detecting that mismatch.

The candidate branch now introduces an **external evidence object**, not a new
portable Image identity:

```text
agent-image-continuation-binding/v0.1
scope = artifact-delta-evidence-binding

parent:
  spec
  image_digest
  verified_entry_set:
    version = agent-image-verified-entry-set/v0.1
    digest
    entries

child:
  ...same exact-content binding...

state_delta:
  projection = agent-image-layer-state-projection/v0.1
  added
  removed
  state_changed
  digest

descriptor_metadata_changed

transition_evidence:
  kind
  media_type
  digest
  size
```

### Why the binding needs more than `image.digest`

The released v0.1 `image.digest` is intentionally the layer payload root. It does
not commit all manifest, provenance, index, or operation-report bytes. The new
`verified_entry_set` digest therefore hashes a sorted inventory of every archive
entry that Core has already validated, each represented as `{path, SHA-256,
size}`. It binds the **exact verified artifact content** without redefining the
released v0.1 image identity and without depending on physical tar/gzip byte
layout.

This distinction is tested explicitly: a second valid parent can have the same
v0.1 layer-root `image.digest` while differing in image/provenance metadata. Such
a parent receives a different verified-entry-set digest and cannot verify against
the original continuation binding.

### What verification recomputes

`verify_continuation_binding` reloads and verifies the supplied parent and child,
recomputes both exact-content subjects and the state delta from the actual
artifacts, hashes the supplied evidence bytes, and requires the complete binding
to equal this recomputed object. Negative tests cover:

- a wrong but valid parent with the same v0.1 layer-root digest;
- modified transition-evidence bytes;
- a forged state delta whose attacker also recomputed its internal delta digest;
- missing evidence bytes.

The real Hermes continuation CI also serializes the generated binding to JSON,
reads it back, verifies it against the parent and child Images plus the canonical
runtime-observation bytes, and requires the binding's `state_changed` set to
match the independently produced generic diff.

The PR-head run
[35656310081](https://github.com/Lightmaze/agent-image/actions/runs/35656310081)
completed successfully with all 14 jobs, including real Hermes continuation on
both hosted Windows and Ubuntu.

### Deliberate proof boundary

A valid binding proves **association and integrity**, not truth of the runtime
observation. Core treats transition evidence as opaque bytes and records its kind,
media type, digest, and size. The generic verifier therefore returns:

```text
causal_transition_verified = false
behavioral_retention_verified = false
```

This is intentional. A future harness-specific verifier, trusted attestation,
or controlled behavioral experiment may raise a stronger claim, but a hash that
correctly binds a report to two artifacts must not itself be rendered as causal
development proof.

The resulting evidence ladder is now explicit:

```text
declared parentage
    != observed state delta
    != exact artifact/delta/evidence binding
    != causal developmental transition proof
    != behavioral retention proof
```

Only the third level is added by this revision.

## Claim boundary

This experiment proves that the existing pinned Hermes adapter and Core can carry
a **real upstream persistent memory-state update** through a parent restore,
child refreeze, deletion of the live continuation source, and independent child
restore on the tested Windows and Ubuntu runners. It also proves, for this
fixture, that the formal CLI diff can separate the durable payload changes from
capture-provenance-only descriptor changes and that a continuation evidence
object can be bound to the exact verified parent, exact verified child, the
versioned state delta, and the observed runtime-evidence bytes.

It does not prove that the new memory was learned from experience, that behavior
changed or was retained, that the parent caused the child state, or that the
current v0.1 lineage fields cryptographically bind this transition. Those are
separate gates.
