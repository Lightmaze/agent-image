# Situated Negotiation Training Ground v0.2

This experiment replaces, rather than extends, the v0.1 append-only probe. The
v0.1 negative result remains immutable evidence.

## Objective

Test whether one persistent Hermes Agent can learn a mission-specific seller
policy from causal practice, freeze the resulting runtime state, and retain the
behavior after a fresh native restore while the model, provider, reasoning,
tools, and evaluation prompts remain unchanged.

The world contains stable vendor cohort policies. A scenario exposes the cohort
code, market reference, seller ask, and principal authority, but not the
seller's minimum price. Each cohort uses a stable ratio to derive that minimum
from the observable market interval. The codes are deliberately semantically
neutral. New held-out scenarios use new products and amounts but the same
latent policies.

## Why v0.1 could not isolate the effect

The first probe had a high baseline, gave the model no observable basis for
recovering the hidden seller floor, rewarded some infeasible counters almost as
highly as explicit walk decisions, and appended 48 self-authored reflections
without independent coaching or consolidation. Before, after, and restored
evaluations also ran in separate time blocks with only two repetitions.

## Development intervention

The primary trained arm uses blocks of continuous Hermes session lineage:

```text
decision
-> deterministic seller response
-> revealed consequence + oracle counterfactual
-> agent reflection in the same session
-> repeat within block
-> agent-authored consolidation
-> concise persistent playbook
-> next block in a fresh session
```

Raw episodes, model responses, usage metadata, feedback, reflections, and every
consolidation remain private evidence. The active memory is concise and is
never replaced by an oracle-authored policy.

Every model invocation carries an explicit Hermes `--profile` selector. Before
any provider call, and again after development and native restore, the runner
uses the official offline `prompt-size --json` surface to prove that the named
profile's memory is active and that zero tools are exposed. Environment-only
`HERMES_PROFILE` selection is not accepted as evidence because Hermes 0.20.5
does not use that variable to rebind `HERMES_HOME` during CLI startup.

## Controls

- `before`: pre-practice base evaluation.
- `concurrent_base`: unchanged base evaluated interleaved with post arms.
- `handbook`: equal harness/model plus generic negotiation guidance, with no
  cohort-specific policy.
- `trained`: persistent causal practice plus reflection and consolidation.
- `shuffled`: identical development mechanism in a coherent but permuted
  seller-policy world; evaluation uses the true world.
- `restored`: fresh Hermes native restore from `trained.aimg`, evaluated without
  resuming a training session.

The shuffled arm tests whether correct action-consequence structure matters.
The concurrent base detects provider drift. The handbook controls for generic
instructions and additional memory text.

## Claim boundary

A positive result would demonstrate portable mission-specific developed state
for this pinned harness/model/world contract. It would not prove general
negotiation expertise, irreducibility to a handbook, P3 across harnesses, or a
real-world procurement capability.

## Pilot result and formal freeze

The first implementation pilot was invalidated by a real harness integration
failure: calls ran against the isolated root runtime rather than the named
profile, so all arms saw empty memory. That negative result is retained as
evidence of profile-selection drift.

After adding explicit profile selection and prompt-surface preflight, an
independent 16-episode/8-held-out-scenario pilot passed every numeric
sensitivity check: trained minus concurrent base `+0.5825`, paired 95% bootstrap
interval `[+0.494375, +0.670625]`, trained minus shuffled `+0.413838`, restore
retention `1.0`, zero restore drop, zero base drift, and zero reservation-price
leaks. Pilot data cannot authorize Gate E; it authorizes freezing this formal
design without changing its thresholds.
