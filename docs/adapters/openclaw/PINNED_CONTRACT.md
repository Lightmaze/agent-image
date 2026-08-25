# OpenClaw Adapter Pinned Contract

## Pin

- npm package: `openclaw@2026.7.1-2`
- Tag: `v2026.7.1-2`
- Commit reported by the CLI: `0790d9f`
- npm integrity:
  `sha512-ycF3yPcbjN6bUPeaUx6Mh6vze1hQWoD3CT/wWcmD7a8xaHHHRUaAlaq+lFxMHf1ssEgODVAwjlzYqp2twkYZ7g==`
- Agent workspace contract:
  <https://github.com/openclaw/openclaw/blob/v2026.7.1-2/docs/concepts/agent-workspace.md>
- Agents CLI contract:
  <https://github.com/openclaw/openclaw/blob/v2026.7.1-2/docs/cli/agents.md>

The package declares Node
`>=22.22.3 <23 || >=24.15.0 <25 || >=25.9.0`. The release smoke uses Node
`24.15.0` and npm `11.12.1`.

The approved implementation plan named Node `24.13.0`. That version cannot
satisfy the pinned OpenClaw package. This is recorded as `NEEDS_DOC_FIX`; the
adapter follows the upstream package constraint rather than silently running an
unsupported combination.

## Public contract used by the adapter

```text
openclaw --version
openclaw agents list --json
openclaw agents add <name> --workspace <absolute-path> --non-interactive --json
openclaw agents delete <name> --force --json
```

Windows smoke tests pass the Node executable explicitly and run the official
package `openclaw.mjs`. They do not rely on ambient PATH resolution of npm's
`openclaw.cmd` shim.

## State boundary

The adapter inventories only the selected agent, its workspace, its agent
directory, and its sessions directory. It does not archive the whole OpenClaw
home.

- `SOUL.md`, `IDENTITY.md`, `AGENTS.md`, `TOOLS.md`, and `USER.md` are mapped
  to identity or workspace semantics.
- `MEMORY.md` and `memory/**` are mapped to memory.
- `skills/**` is mapped to skills.
- sessions are private and require explicit `--include-experience` on export;
  they are not semantically migrated from Hermes in v0.1.
- agent-native files that are not credentials remain in the typed native layer.
- `.git` contents and symlinks are unsupported rather than silently followed.
- auth profiles, credential paths, `.env`, secret filenames, and structured
  secret fields fail closed.

The typed native media type is
`application/vnd.openclaw.agent.v2026.7.1-2+tar+gzip`. Registration is not
copied as a config fragment; the official CLI recreates it for the new target.

## Restore and migration invariants

Native restore creates the absent agent through the official CLI, replaces only
the newly owned workspace contents, writes the typed state, asks OpenClaw to
recognize the target, and reconciles both the complete source inventory and all
image layers. Existing targets and workspaces are refused.

Hermes-to-OpenClaw migration is dry-run by default. The first v0.1 mapping
transforms compatible identity, selected memory, and `SKILL.md` files. Hermes
`state.db`, sessions, and unmapped workspace/config state remain in the source
image and are reported as unsupported. `.env` is redacted. The target records
the source image digest in `.agent-image/provenance.json`.

Rollback uses the official delete command, then verifies that host registration
and the owned workspace are gone. An incomplete cleanup raises
`E_ROLLBACK_FAILED`; it is never silently swallowed. Real failure-injection
rollback evidence remains an Epoch 4 security gate.

## Claim boundary

The current evidence establishes OpenClaw P1 on the pinned Windows contract and
Hermes-to-OpenClaw P2 for the declared mappings. It does not establish P3,
session migration, whole-home portability, later OpenClaw versions, or
failure-rollback hardening on every platform.
