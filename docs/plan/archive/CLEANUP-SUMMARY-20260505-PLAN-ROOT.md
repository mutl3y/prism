# Cleanup Summary — 5 May 2026

Scope: top-level `docs/plan` root reduction and archive normalization
Status: COMPLETED

## What Changed

Archived closed Mutl3y review and recovery plan directories out of the active
`docs/plan` root, keeping only active plans and the latest closed Gilfoyle and
Mutl3y reference surfaces visible at top level.

## Archived In This Pass

- `mutl3y-recovery-20260503-mypy-baseline`
- `mutl3y-recovery-20260503-orphaned-workflow-gate`
- `mutl3y-review-20260503-g58`
- `mutl3y-review-20260503-g59`
- `mutl3y-review-20260503-g60`
- `mutl3y-review-20260503-g61`
- `mutl3y-review-20260503-g62`
- `mutl3y-review-20260503-g63`
- `mutl3y-review-20260504-g65`
- `mutl3y-review-20260504-g66`
- `mutl3y-review-20260504-g67`
- `mutl3y-review-20260504-g68`
- `mutl3y-review-20260504-g69`
- `mutl3y-review-20260504-g70`
- `mutl3y-review-20260504-g71`

## Retained Top-Level Surfaces

- `gilfoyle-review-20260501-g46`: active in-progress Gilfoyle resume surface
- `gilfoyle-review-20260502-g47`: latest closed Gilfoyle reference surface
- `mutl3y-review-20260504-g64`: active Mutl3y review surface
- `mutl3y-review-20260504-g72`: latest closed Mutl3y reference surface
- `mutl3y-review-20260504-g73`: current implementation-bearing Mutl3y surface
- `mutl3y-review-workflow-realrun-20260502`: active workflow resume surface
- `mutl3y-review-workflow-trace-drill-20260502`: paused reference drill
- `20260425-readme-renderer-plugin-design`: design-only retained reference
- `architecture-extensibility-review-20260421`: still-active architecture review surface

## Supporting Helper

- `scripts/archive_completed_review_plans.py`
  - Now recognizes the repo's closed review-plan statuses: `complete`, `completed`, and `completed_checkpoint`.
