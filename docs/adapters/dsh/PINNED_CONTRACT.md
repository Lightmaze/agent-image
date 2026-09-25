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


## Runtime-resolution caveat

The exact top-level package is an identity anchor for the published CLI tarball,
but it is not a hermetic description of the receiver runtime. The published
`@deepseek-ai/dsh@0.1.0-rc.6` package declares many internal
`@deepseek-ai/dsh-*` dependencies with compatible semver ranges. A real
receiver-local installation captured during continuation work resolved most of
those internal packages to later release-candidate versions while
`dsh --version` still reported `0.1.0-rc.6`.

Strong P1/continuation evidence should therefore record a
`ResolutionWitness` for the concrete receiver dependency graph. The witness
is evidence context, not Agent identity and not a substitute for the top-level
package pin. Current production P1 still requires byte-equal
`--dump-config`; semantic witness comparison remains diagnostic only.



## Resolution witness is not a runtime-tree digest

The recorded package-lock is a resolver receipt. Even a canonical lockfile
digest is not automatically a byte-level fingerprint of the installed runtime:
the observed passing lock contains packages with install scripts, whose
post-install filesystem output can depend on the receiver environment.

For current continuation experiments, an exact known-good lockfile semantic
digest may be used as a **strict experimental gate** to control one variable.
It should be named a `ResolutionWitness`, not a universal
`ResolvedHarnessRuntimeClosure`.

If install-script or other realization effects become material to a strong
compatibility claim, add a receiver-local runtime-tree witness rather than
pretending the lockfile already proves installed bytes.

## Runtime realization receipt for continuation evidence

Continuation evidence needs a stronger context than the top-level package pin,
but that context must not be folded into Agent identity.

The candidate continuation lane records a runtime realization receipt with four
separate parts:

```text
RuntimeRequirement
AcquisitionProvenance
ResolutionWitness
MaterializationPolicy
```

For the current npm-based experiment:

- the requirement is DSH `0.1.0-rc.6` under the Node `24.15.0` test
  profile;
- the npm version is **acquisition provenance**, not an enforced DSH identity
  field;
- the package-lock package-identity projection is the strict experimental
  resolution gate;
- lifecycle scripts are recorded as enabled under npm's normal install policy;
- no runtime-tree digest is claimed.

The historical `DshPin.npm == 11.12.1` value therefore describes the tested
adapter environment. Production `DshAdapter._require_pin()` does not enforce
that npm version, so continuation evidence must record the **actual** receiver
npm value separately instead of writing the historical tested value as if it
were the observed runtime.

A strong continuation binding SHOULD include this realization receipt inside
the exact transition-evidence bytes. That binds the parent/child state delta to
the runtime that interpreted the state without making that runtime part of the
Agent's identity.

Current known-good experimental package-identity projection:

```text
sha256:5d3de0bfbc06aae899246d27f2f32ae68b88241f8c1b4472688785b50f202e22
```

This digest is an **acceptance fixture**, not a permanent protocol constant. A
different registry URL may change the whole lockfile receipt without changing
the package-identity projection. Conversely, version, integrity, link status,
or install-script metadata changes alter the projection.

The candidate lane must still run a same-runtime witness control before the
positive mutation:

```text
captured profile bytes
→ fresh control receiver
→ profile bytes equal
→ raw dump witness equal
→ semantic dump witness equal
→ production parent P1
→ positive mutation
```

If the control passes but production parent P1 fails under the same runtime
receipt, investigate the production restore path before adding a broader
runtime-tree commitment or relaxing P1 witness equality.


## P1 mismatch diagnostic contract

The production P1 decision remains raw byte equality for the official
`--dump-config` witness. However, once raw equality fails, the adapter should
retain enough non-evaluating evidence to distinguish the next engineering
branch without changing acceptance.

The already-real-runtime-tested DSH witness comparator can be used **only in the
failure details**:

```text
raw witness mismatch
→ P1 still FAILS
→ compare expected/actual witness non-evaluating
→ attach semantic digests + privacy-safe structural diff
→ rollback target as before
```

This diagnostic path MUST NOT:

- turn `semantic_equal == true` into a restore pass;
- execute `!!js` expressions;
- emit raw scalar values or full config bodies;
- suppress parser rejection;
- preserve a failed receiver profile merely for debugging.

A mismatch error should retain:

```text
raw_equal = false
expected_raw_digest
actual_raw_digest
parser_status
semantic_equal
expected_semantic_digest / actual_semantic_digest when parsed
privacy-safe structural diff
```

This is now preferable to returning only the two raw digests because real
continuation work has already produced receiver mismatches that were rolled back
before their structure could be inspected. The comparator has separately passed
synthetic fail-closed tests and real pinned DSH dump parsing, so using it as a
failure-only instrument no longer asks an unvalidated parser to define
acceptance semantics.

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
