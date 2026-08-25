# v0.1 beta schema freeze

The `agent-image/v0.1` manifest and operation-report vocabulary entered beta
freeze after the four built-in adapter C0 gates and the clean-room fifth-adapter
gate passed on 2026-08-25.

Until `v0.1.0`, changes to existing v0.1 fields, enum meanings, digest rules,
privacy defaults, and loss outcomes are forbidden. Additions must be optional,
backward-compatible extensions. Breaking discoveries require a new protocol
version rather than silently changing v0.1 semantics.

This freeze does not assert that final release gates have passed. In
particular, the trained-agent Gate E remains negative, cross-platform hardening
and Registry work remain, and no P3 claim is permitted.
