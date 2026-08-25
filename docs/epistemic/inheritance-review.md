# Implementation Inheritance Review

## Active goal context

Bootstrap Open Agent Image Protocol v0.1 as an independent open artifact
protocol for developed agents.

## Declared horizon and current epoch

- Horizon goal: a harness-neutral protocol with four real adapters, native
  restores, one Hermes-to-OpenClaw migration, privacy safeguards, a trained-agent
  demonstration, and a registry.
- Epoch goal: Spec plus a safe, fixture-verified Core toolchain.
- Scope authority: the supplied PRD/engineering/acceptance packet and the user.

## Formal requirements

Harness-neutral logical layers, typed native escape hatch, deterministic and safe
container, explicit privacy, no silent loss, independent adapter contract, and
honest portability claims.

## Existing artifact

`../vHarness/` is a TypeScript alpha implementing portable cognitive regimes,
Host authority, state claims, loss reports, checkpoints, and OCI transport. Its
live DSH integration is explicitly absent; the current driver is replay/mock.

## Decisions independently justified against requirements

Agent Image needs its own manifest and lifecycle because it distributes developed
agent state across multiple harnesses. Adapter isolation, content digests, typed
native layers, and loss accounting follow from the Agent Image requirements, not
from the existence of vHarness.

## Demo-only shortcuts or historical accidents

The vHarness replay guest, alpha schemas, OCI transport choice, logical authority
evidence, and internal `HarnessImage` object are not production Agent Image
premises.

## Direction-preservation review

- Governing authority the old implementation loses: authority over Agent Image
  Core module boundaries, manifest fields, transport, and CLI UX.
- Design freedom the future regains: support heterogeneous harnesses, select a
  simple auditable v0.1 container, and evolve adapters independently.
- Commitments and options that remain open: all supplied v0.1 requirements,
  future OCI transport, all four adapters, registry, and trained-agent evidence.
- Scope reductions not decided: no horizon feature has been rejected by choosing
  a smaller bootstrap epoch.

## Counterfactual architecture test

Without the vHarness tree, the requirements still lead to an independent Core,
adapter boundary, explicit inventory, logical layers, safe container, digests,
privacy policy, and operation reports. vHarness is therefore evidence and a
future integration target, not an implementation ancestor.

## Decision

`DEMOTE`

## Evidence and gates required for the decision

The decision is supported by the supplied protocol requirements, vHarness
Charter/types/security documentation, and the explicit absence of live DSH
integration. Any vHarness component reused later must pass a fresh Agent Image
adapter gate.

