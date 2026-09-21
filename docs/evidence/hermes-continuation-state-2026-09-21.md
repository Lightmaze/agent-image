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

- Agent Image branch under review: `web/hermes-continuation-state-20260921`
- Hermes Agent: `0.20.5`
- Hermes source commit: `fcbd1076a93841fa88855acce810e342a5b78101`
- Existing Agent Image adapter: `org.agentimage.hermes` `0.1.0`
- CI evidence run after the runtime-artifact correction:
  [35593576621](https://github.com/Lightmaze/agent-image/actions/runs/35593576621)

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
```

The parent and child source profiles are also hashed immediately before and after
each build. The CI rejects any source mutation during the supposedly read-only
build interval.

## Observed result

Both `real-hermes-continuation (ubuntu-latest)` and
`real-hermes-continuation (windows-latest)` completed the continuation script
successfully.

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

## Remaining diff limitation

The experiment also exposed a separate problem that is **not** fixed here:
`diff_images` compares complete layer descriptors. The same durable payload can
therefore be reported as changed when only instance/provenance metadata such as
`source.origin` changes from `hermes:source` to `hermes:continued`.

For developmental lineage work, the next diff surface should distinguish at
least:

1. payload/state change — digest, size, media type or semantic resource identity;
2. provenance/instance metadata change — source locator/origin or capture context.

This should be repaired before using today's `changed` layer list as an
authoritative developmental delta or designing a stronger lineage commitment on
top of it.

## Claim boundary

This experiment proves that the existing pinned Hermes adapter and Core can carry
a **real upstream persistent memory-state update** through a parent restore,
child refreeze, deletion of the live continuation source, and independent child
restore on the tested Windows and Ubuntu runners.

It does not prove that the new memory was learned from experience, that behavior
changed or was retained, that the parent caused the child state, or that the
current v0.1 lineage fields cryptographically bind this transition. Those are
separate gates.
