# Hermes Epoch Implementation Inheritance Review

## Active goal context

`agent-image-v0.1-formal`

## Declared horizon and current epoch

- Horizon goal: the complete v0.1 protocol, four adapters, three P1 paths, one
  Hermes-to-OpenClaw P2 path, trained-agent proof, and registry.
- Epoch goal: establish a real Hermes P1 round-trip against the pinned official
  contract without weakening evidence, privacy, or loss gates.
- Scope authority: the user, then acceptance, engineering, PRD, and context.

## Formal requirements

Harness-neutral Core; adapter-isolated harness behavior; deterministic safe
archives; explicit privacy and loss; source immutability; transactional restore;
real target recognition; claims bounded by evidence.

## Existing artifact

The bootstrap contains a tested content kernel (`canonical.py`, `paths.py`,
`container.py`, `manifest.py`, `scanner.py`) plus fixture-bound service and CLI
code.

## Decisions independently justified against requirements

Canonical serialization, SHA-256 content addressing, safe relative paths,
bounded regular-file archives, strict manifest validation, and fail-closed
secret classification follow directly from Gates A, B, and D. The same choices
would be made if the bootstrap did not exist.

## Demo-only shortcuts or historical accidents

The fixture inventory format, fixture adapter, fixture-only service dispatch,
and restore/migrate stubs are not formal implementation inputs.

## Direction-preservation review

- Old implementation loses authority over adapter runtime, production service,
  and CLI architecture.
- The formal root regains independent module and transaction boundaries.
- All adapters, P2, behavioral proof, Habitat, and registry directions remain
  open.
- No horizon reduction is decided by selecting Hermes as the current epoch.

## Counterfactual architecture test

The five content-kernel responsibilities are required independently by the
normative gates. Fixture-specific orchestration would not be selected.

## Decision

`REQUALIFY`

Only the five content-kernel files are candidates. Requalification requires the
existing Core/security suite plus new production archive and Hermes contract
gates. Service, CLI, and fixture code remain non-authoritative.
