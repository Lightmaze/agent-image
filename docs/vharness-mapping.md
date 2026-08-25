# vHarness → Agent Image mapping (reconnaissance)

This mapping is based on the current local vHarness alpha source, not on historic
names in the Agent Image requirements. It describes candidate adapter behavior;
no vHarness adapter is implemented yet.

| vHarness object/evidence | Agent Image layer | Export | Restore | Privacy | Notes |
|---|---|---:|---:|---|---|
| `VhdConfig.harnessSet` / `HarnessSetContract` | `runtime` + typed `native` | Candidate | Unproven | private by default | Portable regime policy is semantic metadata; exact contract stays native. |
| `RuntimeRealization` | `runtime` + typed `native` | Candidate | Unproven | private | Runtime family/version and model identity are portable metadata; extension `native` remains opaque. |
| `ModelArtifactIdentity` | `runtime.model` | Candidate | Metadata only | public/unknown | Unknown observations stay unknown; never infer a model digest. |
| `RuntimeBinding.credentialRef` | runtime metadata only | Reference may be named | Never resolve | secret boundary | The credential itself must not enter an image. |
| `PortableRegime.cognition.identitySurface` | `identity` policy metadata | Candidate | Logical only | private/unknown | It is a policy, not necessarily the agent's identity payload. |
| `contextView`, `sessionPolicy`, `TransferEnvelope.ContextTransfer` | `experience` / `native` | Driver-dependent | Unproven | private | vhd owns policies and references; actual sessions remain Guest-owned. |
| `memoryView`, `MemoryTransfer`, `ChronicleReferences`, `PlasticityDelta` | `memory` / `experience` | Driver-dependent | Unproven | private | vhd has no general semantic-memory store. Do not invent one. |
| `toolCausality`, environment and authority policies | `runtime` metadata | Candidate | Logical only | private | Policies do not prove tool/plugin process restoration. |
| Runtime plugins, workers, PTYs, caches, session handles | typed `native` | Guest-driver-dependent | Usually unsupported | private/unknown | vHarness loss spec forbids claiming restoration from metadata alone. |
| `StateClaim` | layer source/capture/privacy metadata | Candidate | Claim-specific | maps `internal`→private | `secret` requires `capture.mode=forbidden`. |
| `HarnessCheckpoint` | `native` + layer descriptors | Candidate | Unproven | claim-specific | Capture boundary and loss report are valuable; referenced payload availability must be verified. |
| `HarnessImage` | typed `native` compatibility layer | Candidate | Unproven | private | Existing format is not replaced and does not become Agent Image Core. |
| Local OCI layout | typed `native` or future transport | Candidate | Inert validation only | descriptor-derived | Loading must not start a Guest, mount a world, resolve credentials, or grant authority. |
| `host-truth.ndjson`, `kernel-state.json`, Host API tokens | excluded / referenced evidence | No default export | Never restore as authority | secret/private | Security spec says tokens and journals never enter images. |
| `ContinuityBinding` | `lineage`/development reference + native | Candidate | No identity adjudication | private | Carries delegated evidence; it does not prove identity continuity. |
| `LossReport` | operation/source report | Candidate | N/A | metadata | Six-class vHarness losses may be preserved as adapter-native details and summarized into Agent Image outcomes. |

## Current capability verdict

- Archive (P0): design candidate only; not implemented.
- Native restore (P1): blocked. The local source explicitly marks the replay
  driver mock/test-only and live DSH integration as `VH_DSH_NOT_INTEGRATED`.
- Semantic migration (P2): not implemented.
- Behavioral portability (P3): outside v0.1 release blocking scope.

## Required P1 invariants

Before claiming vHarness P1, a real adapter must preserve the Harness Set,
Runtime Realization, ordered state claims, checkpoint boundary, lineage and
complete loss report; it must never import authority grants or credentials, and
the restored target must validate through a live non-mock Guest path.

