# Public hero cross-platform release path

Verdict: **PASS on local Windows and WSL Linux**

The same `v0.1.0-rc.1` bundle and the same
`procurement-negotiator-v1.aimg` file were used in both environments. All five
asset checksums passed. The wheel installed as `open-agent-image==0.1.0rc1`, and
the installed CLI verified and inspected the image without `PYTHONPATH`.

Windows and WSL Linux produced byte-identical verify, inspect, and restore JSON
reports. Both restored the hero image through Hermes `0.20.5` as P1, validated
all seven inventory outcomes, and recognized the same runtime surface:

| Surface | Windows | WSL Linux |
|---|---:|---:|
| Memory characters | 3,987 | 3,987 |
| Tools | 0 | 0 |
| Model | `deepseek-v4-flash` | `deepseek-v4-flash` |

Windows additionally completed the public synthetic README task and returned
`counter 260.00` without revealing the private limit. That provider call was
not repeated on Linux; the independent 48-call comparison already establishes
the bounded behavior result, while this run checks release transport and P1
restore across environments.

These are two local operating-system environments on one host. Hosted CI and
macOS remain unobserved and are not included in the claim.
