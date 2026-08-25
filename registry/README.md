# Minimal Agent Image Registry

`v0.1/index.json` is a static, reviewable registry. It records artifact content
digests, source harness contracts, license assertions, privacy/distribution status, lineage,
portability claims, and digest-bound evidence.

The initial artifacts are private local evidence images, so their URIs use the
`withheld://` scheme. This is deliberate: a registry record must not turn a
private image into a public download. The trained-agent entry is retained with
`behavioral: negative`, not promoted into a success claim.

Validate the registry from the repository root:

```text
agent-image registry validate registry/v0.1/index.json --json
```

The validator fails on unknown fields, duplicate IDs/digests, unsafe evidence
paths, evidence digest drift, contradictory privacy/distribution metadata, and
portability levels that exceed their evidence status.
