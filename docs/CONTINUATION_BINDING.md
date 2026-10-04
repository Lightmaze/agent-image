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

This branch is integration-only. Source tests and fresh wheel/sdist installed
package smoke must pass before any version bump or public release. The published
v0.1.0-alpha.2 tag and assets remain immutable.
