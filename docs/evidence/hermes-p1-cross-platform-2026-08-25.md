# Hermes P1 cross-platform evidence

Verdict: **PASS on local Windows and WSL Linux** for the pinned Hermes
`0.20.5` contract.

The same synthetic named profile was exported and restored through the real
official Hermes CLI in both environments. Both sources remained unchanged,
both fresh targets were recognized and validated, and all seven layer paths,
digests, and sizes matched. The shared image content digest is:

```text
sha256:a30d66aa30aafaa8137eefb7744764a60a72cfe2e54a330675b575961044c31a
```

The `.aimg` archive bytes intentionally differ because `created_at` records
the actual export time. Semantic content does not differ.

## Failures that improved the gate

The pinned Hermes release is absent from PyPI. Its official source also
deliberately rejects wheel and sdist construction, so CI checks out the exact
full commit and installs it editable, matching the upstream contract.

The first cross-platform run also exposed CRLF/LF drift in the synthetic input.
The smoke now writes explicit UTF-8 LF bytes. A rerun produced identical
semantic and native-layer digests across Windows and Linux.

## Claim boundary

GitHub Actions now declares real Hermes smoke jobs for Windows and Ubuntu, but
this record observes local Windows and WSL Linux only; it does not pretend an
unrun hosted job has passed. macOS has Core CI coverage, not a real Hermes P1
claim. P3 remains unverified.

Machine-readable evidence is in
`docs/evidence/hermes-p1-cross-platform-2026-08-25.json`.
