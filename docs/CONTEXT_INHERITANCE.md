# Context Inheritance Record

- Date: 2026-08-24
- Source: `docs/source/context-pack/00_CONTEXT_FOR_CODEX.md`
- Source SHA-256: `8fc68b643d2fbe9f3e18e81d1245dca4b866db21e5c978ed6460930b925ff202`
- Authority: epistemic and interpretive; not a fourth specification

## Authority order

When sources conflict, use:

```text
latest explicit user instruction
> acceptance criteria
> engineering design
> requirements/PRD
> historical descriptions in the context handoff
```

The context handoff governs concept meanings, rejected shortcuts, value order,
and what to protect when the normative documents leave ambiguity.

## Inherited commitments

1. Agent state is broader than model weights, prompts, and tool lists.
2. Contextual/runtime and situated training are legitimate working hypotheses;
   weight updates are not the only possible training medium.
3. Prompt, rich context, and practice history are distinct objects.
4. Summaries are derived views and do not automatically replace raw experience,
   causal/temporal structure, replay material, or provenance.
5. Harness Image describes execution embodiment; Agent Image describes a
   developed agent artifact; Pulse Image is a possible persistent-context form.
6. vHarness remains an independent virtualization/hypervisor layer and a
   first-class adapter target, not the protocol owner or a DSH plugin.
7. Explorable World and Training Ground are distinct Habitat categories and must
   not be reunified into a vague environment abstraction.
8. `skills/` artifacts are not equivalent to acquired skill state.
9. A trained-agent claim requires the same model, practice, freeze, fresh restore,
   the same evaluation, and retained behavior—not merely successful unpacking.
10. Protocol timestamp, portable proof, cross-harness adapters, and the minimal
    registry outrank platform breadth during the current strategic window.

## Design-order correction — 2026-08-25

The latest project correction is not another schema requirement. It changes the
order in which we discover what deserves to become architecture.

- Local correctness, defensibility, completeness, and governance can all be
  excellent while the whole product remains unconvincing.
- Strong intuitions must first be allowed to become a felt experience. Only
  then should successful moments be translated into primitives, interfaces,
  and policy.
- Existing artifacts create gravity. Working code may be demoted to substrate
  or prototype when it begins to define the product instead of serving it.
- Protocol proof and adoption proof are different. Gate E shows that measured
  developed state can survive freeze/restore; it does not yet give an external
  developer a downloadable artifact and a short reproducible hero path.
- The current protocol repository is therefore treated as a rigorous transport
  and audit substrate. The next discovery surface is Agent Image's own public
  install / inspect / restore / compare experience. Protocol changes should be
  justified by evidence from that path.

The governing sentence is:

> First make the thing become itself; then make it a rigorous software system.

## Bootstrap drift audit

| Risk from handoff | Current finding | Verdict |
|---|---|---|
| Profile tarball disguised as a protocol | Explicit inventory, logical layers, item digests, privacy, and reports exist | No current drift |
| vHarness schema governing Core | Core imports no vHarness module and contains no production harness vocabulary | No current drift |
| DSH plugin graph generalized into Core | No DSH schema or plugin abstraction exists in Core | No current drift |
| Silent loss | Operation reports reconcile every fixture item to an acceptance-defined outcome | Guard present; real adapters untested |
| Private sessions/user memory published | Private items are removed by public policy; secrets fail closed | Guard present; universal DLP not claimed |
| Summary replaces original experience | Protocol permits experience/evidence payloads and references | Semantics present; positive raw-experience fixture absent |
| Fixture success becomes capability claim | Fixture adapter is machine-marked `accepted_test_only`; restore/migrate fail explicitly | No current false claim |
| CLI success becomes behavioral portability claim | README and status explicitly deny P1/P2/P3 and trained-agent proof | No current false claim |
| Developed state collapses into `skills/` | Schema separates skills, memory, experience, development, evaluation, and lineage | Structure present; developed-state round trip unproven |

## Conflict resolutions

- The context handoff uses `lost` in its typed-crossing explanation. The current
  acceptance document defines operation outcomes as `preserved`, `transformed`,
  `redacted`, `unsupported`, and `dropped_by_user`. Core keeps the acceptance
  vocabulary. Irrecoverable semantic loss belongs in the future adapter loss
  report; it is not silently renamed into an inventory outcome.
- Contextual Skill Attractor remains a research hypothesis and is not encoded as
  a manifest concept.
- Habitat, vHabitat, Team Image, Reprise, sleep, and consolidation remain design
  horizon options, not v0.1 implementation blockers.
- Strategic urgency accelerates a publishable protocol timestamp; it does not
  authorize unverified adapter or behavior claims.

## Explicit unknowns after inheritance

- Which Hermes state is necessary and sufficient for a real P1 developed-agent
  restore against a pinned official version.
- Whether the current logical model can represent raw and referenced experience
  without adapter-specific leakage in a real fifth adapter.
- Which persistent/contextual state is causally responsible for retained behavior
  after same-model fresh restore.
- Whether skill-preserving, privacy-stripping export is possible beyond the v0.1
  file/layer policy.

These unknowns define future acceptance probes. They are not negative product
decisions.

## Epistemic transition

The validated bootstrap remains in context `agent-image-v0.1` as a non-authority
probe with a sealed belief capsule. The re-anchored formal horizon lives in the
new context `agent-image-v0.1-formal`; it may inherit bootstrap and vHarness
knowledge through epistemic links, but neither source tree is an implementation
ancestor of the formal root.
