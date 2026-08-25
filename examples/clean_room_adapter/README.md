# Clean-room fifth adapter

This package uses only the installed `agent_image` public SDK and the
`agent_image.adapters` entry-point group. It does not import adapter
implementations, modify the Core schema, or require a source-tree checkout.

Its deliberately small `cleanroom:<state.json>` producer proves extension
registration and the common archive/report contract. It claims P0 only.
