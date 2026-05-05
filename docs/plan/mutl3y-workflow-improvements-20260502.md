# Mutl3y Workflow Improvement Notes

Updated: 2026-05-02

## Exercise Result

- Parsed all `docs/plan/mutl3y-review-workflow-*/plan.yaml` files in the current repo snapshot.
- Result: 8 plan files parsed cleanly.
- Added repo-local contract validation via `scripts/validate_mutl3y_plan_contract.py`.
- Contract validator result: all 8 Mutl3y workflow `plan.yaml` files passed structure, referenced-artifact, and phase-aware artifact checks.
- Added repo-local authoring guidance at `docs/plan/mutl3y-workflow-authoring.md` with minimal valid examples.
- Added a repo-local stateless-marker warning guardrail in `src/prism/tests/test_t2_04_stateless_marker.py` for the recurring warning-prone registry cluster.
- Added a repo-local execution-trace writer at `scripts/record_execution_trace.py` so barrier recovery steps can be recorded deterministically in `failure_debug`.
- Added validator-backed `--validate-log` support to the repo-local execution-trace writer so trace writes can emit repo-local PASS/FAIL evidence after each checkpoint update.
- Shared workflow prompt surfaces now standardize `record_execution_trace.py --validate-log` usage for real or interruption-prone runs.
- Status distribution:
  - `completed`: 6
  - `in_progress`: 1 (`mutl3y-review-workflow-realrun-20260502`)
  - `paused`: 1 (`mutl3y-review-workflow-trace-drill-20260502`)
- Core required fields present in all plan files checked:
  - `plan_id`
  - `cycle`
  - `status`
  - `resumption_pointer`
  - `artifacts`

## Repeated Friction Seen Across Existing Runs

- Required artifact gaps appear early in some runs and are detected only after phase-start audits.
- Manual or inconsistent model-ledger maintenance still creates avoidable recovery work.
- Narrow live slices repeatedly spend work on the same test-fixture warning cleanup pattern.
- Barrier recovery is documented, but the recovery path is still too manual when expected artifacts are missing.

## Landed Improvements

1. The plan validator now checks required phase dependencies and artifact schema for execution trace, audits, barriers, and model ledger files.
2. Model-ledger writes are now validator-backed in live workflow drills, and malformed YAML has a repo-local stall-and-recovery proof.
3. Every workflow run now carries either a populated ledger or an explicit empty ledger list shape.
4. A repo-local authoring guide now documents minimal valid examples for `plan.yaml`, barrier artifacts, and model bookkeeping artifacts.
5. A repo-local warning guardrail now fails if the known warning-prone scan-pipeline fixture cluster emits `UserWarning` output.
6. Real and interruption-prone workflow runs now have a standardized prompt-surface path for validator-backed execution-trace checkpoint writes.

## Current Disposition

1. Treat the six completed workflow runs as historical evidence, keep `mutl3y-review-workflow-realrun-20260502` as the only active workflow resume surface, and retain `mutl3y-review-workflow-trace-drill-20260502` as paused synthetic reference material.
2. The next highest-signal work has shifted back to code quality in `gilfoyle-review-20260502-g47`, where H12 is the next confirmed live High and H09 remains a narrower secondary carry-forward.
