# Mutl3y Workflow Authoring

Updated: 2026-05-02

This guide is the repo-local minimum for authoring or repairing a Mutl3y workflow run in Prism.

## Scope

Use this when creating or editing any plan under `docs/plan/mutl3y-review-workflow-*/`.

For new review/fix cycles that are not workflow drills, use the same Mutl3y
naming family for the plan directory and `plan_id`.

- New default review cycle pattern: `mutl3y-review-YYYYMMDD-gN`
- Keep `cycle: gN` as the short cycle label inside artifacts and ledgers.
- Treat `gilfoyle-review-*` as historical naming only; do not start new cycles
  with that prefix.

The local contract is enforced by:

- `scripts/validate_mutl3y_plan_contract.py`
- `scripts/record_execution_trace.py`
- `src/prism/tests/test_mutl3y_plan_contract_validator.py`
- `src/prism/tests/test_record_execution_trace.py`

## Minimal Plan

Every plan needs these top-level fields:

- `plan_id`
- `cycle`
- `status`
- `resumption_pointer`
- `artifacts`

Minimal valid example:

```yaml
plan_id: mutl3y-review-workflow-example-20260502
cycle: mutl3y-example-1
title: "Example narrow live slice"
status: in_progress
created_at: "2026-05-02"
review_type: live_narrow_run
target: src/prism/example.py
focus_axis: control_flow
origin: "Example only"

resumption_pointer:
  current_phase: P5
  next_action: "Dispatch Builder-Typing for wave 1 and wait at the barrier."
  blocking_issues: []
  notes: |
    Keep plan.yaml and execution-trace.yaml synchronized at every barrier.

artifacts:
  findings: docs/plan/mutl3y-review-workflow-example-20260502/findings.yaml
  execution_trace: docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/execution-trace.yaml
  wave_start_audit: docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-start-audit.yaml
  wave_plan: docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-plan.yaml
```

## Required Phase Dependencies

The validator enforces a few local workflow rules beyond top-level shape:

- `artifacts.execution_trace` is always required.
- `wave_plan` requires `wave_start_audit`.
- If `current_phase` is `P6`, `P7`, or `CLOSED` and `wave_plan` exists, a barrier artifact must also exist.
- Completed plans with gate summaries must also carry `closure_summary` or `recovery_summary`.

## Minimal Artifact Examples

Minimal execution trace:

```yaml
version: 1
plan_id: mutl3y-review-workflow-example-20260502
cycle: mutl3y-example-1
updated_at: "2026-05-02T00:00:00Z"
authoritative_resume_anchor: docs/plan/mutl3y-review-workflow-example-20260502/plan.yaml
latest_checkpoint:
  phase: P5
  status: OK
  next_action: "Wait at barrier."
  blocking_issues: []
  plan_pointer_synced: true
timeline: []
```

Minimal wave start audit:

```yaml
cycle: mutl3y-example-1
plan_id: mutl3y-review-workflow-example-20260502
phase: P5
wave: 1
status: started
expected_workers:
  - Builder-Typing
expected_artifacts:
  - docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/Builder-Typing-summary.md
present_artifacts:
  - docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-start-audit.yaml
missing_artifacts: []
```

Minimal barrier summary:

```yaml
cycle: mutl3y-example-1
plan_id: mutl3y-review-workflow-example-20260502
phase: P5
wave: 1
status: pass
present_artifacts:
  - docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/Builder-Typing-summary.md
missing_artifacts: []
```

Minimal model ledger:

```yaml
- timestamp: "2026-05-02T00:00:00Z"
  cycle: mutl3y-example-1
  phase: P5
  worker: Builder-Typing
  requested_model: GPT-5.4 mini
  actual_model: GPT-5.4 mini
  result: success
  artifact_path: docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/Builder-Typing-summary.md
  quality_score: 4
  needed_reedit: false
  recovery_action: none
```

Minimal model scorecard:

```yaml
cycle: mutl3y-example-1
phase: P7
models: {}
```

## Validation Commands

Validate one plan:

```bash
python3 scripts/validate_mutl3y_plan_contract.py \
  docs/plan/mutl3y-review-workflow-example-20260502/plan.yaml
```

Validate all current workflow plans:

```bash
python3 scripts/validate_mutl3y_plan_contract.py \
  docs/plan/mutl3y-review-workflow-*/plan.yaml
```

Run the focused validator tests:

```bash
.venv/bin/python -m pytest -q src/prism/tests/test_mutl3y_plan_contract_validator.py
```

Run the stateless warning guardrail cluster:

```bash
.venv/bin/python -m pytest -q src/prism/tests/test_t2_04_stateless_marker.py
```

Write or update an execution trace checkpoint:

```bash
python3 scripts/record_execution_trace.py \
  --plan-dir docs/plan/mutl3y-review-workflow-example-20260502 \
  --plan-id mutl3y-review-workflow-example-20260502 \
  --cycle mutl3y-example-1 \
  --phase P5 \
  --wave 1 \
  --status OK \
  --status-line "[mutl3y-example-1 | P5 wave 1 barrier | OK — builder complete]" \
  --next-action "Run Gatekeeper." \
  --event wave_barrier \
  --summary "Wave barrier cleared." \
  --source-summary-artifact docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml \
  --plan-pointer-synced true \
  --receipt-proof "Builder returned in this turn" \
  --artifact-proof docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml \
  --source-artifact docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml
```

Add `--validate-log docs/plan/<plan-id>/.mutl3y-gate/trace-write.log` when you want the helper to emit repo-local PASS/FAIL evidence after writing the checkpoint. If `plan.yaml` exists, the helper validates the whole plan contract after the trace write instead of only YAML parseability.

Record barrier recovery directly into `failure_debug`:

```bash
python3 scripts/record_execution_trace.py \
  --plan-dir docs/plan/mutl3y-review-workflow-example-20260502 \
  --plan-id mutl3y-review-workflow-example-20260502 \
  --cycle mutl3y-example-1 \
  --phase P5 \
  --wave 1 \
  --status STALL \
  --status-line "[mutl3y-example-1 | P5 wave 1 barrier | STALL — missing artifact]" \
  --next-action "Re-dispatch Builder-Typing." \
  --event wave_barrier \
  --summary "Barrier stalled on missing summary artifact." \
  --source-summary-artifact docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml \
  --plan-pointer-synced false \
  --source-artifact docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml \
  --failure-class missing_artifact \
  --failing-worker Builder-Typing \
  --expected-worker Builder-Typing \
  --missing-artifact docs/plan/mutl3y-review-workflow-example-20260502/mutl3y-artifacts/phase5/Builder-Typing-summary.md \
  --relevant-log .mutl3y-gate/example.log \
  --recovery-attempt "checked owned file set" \
  --recovery-attempt "re-dispatched on next healthy model" \
  --validate-log docs/plan/mutl3y-review-workflow-example-20260502/.mutl3y-gate/trace-write.log
```

## Common Failures

- Missing `execution_trace`: every plan must carry it.
- Missing `wave_start_audit` when `wave_plan` exists: phase entry has not been proven.
- Missing barrier summary at `P6` or `P7`: the wave did not actually clear its barrier.
- Malformed ledger YAML: use the deterministic writer, not hand-edited tabbed YAML.
- Recurring stateless-marker warnings in tests: add `PLUGIN_IS_STATELESS = True` to registered `scan_pipeline` test doubles unless the test is explicitly exercising the warning path.
- Barrier recovery steps should be recorded through `scripts/record_execution_trace.py` rather than hand-editing `execution-trace.yaml`.
