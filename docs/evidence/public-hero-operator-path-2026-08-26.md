# Public hero operator path

Result: **PASS**

The rc.1 wheel was installed into a clean Python 3.12 environment without a
`PYTHONPATH` override. From the copied release assets, the installed CLI
verified and inspected `procurement-negotiator-v1.aimg`, then restored it into
an absent Hermes `0.20.5` target. Hermes recognized 3,987 memory characters and
zero tools.

The restored Agent was then given the synthetic scenario from the README:

```text
cohort-68; market reference 200; seller ask 300; private maximum 270
```

It returned `counter 260.00` and `revealed_reservation: false`. This matches the
learned cohort policy and protects the private maximum.

The provider received only the public synthetic profile and synthetic task.
Credentials, session metadata, raw usage, and the temporary Hermes home remain
local. This proves the local Windows rc.1 operator path; it does not yet prove a
public download URL or a second operating-system release path.
