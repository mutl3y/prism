# Memory Hygiene

Use this during Phase 7 when promoting or reviewing durable learning.

## Goal

Keep `.mutl3y-lessons` useful as a compact retrieval layer, not a graveyard of
never-rechecked prompt rules.

## Hygiene Rules

- Favor the smallest durable rule that changes future behavior.
- Mark lessons that are replaced by newer rules with `superseded_by`.
- Track when a lesson was last confirmed by adding
  `last_confirmed_cycle: gN` when the evidence supports it.
- Add `staleness_review_due: gN` when the lesson depends on tooling,
  model-routing, or workflow structure that may drift.
- If two durable lessons conflict, do not keep both active without an explicit
  precedence note.

## Phase 7 Review

Before final promotion, review any new or touched lesson for:

- duplicate coverage
- stale routing or prompt assumptions
- superseded historical wording
- missing evidence path

When a lesson is stale but still historically useful, downgrade it from active
digest material instead of deleting the historical record.
