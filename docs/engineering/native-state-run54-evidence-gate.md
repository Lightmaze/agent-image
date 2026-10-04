# Native State Run 54 Checkpoint — Evidence Promotion Gate

Status: design/engineering checkpoint on isolated branch; no production-code merge.

## What changed

Run 51–53 produced four separate structured-native building blocks:

1. safe native capsule reader;
2. MAGE profile semantic validator;
3. fresh filesystem staging restore;
4. PreparedNativeRestore exact-subject ownership contract.

Run 54 adds the missing generic promotion rule that decides when those facts are sufficient to claim same-backend P1.

Candidate sidecar schema:

```text
agent-image-native-restore-evidence/v0.1
```

Evidence ladder:

```text
archive-verified
profile-valid
filesystem-staged
runtime-loaded
p1-native-restore
continuable
```

## Key decisions

- Adapters do not self-report P1. A shared evaluator derives the verdict from exact subjects and evidence facts.
- Capture witness levels are: none < self-attested < process-observed < external.
- P1 requires at least process-observed capture evidence bound to the exact native capsule subject.
- P1 requires runtime load, native validation, active receiver target, receiver authority rebind, all profile-required native operations, and a complete loss report.
- Exact retrieval replay and behavioral retention remain orthogonal claims.
- Continuable is stronger than P1: write + flush/freeze + reload + changed successor native subject.
- A continuable receipt may be committed as opaque Structural Continuation transition evidence, but is not causal-development proof.

## MAGE reference profile

Candidate MAGE requirement:

```text
required_operations_for_p1 = [query]
minimum capture witness = process-observed
```

MAGE is still below P1 because:

- the full pinned MageMemory package clean load/query/write gate has not run;
- current capture-barrier evidence is metadata/profile evidence, not yet process-observed.

## Executed local evidence

The candidate generic evaluator and schema were executed locally:

```text
23 tests passed
schema validation passed
```

Negative cases include self-attested capture, wrong capsule/Image subjects, inactive runtime, source authority reuse, missing required query, incomplete loss report, and invalid read-only non-mutation claims.

## Repository runtime-probe status

A test-only pinned MAGE runtime probe was prepared for the existing Linux/Python 3.12 CI cell. The connector safety layer blocked creation of the executable test file. No CI/runtime result or production-code commit is claimed from that attempt.
