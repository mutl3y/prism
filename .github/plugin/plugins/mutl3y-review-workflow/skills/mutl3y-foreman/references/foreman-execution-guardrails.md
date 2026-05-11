# Foreman Execution Guardrails

Read this before any Phase 0 start, any Phase 5 wave start,
any phase-transition status message, and any barrier verdict.

This file is the authoritative execution-control reference for:

- status-line discipline
- barrier checks
- dispatch proof
- stall recovery
- pre-message compliance checks
- phase-start audit artifacts
- minimal artifact inventory

## Foreman Status Check Protocol

**The foreman must emit a visible status line at every phase transition.** Format:

```text
[gN | Phase X → Y | STATUS]
```

Where STATUS is one of:

- `OK — N workers complete, N artifacts on disk`
- `STALL — <agent-name> missing artifact, investigating`
- `BLOCKED — <reason>`

**Mandatory status check points:**

1. After P0 batch joins:
  `[gN | P0→P1 | OK — 4 scouts complete, 4 artifacts on disk]`
2. After each implementation wave barrier:
  `[gN | P5 wave N barrier | OK — N builders complete]`
3. After gate completes:
  `[gN | P6→P7 | OK — 978 passed, ruff PASS, black PASS]`
4. Before reporting cycle complete to user:
  `[gN | cycle complete | findings closed: N, carried: N]`

**Dispatch monitoring checklist (required at each barrier):**

1. Record expected workers for the phase/wave.
2. Record returned workers:
  successful reply, cancellation, timeout, or startup error.
3. Record expected artifact paths and verify they exist on disk.
4. If an artifact is missing, verify file evidence in owned files before
  deciding recover vs re-dispatch.
5. Record model route failures and updated model health or quarantine state.
6. Append or update model usage ledger entries and recompute demotion or
  quarantine candidates.
7. Sync `plan.yaml` `resumption_pointer` to the actual current phase,
  next action, and blocking issues before leaving the barrier.

Immediately after step 6, record ledger updates through the deterministic writer:

```bash
python3 <SKILL_ROOT>/scripts/record_model_usage.py \
  --plan-dir docs/plan/<PLAN_ID> \
  --cycle <gN> \
  --phase <P0|P5|P6|P7> \
  --worker <AGENT_NAME> \
  --task-id <task-id> \
  --requested-tier <tier> \
  --requested-model <model> \
  --actual-model <model> \
  --result <success|route_failure|quality_failure> \
  --failure-type \
    <none|cancelled|timeout|startup|empty_response|...> \
  --artifact-path <artifact-path> \
  --quality-score <1-5> \
  --needed-reedit <true|false> \
  --recovery-action \
    <none|reroute_same_tier|escalate_tier|prompt_tighten|foreman_recovery> \
  --notes "<concise note>" \
  --validate-log .mutl3y-gate/ledger-validate.log
```

Do not freehand-write ledger rows when this script is available.

The script rewrites `mutl3y-artifacts/model-usage-ledger.yaml` and
`model-scorecard.yaml` deterministically and then validates both files.
If you must inspect the validation separately, use:

```bash
python3 <SKILL_ROOT>/scripts/validate_yaml_artifacts.py \
  docs/plan/<PLAN_ID>/mutl3y-artifacts/model-usage-ledger.yaml \
  docs/plan/<PLAN_ID>/mutl3y-artifacts/model-scorecard.yaml \
  > .mutl3y-gate/ledger-validate.log
```

If the writer or validation fails, emit `STALL`, repair the ledger or
scorecard, and rerun the same validation before leaving the barrier.
Tabs are forbidden in ledger and scorecard YAML; use space indentation only.

For real or interruption-prone runs, write or update
`mutl3y-artifacts/execution-trace.yaml` immediately after these seven
checks pass. The trace must point at the same confirmed checkpoint and
next action as `plan.yaml`.
When the repository provides a repo-local writer such as
`scripts/record_execution_trace.py`, use it with
`--validate-log docs/plan/<PLAN_ID>/.mutl3y-gate/trace-write.log`
instead of freehand-editing the trace.
When the status is `STALL`, `BLOCKED`, or `PAUSED`, the trace must also
capture the compact failure slice needed to debug the stop: failure
class, failing workers, missing artifacts, relevant logs, last
successful status line, suspected slice, and recovery attempts.
If no repo-local trace writer exists, update the trace manually and
rerun the repo-local plan validator before leaving the barrier.

The barrier is not complete until all seven checks are satisfied.

**If a status check cannot be emitted (stall):**

