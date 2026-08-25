# vHarness `0.1.0-alpha.1` P1 evidence

Result: **PASS on Windows for the non-mock reference persistent process
Guest.**

The adapter built a private `.aimg` from a stopped `vharness:source` instance,
then restored it twice into absent targets. Each target started a fresh vhd
kernel and completed a live `wake → audit → wake` round-trip through the
process-Guest protocol.

The four persistent Agent-state items were byte-semantically equal before and
after restore. Their canonical digest remained
`sha256:7f24160f891d2463facb4c1dcdb8e121e0b673741599786af3142460e0ddc61d`.
The source instance digest also remained unchanged, and the `.aimg` archive
digest was identical before and after restore.

The target Host journal reached sequence 41, retained two complete typed loss
reports, recorded the source Agent Image digest in Guest evidence, and created
four fresh `vhd:*` grants. No Host authority, journal, kernel snapshot, or API
token entered the image.

The evidence also preserves an important limitation: `security_boundary` is
`false`, because the reference Guest retains ambient OS access. This proves P1
state restore through a real Host/Guest path, not strong isolation, a
model-backed Guest, DSH integration, or behavioral portability.

The machine-readable evidence is in
[`vharness-p1-v0.1.0-alpha.1.json`](vharness-p1-v0.1.0-alpha.1.json).
