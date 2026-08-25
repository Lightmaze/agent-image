# Clean-room fifth-adapter evidence

Result: **PASS.**

The main project wheel and a separately built fifth-adapter wheel were
installed offline into a fresh Python 3.12 virtual environment. The installed
CLI discovered `cleanroom` through the public `agent_image.adapters` entry-point
group, listed it beside the four built-ins, built a P0 image, and verified the
result.

The example imports only the installed `agent_image` public SDK. It neither
imports any built-in adapter nor changes the manifest/Core schema. Its limited
P0 claim is intentional: this gate proves protocol extension, not another
native restore.

The machine-readable evidence is in
[`clean-room-fifth-adapter-2026-08-25.json`](clean-room-fifth-adapter-2026-08-25.json).
