# Structural Continuation Binding — integration candidate

This integration branch exposes a file-only structural continuation surface
without changing the frozen Open Agent Image Protocol v0.1 manifest schema.

```text
agent-image continuation bind
agent-image continuation verify
```

The commands bind exact verified parent/child entry sets, a Core-derived
structural state delta, and opaque transition-evidence bytes. They deliberately
report `causal_transition_verified=false` and
`behavioral_retention_verified=false`.

The v0.1 `image.digest` remains the layer-payload root. Exact artifact identity
therefore also uses a verified-entry-set digest over the exact bytes validated
by Core. `load_image()` must validate and return one captured entry set rather
than verifying a pathname and reopening it.

State delta uses the shared layer-state projection
`kind/media_type/digest/size`; descriptor-only metadata changes remain
separate. Evidence stays opaque so later runtime-specific evidence formats do
not couple the structural primitive to one harness.

## Claim boundary

A successful verify reports both `valid=true` (kept for compatibility) and the
more precise `binding_valid=true`. These mean only that the supplied files and
recomputed delta match the binding. They do **not** mean that the evidence is
truthful, that parent and child are the same continuing subject, or that the
named direction is a real transition. The command therefore also reports:

```text
evidence_semantics_verified=false
continuation_relation_verified=false
causal_transition_verified=false
behavioral_retention_verified=false
```

This distinction is observable, not hypothetical: the structural primitive can
validly bind a redaction/derivation pair, a reversed pair, or unrelated valid
Images when the corresponding binding is built. A harness-specific verifier may
later validate evidence semantics and subject continuity, but this file-only
Core primitive must not imply either.

This branch is integration-only. Source tests and fresh wheel/sdist installed
package smoke must pass before any version bump or public release. The published
v0.1.0-alpha.2 tag and assets remain immutable.
