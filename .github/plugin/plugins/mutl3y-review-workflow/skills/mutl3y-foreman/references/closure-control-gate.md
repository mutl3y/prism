# Closure Control Gate

Purpose:

- Reduce foreman discretion at Phase 7.
- Convert cadence, deep-review, continuation, and commit rules into one
  artifact-backed gate before any cycle-close, pause, or `task_complete` claim.

This gate is mandatory before the foreman may report `cycle complete`, `PAUSED`,
or overall loop completion.

## Gate Artifact

Write this artifact before any Phase 7 close or pause claim:

`docs/plan/<PLAN_ID>/mutl3y-artifacts/phase7/closure-control-gate.yaml`

Required fields:

- `plan_id`
- `cycle`
- `phase: P7`
- `loaded_references`
- `cadence_state`
- `required_next_action`
- `god_mode_required`
- `god_mode_dispatch_status`
- `god_mode_independence_check`
- `continuation_surface`
- `commit_status`
- `foreman_deviation_check`
- `verdict`

`verdict` may be only one of:

- `OK_TO_CLOSE_CYCLE`
- `OPEN_NEXT_CYCLE`
- `PAUSED_WITH_RESUME_ARTIFACT`
- `REOPEN_CURRENT_CYCLE`
- `STALL`

## Mandatory Loaded References

Before writing the gate artifact, the foreman must load:

- `references/phase-7-close-and-learn.md`
- `references/iteration-cadence.md`
- `references/deep-review-protocol.md`
- `references/foreman-execution-guardrails.md`

If any of these are not loaded from current files in the same turn or resume
window, `verdict: STALL`.

## No-Waiver Rules

The foreman may not satisfy this gate with local judgment.

- A green Phase 6 gate is not a close verdict.
- Generic reviewers do not satisfy a required `Gilfoyle Code Review God Mode`
  pass.
- A closure-slice, changed-files, seam-family, or suspected-defect review does
  not satisfy an `independent`, `fresh`, or `unconstrained` pass.
- A prose final answer does not satisfy a continuation surface.
- `task_complete` is forbidden while this gate is missing, stale, or has
  `verdict: STALL` / `REOPEN_CURRENT_CYCLE`.

## God Mode Independence Check

When cadence or deep-review rules require God Mode, write the exact dispatch
prompt into `god_mode_independence_check.prompt_excerpt` before dispatch.

The check fails if the prompt contains any of:

- current findings or shortlist IDs
- closure claims or asks whether the current cycle was validly closed
- focus-axis hints
- suspected seam families
- named candidate files outside the broad target root
- instructions such as `check whether X is still broken`

If the check fails, rewrite the prompt before dispatch. Do not dispatch a biased
prompt and then decide later whether the result counts.

Valid unconstrained prompt shape:

```text
Role: independent whole-target reviewer.

Target: <TARGET_ROOT>
Plan ID: <PLAN_ID>
Write full results to: <ARTIFACT_PATH>

Rules:
- Review the whole target from live source.
- Do not use current cycle findings, closure claims, shortlist framing,
  focus-axis hints, suspected seam families, or named candidate files.
- Ignore the orchestrator's current hypothesis.
- Surface the highest-signal High/Critical findings wherever they actually are.
- Verify promoted findings against live source before writing them.

Return only: agent name, artifact path, finding count, and top findings.
```

## Continuation Surface

The gate must name exactly one continuation surface:

- dispatch receipt plus start-audit artifact for the next cycle or phase
- `mutl3y-artifacts/phase7/paused-resume.yaml`
- a reopened current-cycle finding in `findings.yaml`
- final sign-off only when cadence says a clean God Mode pass after the
  required clean thorough passes has completed

If none exists, `verdict: STALL`.

## Foreman Deviation Check

Set `foreman_deviation_check` with:

- `local_review_used_as_substitute: true|false`
- `generic_reviewer_used_as_substitute: true|false`
- `biased_god_mode_prompt_attempted: true|false`
- `closure_claim_before_required_dispatch: true|false`

Any `true` value requires `verdict: STALL` unless a corrective dispatch or
reopen artifact is already recorded in the same gate artifact.