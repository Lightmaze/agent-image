# Security and privacy hardening matrix

Verdict: **PASS for the locally observed v0.1 beta gates, with explicit claim
limits**.

The release suite covers parent traversal, POSIX and Windows absolute paths,
drive-relative and UNC forms, backslashes, empty/dot segments, symlink entries,
duplicate archive paths, undeclared and missing payloads, digest tampering,
secret filenames, and structured secrets in JSON, YAML, JSONL, and TOML.

Structured content now fails closed if its declared format cannot be parsed.
This prevents malformed JSON/YAML/TOML/JSONL from becoming an escape hatch for
secret scanning. Unknown privacy classification remains non-public and public
build/redaction excludes private and unknown state. Inspect and diff expose
metadata without payloads.

No-overwrite tests cover images and operation-report files. Adapter tests
reconcile every inventory item to a typed outcome. A real pinned OpenClaw
Windows failure-injection run also proved complete official-host and workspace
rollback after target creation.

The complete local suite passes 65 tests, 9 registered test-only mock points
with no issues or production blockers, and the UTF-8/mojibake scan.

## Claim boundary

This is not universal DLP, code safety, publisher authentication, encryption,
or a trust store. GitHub-hosted Windows/Linux/macOS jobs are configured but not
claimed as observed results here. Real OpenClaw rollback injection was observed
on Windows only.
