# vHarness pinned adapter contract

The v0.1 adapter is pinned to the local vHarness `0.1.0-alpha.1` source and
runtime build, Node `24.15.0`, and the vHarness-owned pnpm `11.7.0` lock. The
Agent Image repository does not translate vHarness contracts into Core fields.

The supported P1 producer/consumer scope is a stopped
`agent-image.reference-persistent` process-Guest instance containing:

- `vhd-config.json`: a schema-valid `HarnessSetContract`,
  `RuntimeRealization`, and relative driver paths;
- `guest-state.json`: explicit persistent Agent state items with semantic
  classes, transfer types, privacy, and values;
- `reference-guest.mjs`: the non-mock persistent process Guest implementation.

`host-truth.ndjson`, `kernel-state.json`, locks, authority grants, and
`host-api.token` are never exported. A source with Host state or any unexpected
file fails closed. `credentialRef` must be exactly `none`.

Restore creates a new target directory and a fresh vhd authority domain. The
restored Guest performs a live `wake → audit → wake` transaction through the
pinned vhd and vh binaries. The Host must record:

- complete typed loss reports;
- no authority escalation;
- fresh `vhd:*` authority grants rather than imported grants;
- the source Agent Image digest in process-Guest evidence;
- the same persistent Agent-state item digest after the round-trip.

The current reference Guest has ambient OS access, so vhd correctly reports
`security_boundary: false`. P1 here means native state restoration through a
real Host/Guest path; it does not claim strong sandbox isolation, a model-backed
Guest, DSH integration, or P3 behavioral portability.
