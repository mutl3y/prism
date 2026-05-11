# Context Degradation Playbook

Use this when a cycle starts to lose continuity even though artifacts exist.

Treat degradation as an execution event, not as vague model weakness.

## Triggers

Record a degradation event when any of these happens inside one phase:

- live context is clearly beyond the active phase, owned file set, and short
  failure slice
- the same file, log, or artifact excerpt must be re-read twice because the
  prior summary was not enough
- a summary artifact is contradicted by live source twice
- a worker returns on-topic but low-signal output twice after one prompt
  tightening pass
- progress stalls because the foreman is carrying too many concurrent worker
  summaries at once

## Recovery Order

1. Stop narration and mark the phase `STALL` or `repeat`.
2. Offload long output to disk if it is not already persisted.
3. Reduce live context to current phase, active finding slice, owned file set,
   artifact paths, and one short failure excerpt.
4. If continuity still feels weak, create or refresh an anchored compaction
   summary using `anchored-compaction.md`.
5. Re-run the next action from repo-backed state, not from conversational
   recollection.

## Required Recording

When a degradation event changes routing, resume strategy, or barrier outcome,
record it in the active phase artifact or execution trace with:

- `degradation_trigger`
- `recovery_action`
- `affected_workers`
- `artifact_anchor`
- `next_clean_resume_point`

Keep the note compact. Do not paste long logs.

## Foreman Rules

- Do not treat repeated re-reading as harmless noise.
- Do not keep layering corrections on top of a weak summary artifact.
- Prefer a clean restart from artifact-backed state over carrying a bloated
  context forward.
