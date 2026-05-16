# Phase 4 Decide

Purpose:

- Choose the next execution path from graded or investigated findings.
- Slice implementation work into disjoint owned-file waves.

Source of truth:

- `findings.yaml`
- The Phase 1 grading artifact
- Any Phase 3 synthesis artifact
- `mutl3y-artifacts/phase4/` decision artifacts and wave-shaping summaries

Rules:

- Present mutually exclusive options before committing to the next phase.
- Record the decision in `findings.yaml` before dispatching builders.
- Persist decision summaries and wave-shaping notes under `mutl3y-artifacts/phase4/`.
- Run the mandatory dedup and normalization pass across typing, ownership, control-flow, and graph findings before creating a builder wave.
- Slice implementation by explicit owned file sets, not by raw lane totals.
- If ownership is not disjoint, stop and re-slice before entering Phase 5.

Outcomes:

- `P4 complete -> P5`
- `carry or defer and return to planning`
- `STALL`
- `BLOCKED`
