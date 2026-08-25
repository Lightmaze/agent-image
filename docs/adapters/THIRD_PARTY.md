# Third-party adapter contract

Third-party packages register one factory under the
`agent_image.adapters` Python entry-point group. The entry-point name must equal
the adapter's stable `locator_prefix`.

```toml
[project.entry-points."agent_image.adapters"]
myharness = "my_package:create_adapter"
```

The returned object implements the public `ProductionAdapter` contract:

- stable `id`, `version`, and `locator_prefix`;
- `capabilities()`;
- `inspect_source(source)`;
- `export(source, policy, include_experience=..., include_workspace=...)`;
- `native_restore(image, target)` (it may fail explicitly when P1 is not
  declared).

Typed SDK records and helpers are exported from the installed `agent_image`
package: `AdapterCapabilities`, `SourceInventory`, `ExportPlan`, `RestorePlan`,
`MigrationPlan`, `OperationReport`, `AdapterExport`, `AgentImageError`, canonical
JSON/digest helpers, and `layer_root_digest`.

Registration is fail-loud. Invalid contracts, duplicate prefixes, or collisions
with `hermes`, `openclaw`, `dsh`, or `vharness` stop the command. Discovery does
not mark a runtime as verified; capability evidence remains a separate artifact.

See `examples/clean_room_adapter/` for a separately buildable P0 package that
uses no built-in adapter modules and requires no Core schema changes.
