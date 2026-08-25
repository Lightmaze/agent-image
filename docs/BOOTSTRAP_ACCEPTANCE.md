# Bootstrap Acceptance Report

- Date: 2026-08-24
- Artifact version: `0.1.0-alpha.0`
- Verdict: **PASS bootstrap epoch / HOLD full v0.1.0**
- Epistemic state: `BUILD:core-bootstrap`

## Accepted scope

This epoch accepts the independent protocol root and a fixture-only Core
acceptance path. It does not accept production adapter, native restore, semantic
migration, trained-agent, registry, or release claims.

## Evidence

| Area | Result | Evidence |
|---|---|---|
| Manifest and version | Pass | Example validates; missing spec, illegal layer kind, and invalid date-time fail |
| Deterministic build | Pass | Identical inventory produces byte-identical `.aimg` files |
| Self-verification | Pass | Build reopens and verifies before atomic publication |
| Source safety | Pass | Fixture source hashes remain unchanged; existing output is not overwritten |
| Inspect privacy | Pass | Metadata summaries contain no private payload content |
| Redaction | Pass | New public image removes private layer, records outcome, and re-verifies |
| Diff | Pass | Equal content is empty; changed layers and privacy deltas are reported |
| Archive integrity | Pass | Missing, undeclared, and byte-tampered payloads fail |
| Path safety | Pass | Absolute paths, traversal, duplicate paths, and symlinks fail without extraction |
| Secret handling | Pass | Denied filename plus JSON/YAML secret keys fail closed |
| No silent loss | Pass | Build/redaction item counts reconcile with typed outcomes |
| Core firewall | Pass | Production harness names do not appear in Core modules |
| Mock governance | Pass | 5 accepted test-only markers; 0 issues; 0 production blockers |
| Encoding | Pass | UTF-8/mojibake scan passes, including archived Chinese source documents |
| Package | Pass | Python wheel builds without network or user-cache writes |
| Epistemic state | Pass | Design horizon registered; vHarness implementation authority demoted; invariants valid |

Automated test result: **22/22 passed**, with no failures, skips, or expected
failures.

## Reproduction

```powershell
cd agent-image
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python scripts/scan_mojibake.py .
python scripts/scan_mock_points.py --root . --fail-on-issues --fail-on-production-blockers
```

Core CLI smoke path:

```powershell
$env:PYTHONPATH = "src"
python -m agent_image.cli build --from fixture:tests/fixtures/minimal -o private.aimg --yes
python -m agent_image.cli inspect private.aimg
python -m agent_image.cli verify private.aimg
python -m agent_image.cli redact private.aimg --policy public -o public.aimg
python -m agent_image.cli diff private.aimg public.aimg
```

## Open gates

1. Select an open-source license.
2. Complete external review of the v0.1 schema and semantic boundary.
3. Pin an official Hermes contract and deliver a real P1 round trip.
4. Implement OpenClaw P1 and Hermes → OpenClaw P2 with loss reports.
5. Implement DSH and vHarness adapters against live, versioned evidence.
6. Run the trained-agent freeze/restore evaluation and build the registry.
