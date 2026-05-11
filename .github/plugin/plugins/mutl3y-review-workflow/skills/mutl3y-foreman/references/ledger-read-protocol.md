# Ledger Read Protocol

Use this file for normal operation. Do not load ledger schemas unless you are editing ledger files.

Default memory directory: `docs/plan/.mutl3y-lessons`. This is the canonical learned-memory store for this review loop.

## Review Subagents

Before flagging anything, read only:

- `docs/plan/.mutl3y-lessons/digest.yaml`
- `docs/plan/.mutl3y-lessons/import-graph.json`
- a role-scoped slice derived from `docs/plan/.mutl3y-lessons/architecture-graph.json`

Fallback to raw ledger files only if `digest.yaml` is missing.

Scouts must apply `do_not_re_flag` and `active_lessons` before writing observations. If a candidate matches a do-not-re-flag entry but appears newly valid, record it as `needs_recheck` with the closure entry cited; do not promote it directly.

## Orchestrator

- Do not rewrite persistent ledger files during review or fix waves.
- Phase 7 is the only normal persistent ledger-write phase, after a green gate or explicitly accepted closure state.
- Write learning candidates to phase artifacts during P0-P6; promote them to `.mutl3y-lessons` only in P7.
- Read `model-usage-rollup.yaml` before first dispatch and after any phase with route failures.
- Regenerate `import-graph.json` only when source mtimes require it.
- Refresh `architecture-graph.json` only when source mtimes or architecture-review triggers require it.
- Regenerate `digest.yaml` last, after lessons, closed findings, focus-axis, and model rollup are updated.

## Why

This keeps review context small. One digest read plus one bounded graph slice is much cheaper than reading multiple raw history files and rediscovering the same architecture facts every cycle.
