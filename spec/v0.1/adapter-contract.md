# Adapter Contract

Each production adapter has a stable id and independent version and implements:

```text
detect(locator) -> SourceCandidate[]
inspect_source(candidate) -> SourceInventory
export_plan(candidate, policy) -> ExportPlan
execute_export(plan, staging) -> ExportResult
native_restore_preflight(image, target) -> RestorePlan
execute_native_restore(plan) -> RestoreResult
semantic_import_preflight(image, target) -> MigrationPlan
execute_semantic_import(plan) -> MigrationResult
capabilities() -> AdapterCapabilities
```

Adapters do not pack archives, compute image digests, decide core privacy rules,
or mutate source state during detect/inspect. Every plan contains the complete
source inventory and one proposed outcome per item. Unsupported methods return a
typed error and capability `false`; they are never silent no-ops.

Restore and migration use a new staging target, validate it, and only then
activate it. Existing targets are rejected by default. Any failure cleans the
staging target or records it as quarantined; it must not leave an active partial
agent.

The bootstrap `dev.agentimage.fixture` adapter is test-only. It reads an explicit
inventory and provides no restore or migration evidence.

