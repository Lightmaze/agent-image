# Native State Run 68 — MAGE continuable realization migration

Status: engineering checkpoint; profile-specific candidate; not merged implementation evidence.

## Decision

Run 67's in-memory `reembed-all-derived-index` path is sufficient only for transient/read-only migration.
For writable continuation under pinned MAGE, source inline embeddings must not be allowed to coexist with
new target-realization embeddings after a successor write.

Pinned source establishes the cause:

- `HybridIndex.add_node()` / `add_hyperedge()` reuse non-null inline embeddings.
- `JsonlStore.upsert_node()` / `upsert_hyperedge()` serialize those embeddings into append-only JSONL.
- `MageMemory.__init__()` rebuilds indexes from stored nodes/hyperedges.
- Therefore an in-memory-only overlay can revert to a mixed source/target vector space on ordinary reload.

For a continuable semantic migration:

1. source Agent Image / source working directory remains immutable;
2. materialize a distinct target MAGE working directory;
3. re-embed every non-tombstone node/hyperedge JSONL log record under the target realization;
4. copy edges/events byte-for-byte;
5. prove source/target equality under a profile-owned authoritative projection that strips only the
   top-level `embedding` field from node/hyperedge records;
6. treat target as a lineage-bearing semantic-migration successor, not an exact restore.

## Candidate evidence

Local candidate helper: `mage_store_migration.py`.

Focused tests:
- Run 68 migration helper: 11/11 PASS
- Run 67 preflight regression: 11/11 PASS
- combined: 22/22 PASS
- py_compile: PASS

Exact pinned `mage_memory/indexing/vector_index.py` blob:
`36d9fb45d8e0571b9be9ef69d4eba63e5576a666`.

Fixed successor differential (source hash realization seed=7, target seed=11, dim=64):
- mixed persisted old/new vectors vs coherent target: top-1 agreement 0.0%, mean top-5 overlap 24.17%;
- fully materialized target: top-1 100%, mean top-5 overlap 100%, exact top-5 100%.

A separate store-materialization example confirmed source bytes unchanged, projection equality, byte-identical
edges/events, and complete target-dimension re-embedding.

## Boundary

This checkpoint does NOT prove full pinned MageMemory `load -> query -> write -> flush/freeze -> reload`.
MAGE P1 remains blocked on that package-level runtime gate and on real Agent Image adapter integration.
