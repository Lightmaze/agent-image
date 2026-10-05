# Native State Run 71 — producer transaction candidate

Repository-validated base: `web/agent-image-run70-integration` at `9d39592607fbb238df2d35a0b94db8a4acf3ead0`.

Run 71 specifies the next generic structured-native construction slice: a persisted reviewed build subject, pre/post capture drift gates, conservative atomic privacy finalization, and a two-file prepared workspace whose receipt binds the exact candidate artifact. Final publication is intentionally source-free and grants neither runtime activation nor receiver authority.

The candidate introduces three logical contracts: `agent-image-build-plan/v0.1`, `agent-image-structured-native-subject/v0.1`, and `agent-image-prepared-build/v0.1`. Mixed structured-native privacy is finalized conservatively; private/unknown units are removed whole from public output rather than generically sliced. Authoritative payload bytes remain unchanged when only classification metadata is promoted.

A local candidate implementation and focused synthetic integration harness passed 8 tests covering plan binding, both drift gates, privacy promotion, whole-unit public removal, source-free publication, and tamper rejection. This is candidate evidence only. No Run 71 repository CI, installed-package smoke, MAGE P1, receiver activation, or behavioral-retention claim is made.

Next gate: apply the candidate producer slice to a clean Run 70 checkout, then run the full repository matrix plus installed wheel/sdist smoke for reviewed-plan → prepare → source unavailable → publish-prepared → verify/inspect/redact.