- Missing expected artifact means `STALL`, not "in progress".
- Stop immediately and emit `[gN | STALL — <description>]`
- Diagnose before continuing:
  check artifacts on disk, file edits, and cancellation errors.
- Do NOT narrate "next steps" while in a stall state
- Do NOT move to the next phase until the stall is resolved and an OK
  status can be emitted.

**Recovery order while stalled:**

1. Reconcile dispatch receipts:
  who was launched, who returned, and what error class if any.
2. Verify artifacts and file evidence for each missing/failed worker.
3. Re-dispatch only unresolved workers using the next healthy compatible model.
4. Repair stale `plan.yaml` resumption state if it no longer matches artifact reality.
5. Re-run barrier checks and emit updated status line.
6. Continue only after `OK`.

## Foreman-Recovery Edit Rule

Foreman-local editing is emergency recovery only, not a normal worker lane.

- If the foreman edits code inside a Phase 5 or Phase 6 repair slice, record
  `foreman_recovery` explicitly in the active phase artifact.
- A foreman recovery edit must be limited to one narrow slice with one focused
  validation bundle immediately after the edit.
- After that focused validation, return to canonical worker dispatch for the
  next unresolved slice unless a second concrete blocker is documented.
- Do not let foreman recovery silently become the default implementation mode
  across multiple consecutive slices.

Ledger-validation failures follow the same recovery rule.
Do not treat malformed YAML as bookkeeping noise.

## Context Health Escalation

If repeated re-reading, summary contradiction, or low-signal retries show that
artifact-first flow was not enough, the foreman must:

1. stop forward narration
2. record the degradation trigger in the active phase artifact or trace
3. reduce live context to the active phase, owned files, artifact anchors,
   and one short failure slice
4. refresh an anchored compaction summary when resume continuity is weak
5. restart from repo-backed state instead of conversational recall

Do not keep layering more prose on top of a degraded slice.

## Stale Gate Evidence Rule

Once any code change lands after a retained aggregate gate log was written,
that older aggregate gate log is no longer the authoritative remaining-failure
queue.

- Keep it as historical evidence, but mark it stale in the active phase
  artifact or trace.
- Do not keep selecting additional fix slices from that stale aggregate log
  after a later repair lands unless you first refresh the relevant gate.
- Valid refreshes are:
  - the full aggregate gate again, or
  - a smaller retained status batch that covers the remaining candidate queue
    you intend to trust.

If the queue is not refreshed, the correct status is `STALL`, not continued
triage from stale evidence.

## Aggregate-vs-Isolated Repro Rule

When a failure appears in the aggregate gate but a nearby isolated repro passes,
do not treat the aggregate failure as a confirmed production defect yet.

- First classify it as a possible order-sensitive or environment-sensitive
  failure.
- Run one cheapest discriminating repro that keeps just enough neighboring
  tests to check for contamination.
- Only after that repro fails should the slice become an implementation target.
- If the reduced repro passes, record the contradiction in the phase artifact
  and continue triage from a cleaner, confirmed slice.

**Anti-stall rule:** After emitting a cycle-complete status line,
the foreman MUST immediately dispatch the next phase, or the next cycle's
Phase 0 scouts, in the same response turn. Writing `Next: g28...`
without dispatching IS a stall. If the next cycle cannot start in the same
turn, emit `[PAUSED — waiting for user]` explicitly instead of implying
continuation.

**Continuation-surface rule:** If a retained gate summary, closure summary,
`plan.yaml` `next_action`, or other repo-backed artifact names a valid next
step and there is no active blocker, one of the following must exist before
the foreman may end the turn:

1. a dispatch receipt plus start-audit artifact for that next phase or cycle
2. `mutl3y-artifacts/phase7/paused-resume.yaml` naming the next step,
   pause reason, and whether commit was deferred

For Phase 7, `mutl3y-artifacts/phase7/closure-control-gate.yaml` must also
exist and carry a non-stall verdict. Without it, the correct status is `STALL`
even if the gate is green and the closure summary exists.

If neither exists, the correct status is `STALL`, not completion. In that
state, `task_complete` is forbidden.

**Commit-policy rule:** Missing commit permission must never become an
invisible workflow branch. If the user explicitly requested or approved repo
commits in the current conversation, the foreman must make the closure commit
non-interactively before opening the next cycle. If not, Phase 7 must record
`commit_deferred` with the reason and continue; it must not imply that a
commit was created, and it must not stall the loop solely because commit
permission is absent.

## Foreman Compliance Checklist

Use this as the final pre-message gate before any phase-transition update,
wave-progress claim, or cycle-status claim.

