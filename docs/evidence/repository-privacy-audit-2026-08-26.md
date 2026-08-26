# Repository and rc.1 bundle privacy audit

Verdict: **PASS to request publication authorization**

No repository or release is public yet. The candidate has no remote, so there
is no current external exposure. A future normal push of `main` would publish
the audited project history; it would not publish the one reflog-only recovery
commit, ignored `.tmp` experiments, or ignored `dist` contents unless those
objects were deliberately added to a ref.

## Findings

- The project is an independent Git root with one branch, one worktree, one
  prior annotated alpha tag, no remote, no submodule, and no nested Git root in
  the publishable tree.
- All 25 reachable commits and the one reflog-only commit use a synthetic or
  GitHub noreply author/committer identity. The annotated tagger is the same
  class. No identifying routable email was found.
- Git object validation passed. Reachable and reflog history contain no
  provider-token prefix, Bearer credential, private-key block, or personal
  machine path.
- A broad secret-assignment pattern found only the deliberate negative fixture
  and scanner assertions. The sole credential-shaped tracked filename is
  `tests/fixtures/secret-file/.env`, whose purpose is to prove that `.env` is
  rejected; it is not runtime configuration.
- No `.aimg` file is tracked. The public hero remains a release asset. The rc.1
  wheel and sdist contain no credential-shaped filename, the hero verifies with
  all layers public, and the six-asset bundle matches its checksum manifest.

The nested-repository mode of the bundled audit script could not traverse one
ignored private experiment directory because of its local ACL. No permission
was widened. A second read-only search explicitly excluded `.tmp`, `dist`,
build, dependency, and venv directories and found only this repository's own
`.git/config` in the publishable tree.

## Exposure classification

- Already public: none; no remote exists.
- Normal-push exposure: the project-only history on `main` after the audit
  follow-up commit.
- Force-only exposure: not applicable until a destination exists.
- Local recovery residue: one reflog-only commit; it is not part of a normal
  branch or tag push.

No history rewrite, force push, identity change, or cleanup is required. This
pass permits asking for the exact public destination and publication actions;
it does not itself authorize remote creation, push, tag, release creation, or
asset upload.
