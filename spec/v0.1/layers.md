# Logical Layers

Layer semantics are defined by `SPEC.md`; this file records mapping rules.

1. Preserve source bytes when possible and attach semantic metadata rather than
   destructively rewriting files.
2. Use `native` for state that cannot be faithfully interpreted by Core.
3. Use `other` only when an extension media type defines the semantics; it is not
   a place to hide unsupported state.
4. Split items with different privacy or portability classes into separate layer
   descriptors.
5. `source` metadata may name an original path and adapter reason, but producers
   SHOULD remove absolute machine paths before publication.
6. A layer path MUST live below `layers/<kind>/` where `<kind>` equals its
   descriptor kind.
7. A summary or materialized view is derived evidence. Keep it separate from raw
   experience and retain a source path, URI, digest, or adapter report that makes
   the derivation auditable.
8. Skill artifacts describe reusable resources; they are not by themselves
   evidence that an agent acquired or retained a skill.

Portability values are:

- `portable`: another adapter may interpret the payload from documented semantics;
- `adapter-specific`: a named adapter understands it;
- `opaque`: bytes are preserved without a portable interpretation.
