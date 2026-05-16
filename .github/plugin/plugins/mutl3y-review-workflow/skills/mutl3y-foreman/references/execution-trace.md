# Execution Trace

Use this for real or interruption-prone workflow runs where restart durability matters.

Purpose:

- Keep one compact, machine-readable checkpoint file for the latest confirmed execution state.
- Make unexpected stops, stalls, or agent/session interruption recoverable without reconstructing state from many artifacts.
- Preserve the smallest failure slice needed to debug why execution stopped.
- Avoid turning the workflow into a transcript log.

This file does not replace `plan.yaml`.

- `plan.yaml` with `resumption_pointer` remains the authoritative restart anchor.
- `mutl3y-artifacts/execution-trace.yaml` is the checkpoint and audit companion.
- If the two disagree, repo artifacts win, then `plan.yaml` must be repaired, and the repair must be appended to the trace.

## When To Update

Write or update `docs/plan/<plan-id>/mutl3y-artifacts/execution-trace.yaml` only after a confirmed checkpoint.

Required checkpoint moments for real runs:

- after Phase 0 batch join and barrier clear
- after each Phase 5 wave barrier
- after the Phase 6 gate verdict
- after Phase 7 closure bookkeeping
- on any emitted `STALL`, `BLOCKED`, or `PAUSED` status
- immediately after repairing a stale `resumption_pointer`

Required diagnostic moments:

- any subagent cancellation, timeout, startup failure, or empty-output failure
- any missing-artifact barrier failure
- any false-clean or inconclusive-review safeguard trigger
- any plan-pointer repair caused by trace or artifact mismatch

## Preferred Write Path

When the repository provides a repo-local writer such as
`scripts/record_execution_trace.py`, use it instead of
freehand-editing `mutl3y-artifacts/execution-trace.yaml`.

Preferred command pattern:

```bash
python3 scripts/record_execution_trace.py \
  --plan-dir docs/plan/<plan-id> \
  --plan-id <plan-id> \
  --cycle <gN> \
  --phase <P0|P5|P6|P7> \
  --status <OK|STALL|BLOCKED|PAUSED> \
  --status-line "[<gN> | ... | ...]" \
  --next-action "<next-action>" \
  --event <phase_transition|wave_barrier|gate_verdict|closeout|...> \
  --summary "<one-line summary>" \
  --source-summary-artifact \
    docs/plan/<plan-id>/mutl3y-artifacts/<phase-summary>.yaml \
  --plan-pointer-synced <true|false> \
  --validate-log docs/plan/<plan-id>/.mutl3y-gate/trace-write.log
```

For `STALL`, `BLOCKED`, or `PAUSED` checkpoints, pass the compact
failure slice through helper flags such as `--failure-class`,
`--failing-worker`, `--missing-artifact`, `--relevant-log`, and
`--recovery-attempt` instead of hand-editing `failure_debug`.

If no repo-local trace writer exists, update `execution-trace.yaml`
manually and rerun the repo-local plan validator before leaving the
barrier.

Never write speculative future state.

- Do not log `wave launched` before receipts and artifact proof exist.
- Do not log `Phase 6 running` while builders are still unresolved.
- Do not log `next cycle starting` unless the next dispatch already happened.

## Minimal Shape

