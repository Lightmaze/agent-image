# Native State Run 70 — repository integration checkpoint

Status: executable repository integration; isolated branch; not merged to main; MAGE runtime P1 still open.

## What changed

Run 70 stops treating structured-native Core support as an external overlay and lands the first executable slice into the real Agent Image repository.

Branch: `web/agent-image-run70-integration`

First executable integration commit:

`41c202a3c8dfb73fc1f51757ef9efe692540a654`

The commit adds:

- `native_capsule.py`: safe, no-extraction native-capsule parsing and schema/digest validation;
- `native_classification.py`: final effective privacy homogeneity and structured-native portability invariant;
- `native_realization.py`: content-bound realization sidecar envelope and reference validation;
- `structured_native.py`: Core envelope verification plus metadata-only native diff;
- `image_archive.py` integration so normal `verify`, `inspect`, `diff`, and whole-layer `redact` traverse the structured-native boundary;
- realization-binding regression tests.

This is deliberately a Core reader/verifier cut. It does not yet land producer finalization, reviewed build-plan execution, prepared publication/workspace recovery, MAGE realization preflight/migration, or typed native-transition evidence.

## Repository gate

GitHub Actions run 37227860881 for the executable commit completed successfully.

All 12 jobs passed:

- Python 3.11 / 3.12 / 3.13 on Ubuntu, Windows, and macOS;
- full pytest;
- mock-point scan;
- mojibake scan;
- Registry validation;
- wheel/sdist build;
- installed-package smoke;
- real Hermes smoke on Ubuntu and Windows.

This is the first repository-level CI evidence for the structured-native Core slice, rather than a docs-only checkpoint or an external candidate test.

## CI false-negative removed

Creating the integration branch at the unchanged Run 68 head triggered run 37227442565. Product steps passed, but the Windows installed-package job failed only in `setup-uv` post-job cache cleanup because its private cache directory did not exist. The job already passes an explicit `.tmp/uv-cache` directory to every uv command, so Run 70 disables setup-uv's separate cache for that job. This is CI infrastructure hardening, not a product workaround.

## Current claim boundary

Run 70 may claim:

- the repository's normal Core verify path now recognizes and validates structured-native capsule layers;
- realization sidecars are bound and profile-matched at the generic envelope level;
- normal inspect/diff expose metadata-only structured-native summaries;
- public redaction remains whole-layer and does not rewrite native inner objects;
- the integrated slice survives the repository's complete current CI matrix.

Run 70 may not claim:

- producer-side structured-native capture/publication is integrated;
- reviewed plan / prepared publication transaction is integrated;
- MAGE full `MageMemory load -> query -> write -> flush/freeze -> reload` P1 is proven;
- semantic migration or native transition is a Core-level universal contract;
- behavioral retention follows from structural verification.

## Next integration cut

Land the producer/publication half on top of this exact branch:

`build_plan.py` + `native_privacy_plan.py` + `native_export_planner.py` + prepared-build/workspace transaction + formal service/CLI integration.

The required end-to-end gate is then:

structured-native source preview
→ reviewed build plan
→ capture
→ producer finalization
→ recoverable prepared candidate
→ source-free exact publication
→ Core verify / inspect / diff / redact
→ installed wheel/sdist CLI smoke.

MAGE runtime-specific preflight/migration remains behind the profile boundary until the generic producer→Core path is repository-green.
