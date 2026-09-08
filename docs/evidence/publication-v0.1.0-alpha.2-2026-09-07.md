# First public release: v0.1.0-alpha.2

Published September 7, 2026 (America/New_York), at `2026-09-08T01:40:38Z`.

**Result: the public download-to-use path passes.** Install the CLI, verify the
developed-state image, restore into a fresh Hermes home, and use the restored
Agent. This remains an alpha technical preview with the existing bounded claims.

- [Public repository](https://github.com/Lightmaze/agent-image)
- [Download the six release assets](https://github.com/Lightmaze/agent-image/releases/tag/v0.1.0-alpha.2)
- [Passing release-tag CI](https://github.com/Lightmaze/agent-image/actions/runs/34177445943)
- [Machine-readable publication evidence](publication-v0.1.0-alpha.2-2026-09-07.json)

## What a downloader receives

The fixed annotated tag resolves to `d4cca1cc48529425feffb32ac8c2c47d140da4f1`.
Anonymous GitHub API access confirms a public repository and a published,
non-draft prerelease with six assets. All six assets were downloaded without
GitHub credentials on Windows and WSL Linux. Their file digests match GitHub's
asset digests; the five content assets also match the included checksum file.

| Public-package check | Observed result |
|---|---|
| Fresh Windows wheel install, Python 3.12.10 | Pass; no `PYTHONPATH` |
| Fresh Windows source-distribution install | Pass; installed CLI verifies the downloaded hero |
| Fresh WSL Linux wheel install, Python 3.12.13 | Pass; no `PYTHONPATH` |
| Real Hermes 0.20.5 restore and profile recognition | Pass in fresh, isolated Windows and Linux homes |
| Cross-platform verify / inspect / restore reports | Byte-identical for all three reports |
| Downloaded Registry | Seven records validate; one public image, six private evidence records |
| Actual README task after Windows restore | `{"action": "counter", "offer": 260.00}`; private synthetic limit not disclosed |

The README task used the restored `procurement-negotiator` profile and
`deepseek-v4-flash` with `--reasoning none`. Credentials came from the process
environment, not the image. This single use check is not a repeat of the full
behavioral experiment; the [earlier controlled comparison](public-hero-restore-comparison-2026-08-26.md)
remains the source for the 24-decision result.

The image has seven public layers. Restore reports five as preserved and two
development/evaluation evidence layers as unsupported by the native Hermes
profile import. Those two remain in the source image; they are not silently
discarded or claimed as imported runtime state. Both platforms report the same
outcomes and validate P1.

## Hosted checks and the first-use correction

All 12 release-tag CI jobs passed: nine Core combinations across Windows,
Ubuntu, and macOS with Python 3.11–3.13; clean Windows wheel/sdist installation;
and real Hermes CLI round-trips on Windows and Ubuntu.

The [first hosted run](https://github.com/Lightmaze/agent-image/actions/runs/34177125235)
found that the installation smoke script incorrectly required a warm offline
dependency cache. Commit `d4cca1c` makes offline mode opt-in and checks every
native command's exit status. The [corrected commit run](https://github.com/Lightmaze/agent-image/actions/runs/34177276201)
and release-tag run both passed. No protocol or runtime behavior was changed.

## Publication boundary

Only the independent Agent Image repository was published. Remote refs contain
`main` and the reviewed alpha.2 tag; the older local alpha.1 tag was not pushed.
Commit and tag identities use project GitHub noreply metadata. The previously
reviewed public-safe artifact set was uploaded unchanged. The release-file
SHA-256 remains distinct from the protocol's layer payload-root digest.

The release is now usable without access to the author's workspace. Future
development proceeds through new commits and versions; the published tag and
assets are not rewritten.
