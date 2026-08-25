# Negotiation Training Ground

This is a disposable scientific probe for Gate E, not a production Habitat and
not a mock behavioral proof. It asks whether practice owned by one persistent
Hermes profile survives Agent Image freeze and fresh native restore when the
model and evaluation stay unchanged.

The experiment uses only synthetic procurement data. It runs 48 practice
episodes and evaluates 20 held-out scenarios twice at each of three points:
before practice, after practice, and after fresh restore. Primary scoring is
deterministic; model output is retained as raw evidence.

Run a single real-provider connectivity probe first:

```powershell
uv run python -m experiments.negotiation_ground.runner probe `
  --hermes .venv-hermes/Scripts/hermes.exe `
  --run-root .tmp/negotiation-probe
```

Then run the preregistered experiment:

```powershell
uv run python -m experiments.negotiation_ground.runner run `
  --hermes .venv-hermes/Scripts/hermes.exe `
  --run-root .tmp/negotiation-ground-20260824
```

The preregistration caps the run at 168 model calls and USD 1.00 in estimated
provider cost. If the process is interrupted, pass `--resume` with the same
arguments and run root. A resume validates the model identity, reuses only
completed checkpoints, and never repeats a recorded scenario.

The runner never deletes or overwrites an existing run root. Credentials are
inherited from the process environment and are never written to prompts,
profiles, images, or evidence. A completed run produces `before.aimg`,
`trained.aimg`, raw JSONL, usage records, and `final-evidence.json`.
