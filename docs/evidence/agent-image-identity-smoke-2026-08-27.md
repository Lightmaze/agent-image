# Agent Image identity and rc.1 package smoke

Result: **PASS on local Windows and WSL Linux**

This check verifies that the public identity correction is an installable
release change, not only a README rename.

- The project metadata and lockfile resolve the distribution as
  `agent-image==0.1.0rc1`; the CLI remains `agent-image` and the import namespace
  remains `agent_image`.
- The renamed wheel and source distribution each installed in a fresh Windows
  Python 3.12 environment without `PYTHONPATH`. Both exposed the CLI and passed
  inspect, verify, redact, diff, and Registry smoke operations.
- The same release-bundle wheel installed in a fresh WSL Ubuntu Python 3.12
  environment.
- On both Windows and WSL, the installed wheel verified the fixed public hero
  digest `sha256:8a258bc82ba8b161a107a4cf970c51e1f19228dcc78c8696e0bf13a699e257b2`,
  restored it through real Hermes `0.20.5`, validated P1 with seven inventory
  outcomes, and produced a Hermes-recognized `procurement-negotiator` profile.
- The six-file rc.1 release bundle contains only the renamed package artifacts;
  every entry in `v0.1.0-rc.1.sha256` matches its copied release asset.

No provider call was repeated. The previously preregistered
[fresh-restore comparison](public-hero-restore-comparison-2026-08-26.md) remains
the behavior evidence; this check covers public identity, packaging, transport,
and native restore.
