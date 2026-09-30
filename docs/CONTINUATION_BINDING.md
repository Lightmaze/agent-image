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


## Receiver-owned evidence verification (experimental)

The optional Python contract in `agent_image.evidence_verifier` separates a
second verification stage from structural binding. A receiver explicitly passes
a verifier selected by its local policy. The binding's `evidence_kind` remains
data: it is not a registry key, module name, entry point, or permission to load
code. Core performs no dynamic import or verifier discovery.

Only the already verified binding digest, exact parent/child Image and
verified-entry-set digests, state-delta digest, evidence metadata, and evidence
bytes are exposed to the verifier. Claims form a dependency ladder:

1. continuation, causal, and behavioral claims require verified evidence semantics;
2. causal and behavioral claims also require a verified continuation relation;
3. no evidence claim issues an ActivationBinding or transfers receiver authority.

The synthetic conformance tests include a byte-valid but semantically forged
receipt, which structural verification accepts and the receiver-selected
verifier rejects. They also reject prerequisite-skipping claims and demonstrate
that a malicious-looking evidence kind cannot select executable code.

This contract is not a vHarness capability claim. The tests use a synthetic
digest receipt; a pinned real vHarness restore/activation receipt and its native
enforcement path remain required before any causal, behavioral, or runtime
authority claim can be promoted.
