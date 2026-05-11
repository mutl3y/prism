# Phase 7 Close And Learn

Purpose:

- Close findings after a green gate and compile durable learning.
- Fold cycle-local telemetry into the persistent lesson stores without
  turning them into transcripts.

Source of truth:

- The final gate summary and `.mutl3y-gate/` evidence
- `findings.yaml`
- `mutl3y-artifacts/model-usage-ledger.yaml` and `model-scorecard.yaml`
- Scout coverage patches and gate-escape learning artifacts

Load now:

- `closure-control-gate.md`
- `iteration-cadence.md`
- `deep-review-protocol.md`
- `foreman-execution-guardrails.md`
- `self-improvement-protocol.md`
- `memory-hygiene.md`
- `workflow-evaluation.md` when workflow prompts, guardrails, or routing
  changed during the cycle
- `ledger-schema.md`
- `phase-7-ledger-updater-prompt.md`

Use companion entrypoint:

- `../../agents/mutl3y-archivist.agent.md`

Rules:

- First write `mutl3y-artifacts/phase7/closure-control-gate.yaml` using
  `closure-control-gate.md`. Phase 7 may not report close, pause, or
  `task_complete` before that gate has a non-stall verdict.
- Default to foreman-local bookkeeping after a green gate.
- Use `Archivist-Ledger` only when closure bookkeeping is unusually large.
- Reconcile `findings.yaml` against all landed direct and delegated fixes
  before reporting cycle completion; every closed finding must carry
  fresh `closed_evidence` that points at the retained Phase 7 summary
  artifact and the focused validation bundle.
- Distinguish `cycle complete` from `overall loop may stop`. A green narrow
  or checkpoint cycle may close itself, but Phase 7 must not present that as
  final stop unless the iteration-cadence terminal condition has been met.
- Before any final stop or pause claim, reconcile older same-family review
  plans. If a predecessor plan remains `in_progress`, either close it with an
  explicit carry-forward handoff or keep it as the active resume surface.
- If the cadence terminal condition is not yet met after a green closeout,
  Phase 7 must leave a concrete continuation surface: either open the next
  required cycle or write `mutl3y-artifacts/phase7/paused-resume.yaml`
  naming the next cycle, the pause reason, and why overall stop is still
  invalid.
- A retained `next_recommendation` or `plan.yaml` `next_action` is binding at
  Phase 7. If it is valid and unblocked, Phase 7 must either dispatch the
  next cycle in the same turn or write the paused-resume artifact before the
  foreman ends the turn.
- `task_complete` is forbidden until that continuation surface exists on
  disk. A prose-only “next up” note is not enough.
- Commit handling must be explicit. If the user explicitly requested or
  approved repo commits in the current conversation, make one non-interactive
  closure commit before opening the next cycle. If commit is not authorized,
  write `commit_deferred` and the reason into the closure summary or
  paused-resume artifact, then continue the workflow without implying a
  commit happened.
- Promote durable lessons only when the criteria in
  `self-improvement-protocol.md` are satisfied.
- Record model-usage rows through `scripts/record_model_usage.py`; do not
  freehand-write ledger rows when the script is available.
- Immediately validate `mutl3y-artifacts/model-usage-ledger.yaml` and
  `model-scorecard.yaml` after any update; if validation fails, Phase 7
  must `STALL` until the malformed YAML is repaired.
- Ledger and scorecard YAML must use spaces only. Tabs are forbidden.
- When deep review or God Mode finds a missed High/Critical finding,
  write the scout coverage patch before closing the cycle.
- Do not let learning files become transcripts; summarize and deduplicate
  before promotion.
- Review newly promoted or recently touched lessons for stale routing
  assumptions, superseded wording, and conflicting active rules before
  finalizing the digest.
- After learning promotion, collapse wave-level artifact sprawl into one
  retained Phase 7 closure summary and perform a safe cleanup assessment
  for transient or duplicate artifacts before leaving the cycle; if
  automatic cleanup is not clearly safe, emit explicit cleanup
  candidates instead of silently retaining everything.
- When the cycle changed workflow references or prompts, run the compact
  workflow evaluation dimensions from `workflow-evaluation.md` before
  reporting closure of the workflow slice.
- If the repository provides a completed-plan cleanup helper, run it after
  the closure summary is written so pure wave scaffolding is pruned
  automatically from completed plans before the cycle is considered fully
  closed.
- If the repository provides a plan-archive helper, archive completed
  workflow-run plan directories out of the active `docs/plan` root once
  their closure summary and execution trace are retained and no resume
  path is still needed.
- For real or interruption-prone runs, write the final closeout
  checkpoint to `mutl3y-artifacts/execution-trace.yaml` before
  reporting cycle completion or pause. Use a repo-local trace writer
  with validation logging when the repository provides one.

Outcomes:

- `cycle complete`
- `repeat P7 bookkeeping`
- `STALL`
- `BLOCKED`
