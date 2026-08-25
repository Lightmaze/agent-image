# DSH P1 Gate Evidence

Verdict: **PASS for the pinned shipped headless profile on Windows**.

## Contract

- `@deepseek-ai/dsh@0.1.0-rc.6`
- Node `24.15.0`
- npm `11.12.1`
- isolated `DSH_HOME`

The npm artifact does not expose a `gitHead`; the exact npm integrity and
locally hashed shipped README/package/entry point define the reproducible pin.

## Round-trip

```text
official DSH headless profile initialization
-> ordered profile inventory
-> official --dump-config
-> typed native Agent Image
-> verify
-> new restored profile
-> official --dump-config
-> file, bundle-order, dependency, and composition reconciliation
```

The image contains one opaque DSH layer rather than a fabricated universal
plugin graph. Its seven operation items cover four profile files, two ordered
bundles, and the official composed-config snapshot. The target retained all
seven; the source and target dumps have the same SHA-256, and the source profile
digest remained unchanged.

The official shipped profile has empty external dependency metadata. Therefore
this gate proves in-box bundle resolution, not arbitrary dependency
reinstallation. Deterministic fault injection verifies that an unresolved
dependency raises `E_NATIVE_INCOMPATIBLE` and rolls back the new target. Secret
profile filenames fail with `E_SECRET_DETECTED`.

## Claim boundary

This is DSH P1 for one exact developer-preview package and Windows environment.
It does not claim session portability, external plugin reinstall, P2, P3, or
later-version compatibility.

The machine-readable record is `docs/evidence/dsh-p1-v0.1.0-rc.6.json`.
