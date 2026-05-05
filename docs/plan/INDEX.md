# Plan Inventory

Updated: 2026-05-05

## Active Plans

- `mutl3y-review-20260504-g73`
  - Current implementation-bearing Mutl3y review surface.
- `architecture-extensibility-review-20260421`
  - Active architecture backlog surface; async I/O remains the next planned engineering slice.

## Retained Closed Reference Plans

- `gilfoyle-review-20260502-g47`
  - Latest closed Gilfoyle review cycle retained at the top level as the current closed reference surface.
- `mutl3y-review-20260504-g72`
  - Latest closed Mutl3y review checkpoint retained at the top level as the current closed reference surface.
- `20260425-readme-renderer-plugin-design`
  - Design-only planning artifact retained as durable reference material.

## Mutl3y Review History

- Completed superseded Mutl3y review cycles should be archived out of the active root once closure evidence is retained and any carry-forward handoff is explicit.
- Archived Mutl3y review history lives under `archive/`:
  - `mutl3y-review-20260502-g48` through `mutl3y-review-20260502-g55`
  - `mutl3y-review-20260503-g56` through `mutl3y-review-20260503-g63`
  - `mutl3y-review-20260504-g64` through `mutl3y-review-20260504-g71`
- Archived Mutl3y recovery history also lives under `archive/`:
  - `mutl3y-recovery-20260503-mypy-baseline`
  - `mutl3y-recovery-20260503-orphaned-workflow-gate`

## Gilfoyle Review History

- Completed superseded Gilfoyle review cycles are archived out of the active root.
- Archived Gilfoyle review history lives under `archive/`:
  - `gilfoyle-review-20260501-g35` through `gilfoyle-review-20260501-g46`
  - Earlier archived Gilfoyle review material also remains authoritative history there.

## Architecture And Historical Design Plans

- `architecture-extensibility-review-20260421`
  - Still marked active and retained as a top-level architecture review surface.
- `archive/`
  - Archived and older plan material.

## Cleanup Policy

- Safe to remove:
  - `*.parse-error.bak`
  - editor backup files
  - other transient repair leftovers that are not named by any active `plan.yaml`
- Keep intact:
  - every `plan.yaml`
  - every `findings.yaml`
  - `.mutl3y-lessons/`
  - `archive/`
  - per-plan artifacts referenced from active plans
- Prefer compression or archival over deletion for large completed-plan artifacts.
- Prefer archival out of the active `docs/plan` root for completed workflow
  run directories once closure evidence is retained and no resume path is
  still active.
- Prefer archival out of the active `docs/plan` root for completed superseded
  Mutl3y review cycles once a newer active Mutl3y resume surface exists and
  any unresolved findings are explicitly carried forward.
- Prefer archival out of the active `docs/plan` root for completed superseded
  Gilfoyle review cycles once a newer completed cycle exists and no active
  resume path depends on the older directory remaining top-level.

## Lessons Surface

- `.mutl3y-lessons/`
  - Canonical lessons and review-history rollup surface for the current naming scheme.

## Mutl3y Improvement Signals

- Repeated workflow friction centers on missing required artifacts, brittle manual ledger edits, and repeated fixture-warning cleanup slices.
- A repo-local plan contract validator now exists at `scripts/validate_mutl3y_plan_contract.py` and currently passes across all 8 Mutl3y workflow `plan.yaml` files with phase-aware artifact checks.
- A repo-local authoring guide now exists at `docs/plan/mutl3y-workflow-authoring.md`.
- A repo-local stateless-marker warning guardrail now lives in `src/prism/tests/test_t2_04_stateless_marker.py` for the recurring warning-prone registry cluster.
- A repo-local execution-trace helper now exists at `scripts/record_execution_trace.py` for deterministic checkpoint and barrier-recovery updates.
- The execution-trace helper now supports `--validate-log` to emit repo-local PASS/FAIL evidence after each trace write.
- Workflow prompt surfaces now standardize `record_execution_trace.py --validate-log` usage for real or interruption-prone runs.
