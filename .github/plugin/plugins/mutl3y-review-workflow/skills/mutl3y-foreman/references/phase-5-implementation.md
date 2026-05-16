# Phase 5 Implementation

Purpose:

- Run implementation waves using named builders with explicit file ownership.
- Keep builder execution artifact-backed, wave-scoped, and barrier-checked.

Source of truth:

- `mutl3y-artifacts/phase5/wave-<N>-start-audit.yaml`
- `mutl3y-artifacts/phase5/wave-<N>-plan.yaml`
- `findings.yaml`

Load now:

- `phase-5-builder-policy.md`
- `parallel-execution.md`
- `multiprocess-execution.md`
- `phase-5-fix-wave-prompt.md`
- `phase-start-audit-template.yaml`
- `common-traps.md`

Use companion entrypoint:

- `../../agents/mutl3y-builder.agent.md`

Rules:

- Implementation workers are the default.
- Launch the full disjoint builder batch before waiting at the wave barrier.
- Every builder must have an explicit owned file set.
- The foreman does not take edits back unless a worker fails or scopes overlap.
- If the foreman performs emergency recovery edits, that exception must be
  recorded as `foreman_recovery` in the wave artifact and may cover only one
  narrow validated slice before builder dispatch resumes.
- Dispatch proof, stall recovery, and cancelled-worker handling are
  controlled by `foreman-execution-guardrails.md` and
  `model-routing-policy.md`.

Barrier:

- Verify one summary artifact per dispatched builder.
- If an artifact is missing, inspect owned files first, then recover or re-dispatch.
- Run the narrow gate and the anti-pattern grep gate from
  `phase-5-builder-policy.md` before leaving the wave barrier.
- Sync model ledger, scorecard, and `plan.yaml` state before moving to validation.
- For real or interruption-prone runs, write or update
  `mutl3y-artifacts/execution-trace.yaml` with the confirmed
  wave-barrier state, or with the failure-debug slice if the barrier
  stalls. Use a repo-local trace writer with validation logging when
  the repository provides one.

Outcomes:

- `P5 complete -> P6`
- `repeat P5 wave`
- `STALL`
- `BLOCKED`
