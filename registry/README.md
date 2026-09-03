# Minimal Agent Image Registry

`v0.1/index.json` is a static, reviewable registry. It records artifact content
digests, source harness contracts, license assertions, privacy/distribution status, lineage,
portability claims, and digest-bound evidence.

The first six artifacts are private local evidence images, so their URIs use
the `withheld://` scheme. This is deliberate: a registry record must not turn a
private image into a public download. The seventh artifact is a public-safe
release asset and uses its immutable GitHub prerelease URL with distribution
`publishable`. The negative and positive private training images remain
available only as digest-bound historical evidence.

Validate the registry from the repository root:

```text
agent-image registry validate registry/v0.1/index.json --json
```

The validator fails on unknown fields, duplicate IDs/digests, unsafe evidence
paths, evidence digest drift, contradictory privacy/distribution metadata, and
portability levels that exceed their evidence status.