```yaml
version: 1
plan_id: "<plan-id>"
cycle: "gNN"
updated_at: "<ISO-8601>"
authoritative_resume_anchor: "docs/plan/<plan-id>/plan.yaml"

latest_checkpoint:
  phase: "P5"
  wave: 2
  status: "OK"           # OK | STALL | BLOCKED | PAUSED
  status_line: "[gNN | P5 wave 2 barrier | OK — 2 builders complete]"
  next_action: "Load Phase 6 validation manifest and run Gatekeeper."
  blocking_issues: []
  plan_pointer_synced: true
  receipt_proof:
    - "Builder-ControlFlow returned in this turn"
    - "Builder-Ownership returned in this turn"
  artifact_proof:
    - "docs/plan/<plan-id>/mutl3y-artifacts/phase5/wave-2-plan.yaml"
    - "docs/plan/<plan-id>/mutl3y-artifacts/phase5/Builder-ControlFlow-summary.md"
    - "docs/plan/<plan-id>/mutl3y-artifacts/phase5/Builder-Ownership-summary.md"
  source_summary_artifact: "docs/plan/<plan-id>/mutl3y-artifacts/phase5/wave-2-barrier-summary.yaml"
  failure_debug: null

timeline:
  - timestamp: "<ISO-8601>"
    phase: "P0"
    wave: null
    status: "OK"
    event: "phase_transition"
    summary: "4 scouts complete, 4 artifacts on disk"
    source_artifacts:
      - "docs/plan/<plan-id>/mutl3y-artifacts/phase0/Scout-Typing.yaml"
      - "docs/plan/<plan-id>/mutl3y-artifacts/phase0/Scout-Ownership.yaml"
      - "docs/plan/<plan-id>/mutl3y-artifacts/phase0/Scout-ControlFlow.yaml"
      - "docs/plan/<plan-id>/mutl3y-artifacts/phase0/Scout-Graph.yaml"
    plan_pointer_synced: true
      failure_debug: null

    # For STALL / BLOCKED / PAUSED checkpoints, replace failure_debug: null with:
    # failure_debug:
    #   failure_class: "missing_artifact"   # missing_artifact | cancelled_worker | timeout | startup_failure | empty_output | false_clean | plan_pointer_mismatch | gate_failure | external_blocker | unknown
    #   failing_workers: ["Scout-Graph"]
    #   expected_workers: ["Scout-Typing", "Scout-Ownership", "Scout-ControlFlow", "Scout-Graph"]
    #   returned_workers: ["Scout-Typing", "Scout-Ownership", "Scout-ControlFlow"]
    #   missing_artifacts:
    #     - "docs/plan/<plan-id>/mutl3y-artifacts/phase0/Scout-Graph.yaml"
    #   relevant_logs:
    #     - "docs/plan/<plan-id>/.mutl3y-gate/Scout-Graph.stderr.log"
    #   route_failures:
    #     - "Scout-Graph: GPT-5 mini timeout"
    #   last_successful_status_line: "[gNN | P0 start | OK — audit written]"
    #   suspected_slice: "Phase 0 barrier after scout join"
    #   recovery_attempted:
    #     - "checked owned file set"
    #     - "re-dispatched on next healthy model"
    #   debug_hypothesis: "Worker timed out before writing artifact."
```

## Recovery Rules

On resume:

1. Read `plan.yaml` first.
2. Read `execution-trace.yaml` second.
3. Verify that the trace's `latest_checkpoint` matches repo artifacts on disk.
4. If the trace is newer than `plan.yaml` and the artifacts support it, repair `plan.yaml` and append a `plan_pointer_repaired` timeline event.
5. If the trace is stale or missing, continue with `plan.yaml` plus repo artifacts and record `trace_unavailable` or `trace_stale` in the next checkpoint.

On failure diagnosis:

1. Read `latest_checkpoint.failure_debug` first when `status != OK`.
2. Check `missing_artifacts`, `failing_workers`, and `relevant_logs` before reopening broad exploration.
3. Use `last_successful_status_line` plus `suspected_slice` to restart from the nearest confirmed barrier.
4. If `debug_hypothesis` is wrong, overwrite it at the next confirmed checkpoint rather than appending chat narrative.

## Keep It Small

Allowed content:

- status lines
- next action
- blocking issues
- artifact proof paths
- short receipt proof
- one-line summaries
- compact failure slice for non-OK checkpoints

Do not include:

- full logs
- full YAML findings
- stack traces
- long narrative prose
- speculative future branches

Point to `.mutl3y-gate/*` or phase summary artifacts instead of copying them.
