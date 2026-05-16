# Phase 5 Builder Policy

Builder lanes:

- `Builder-Typing`
- `Builder-Abstraction`
- `Builder-ControlFlow`
- `Builder-Duplication`
- `Builder-Ownership`

Builder return contract:

- agent name
- owned file set
- summary artifact path
- changed files
- concise status

Typing-sensitive, DI-sensitive, and contract-preservation rules:

1. Emit the hard bans before editing: never use `dict(TypedDict)`, never use `cast` after a lossy transform, never use `cast(Any, ...)`, never widen to `Any` to silence mypy, and never add silent fallbacks to DI resolution.
2. Require builders to name the contract or fail-closed invariant each owned file preserves before producing diffs.
3. Run the immediate narrow gate after each wave: `pytest -q` plus `mypy --no-error-summary | head -3` on touched modules only.
4. Use `balanced` tier models first for typing-sensitive, DI-sensitive, and contract-preservation work.
5. Expect first-pass re-edit burden on typing and DI work; plan the wave with that assumption.

Wave barrier checks:

- Verify every dispatched builder produced its expected summary artifact.
- If edits are present but the summary artifact is missing, recover the artifact locally and note `artifact recovered by foreman`.
- If edits are absent, re-dispatch the worker before the gate.
- Do not leave the wave barrier until every finding is either complete or explicitly re-dispatched.

Mandatory anti-pattern grep gate at the wave barrier:

```bash
mkdir -p .mutl3y-gate/tmp && \
rg -n "cast\(Any,|typing\.cast\(Any," src/prism > .mutl3y-gate/tmp/wave-antipattern-cast-any.txt || true && \
rg -n "cast\([^\)]*TypedDict[^\)]*,\s*dict\(|cast\([^\)]*,\s*dict\(" src/prism > .mutl3y-gate/tmp/wave-antipattern-typeddict-lossy-cast.txt || true && \
rg -n "except\s+Exception\s*:\s*pass" src/prism > .mutl3y-gate/tmp/wave-antipattern-except-pass.txt || true
```

Barrier verdict rule:

- PASS only when all three outputs are empty or contain acknowledged baseline-only hits.
- FAIL when new wave-introduced hits appear; remediate or defer explicitly before proceeding.

Use `phase-5-fix-wave-prompt.md` as the worker prompt contract.
