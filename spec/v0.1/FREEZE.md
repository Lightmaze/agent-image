# v0.1 alpha compatibility boundary

The `agent-image/v0.1` manifest and operation-report vocabulary entered an alpha
compatibility boundary after the four built-in adapter C0 gates and the
clean-room fifth-adapter gate passed on 2026-08-25.

Published alpha artifacts remain immutable and future implementations should
continue to inspect them or provide an explicit migration path. Before beta,
identity, object-graph, and lifecycle discoveries may still require breaking
schema changes. Such changes must be documented and versioned; they must not be
silently applied to an already published artifact.

This boundary does not assert that final release gates have passed. The current
alpha has positive bounded same-harness developed-state evidence, but complete
computational identity, strong vHarness isolation, and P3 remain outside its
claims. The Registry is outside the Core manifest schema.
