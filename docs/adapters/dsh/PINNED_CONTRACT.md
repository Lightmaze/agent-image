# DeepSeek Harness Adapter Pinned Contract

## Pin

- Package: `@deepseek-ai/dsh@0.1.0-rc.6`
- npm integrity:
  `sha512-brpZfED7ieRa2PQ5tUxMhHrM1pb2CmKFVM/f6yMULBDMicahk+Z2OsHgTwTDnoiZm23Ftu9rQz0NN4pflaoJcg==`
- Installed package `package.json` SHA-256:
  `3736cbf834f99298c644da821dbb08878223065bdf19242d6c64768ac9e97fe2`
- Installed package `README.md` SHA-256:
  `800b93592c9fe99f5af4e2cac9eacf56388792af07542a7934b7e2e1bd210b61`
- Official CLI documentation:
  <https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/README.md>
- Runtime used by Agent Image smoke: Node `24.15.0`, npm `11.12.1`

The npm artifact does not publish a `gitHead`, and the official GitHub link is
on mutable `master`. Compatibility authority therefore comes from the exact npm
version, integrity, and locally hashed shipped contract—not from an inferred
repository commit.

## Public contract used by the adapter

```text
dsh --version
dsh --profile <name> --dump-config
$DSH_HOME/profiles/<name>/package.json
$DSH_HOME/profiles/<name>/cordis.patch.yml
```

`package.json` owns `dsh.profile.bundles` as an ordered list and dependency
metadata. The tree composes over an empty root in bundle order, followed by the
profile patch, the home-level patch, and command-line overlays. The adapter uses
the official `--dump-config` result as the effective-composition audit surface.

## Agent Image boundary

The DSH adapter intentionally does not invent a universal plugin graph. It
stores one typed native composition containing:

- safe profile files, including `package.json`, `cordis.patch.yml`, generated
  `cordis.yml`, lock/workspace metadata, and unknown non-secret files;
- exact ordered bundle names and dependency metadata;
- the official composed configuration and its digest.

The media type is
`application/vnd.deepseek-harness.profile.v0.1.0-rc.6+tar+gzip`.

Profile `node_modules` directories and symlinks are not archived. Secret
filenames and structured secret fields fail closed. A restore that cannot
resolve the declared composition fails through the official `--dump-config`
command and rolls back the newly created target. The adapter does not claim to
reinstall arbitrary external packages in v0.1.

## P1 invariants

1. The target profile must be absent and remain below the exact DSH profiles
   root.
2. Profile files, bundle order, and dependency metadata must match the image.
3. The official target `--dump-config` output must byte-match the source audit
   snapshot.
4. Unresolved dependencies or version drift fail loudly.
5. Every source item and the native layer receive an explicit operation
   outcome.
6. The source profile is content-hashed before and after export.

## Claim boundary

The current gate establishes P1 for the shipped `headless` profile with in-box
bundles and empty external dependency metadata. Fail-loud unresolved dependency
behavior is covered by deterministic fault injection. Arbitrary third-party
plugin installation, session state, cross-platform DSH smoke, and P2/P3 are not
claimed.