The foreman must answer `yes` to every item below before sending a progress
update that implies execution already happened:

1. **Receipt check:** Did the dispatch, validation, or recovery tool call
  already return in this turn?
2. **Artifact check:** Do the artifact paths that prove that action exists
  on disk right now?
3. **Ownership check:** For each writer, is the owned file set explicit and
  still disjoint?
4. **Barrier check:** Have returned workers, missing workers, and route
  failures been enumerated, not assumed?
5. **Plan-sync check:** Does `plan.yaml` `resumption_pointer` match the
  artifact-backed current state?
6. **Status check:** Can the update be expressed as one of `OK`, `STALL`,
  `BLOCKED`, or `PAUSED` without hand-waving?

If any answer is `no`, do not narrate progress. The only valid next statuses are:

- `STALL` when expected execution evidence is missing or contradictory
- `BLOCKED` when a real external dependency prevents progress
- `PAUSED` when the user, not the foreman, is the reason execution is stopping

Forbidden claim examples:

- "wave launched"
- "builders are working"
- "validation is underway"
- "this is complete"
- "next cycle is starting"

Those phrases are invalid unless the receipt check and artifact check are
both already satisfied.

## Cancelled Worker Recovery

Treat `error invoking subagent cancelled` and equivalent cancellation
failures as failed workers immediately.

Required recovery order:

1. Inspect the worker's owned files directly.
2. Determine whether edits are present and whether the expected artifact exists.
3. If edits are present but the artifact is missing, recover the artifact
  locally and note the recovery.
4. If edits are absent, re-dispatch the worker on the next healthy
  compatible model.
5. Record the cancellation in the phase artifact and in the model ledger
  before leaving the barrier.

Do not proceed to a gate or phase transition until the cancelled worker is
either recovered or re-dispatched successfully.

## Phase-Start Artifact Audit Rule

Before the foreman may narrate that Phase 0 has started, or that a Phase 5
wave is starting, ready, or queued for builders, it must first write a
repo-backed start-audit artifact for that phase entry.

Required artifact paths:

- Phase 0 cycle entry: `mutl3y-artifacts/phase0/phase-start-audit.yaml`
- Phase 5 wave entry: `mutl3y-artifacts/phase5/wave-<N>-start-audit.yaml`

## Resume dirty-tree pre-dispatch gate

- When resuming or continuing a prior cycle, the foreman must check for
  tracked, modified Python files in the working tree (dirty tracked `.py`
  files). If any are present, the foreman MUST run the resume-dirty-tree
  repo gate before narrating phase start or dispatching any new wave work.

- Required commands (repo-wide):

  - `.venv/bin/python -m ruff check src/prism`
  - `.venv/bin/python -m black --check src/prism`

- Outcome recording: write the result into the phase start-audit artifact
  (e.g. `mutl3y-artifacts/phase0/phase-start-audit.yaml` or
  `mutl3y-artifacts/phase5/wave-<N>-start-audit.yaml`) under `resume_dirty_tree`:

```yaml
resume_dirty_tree:
  status: OK|STALL|BLOCKED
  ruff_exit: <int>
  black_exit: <int>
  checked_at: <utc_iso8601>
  changed_files: [<paths>]
  log: .mutl3y-gate/resume-dirty-tree.log
```

- Status mapping and enforcement:
  - `OK`: both commands exited 0 — new wave work may proceed.
  - `BLOCKED`: either command failed (non-zero) — block new wave work until fixes and re-run; emit `BLOCKED` status line.
  - `STALL`: checks have not been run or are pending — block new wave work until checks run and status updated; emit `STALL`.

- The foreman must not narrate `Phase X started` or launch builders until
  `resume_dirty_tree.status` exists and equals `OK`.

## Execution Trace Checkpoint

For real or interruption-prone runs, maintain
`mutl3y-artifacts/execution-trace.yaml` according to
`references/execution-trace.md`.

Use that file as the canonical source for:

- checkpoint write timing
- required trace fields
- non-OK failure-debug content
- restart and plan-pointer repair rules

Narration rule remains strict here:

- If the start-audit artifact does not exist yet, the phase has not started
  for narration purposes.
- If the start-audit artifact says `stall`, the only valid user-facing
  status is `STALL`.
- Do not say "starting Phase 0", "launching wave N", or equivalent until
  the corresponding start-audit artifact is on disk.

## Minimal Artifact Inventory

Use `references/artifact-inventory.md` as the canonical source for minimum
phase and barrier artifacts.

If the cycle state implies one of those artifacts should exist and it does
not, emit `STALL`, recover the missing evidence, and only then continue.
