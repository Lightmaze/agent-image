# Security Policy

The project is pre-release. Do not use it as the sole backup for a live agent and
do not publish images without inspecting their privacy summary and redaction
report.

Security bugs include archive path traversal, symlink escape, digest bypass,
undeclared payload acceptance, secret inclusion, private payload disclosure, and
silent state loss. Report them privately to the repository owner until a public
security contact is established.

The v0.1 policy is fail closed: secret items are never packable; public redaction
removes private and unknown items; restore must eventually validate into staging
before activation; image content never confers runtime authority. Declared
JSON, YAML, JSONL, and TOML that cannot be parsed also fails closed because an
unscannable structured file cannot be treated as secret-free.

SHA-256 checksums provide content integrity, not publisher authenticity. The
bootstrap alpha has no signatures, trust store, encryption, or universal DLP.
Do not infer that a valid image is safe to execute or that its provenance claims
are endorsed by this project.
