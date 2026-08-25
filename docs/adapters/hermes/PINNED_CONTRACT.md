# Hermes Adapter Pinned Contract

## Pin

- Repository: <https://github.com/NousResearch/hermes-agent>
- Release: `v0.20.5`
- Tag: `v2026.8.19`
- Commit: `fcbd107`
- Profile implementation:
  <https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/hermes_cli/profiles.py>
- CLI reference:
  <https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/reference/profile-commands.md>

This pin is the first production compatibility target. Newer Hermes versions
must be probed and reported; they are not silently assumed compatible.

## Public contract used by the adapter

```text
hermes --version
hermes profile show <name>
hermes profile export <name> -o <archive.tar.gz>
hermes profile import <archive.tar.gz> --name <new-name>
```

Named profiles live below the Hermes profiles root and have their own config,
identity, memory, sessions, skills, cron, plugin, and runtime state. Import
refuses an existing target and refuses `default` as a target name.

The official exporter stages a copy, excludes `.env` and `auth.json`, scrubs
secret-shaped strings in text files, and leaves the source untouched. Its
coverage is not identical for all profiles:

- default profile export uses a root allow-list and intentionally excludes
  database/runtime infrastructure;
- named profile export excludes credential filenames but otherwise preserves
  the profile snapshot, including safe native state.

Therefore the adapter must not equate official export success with complete
Agent Image capture.

## Agent Image contract

1. Use the official Hermes export as the native snapshot boundary.
2. Inspect the snapshot in an isolated directory without following links.
3. Run Agent Image filename and structured-content secret checks again.
4. Map recognized identity, skills, memory, experience, and workspace files to
   harness-neutral layers.
5. Preserve the safe official snapshot as a typed Hermes native layer.
6. Reconcile source-visible items, snapshot items, included layers, exclusions,
   and unsupported state in the source report.
7. Restore through official `profile import` into a different, absent name.
8. Validate the target with `profile show` and invariant digests.
9. Hash the source before and after export/restore and fail if it changed.

## Claim boundary

A successful gate establishes Hermes P1 only for the pinned contract and the
tested platform. It does not establish cross-harness semantics or behavioral
portability.
