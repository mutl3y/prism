# Phase 0 Spillage Summary

Primary spillover is concentrated in two places: standalone historical files at the top of docs/plan and execution-heavy residue under g84-remediation-mutl3y-cycle-20260509. The safest first-pass archive move is the top-level 20260507 summary/status/closure trio plus the g84 wave, closure, and artifact subtrees.

I did not mark post-g84-arch-refactor-20260511 for archive. Its root plan is still marked ACTIVE, and its implementation-plan documents are still live references for ongoing architecture and multi-platform work. Within that area, the phase summaries are complete, but they read as current-plan evidence rather than abandoned spillover.

One file is worth treating as stale even though it is dated today: docs/plan/HOUSEKEEPING_AND_ERROR_ENVELOPE_SUMMARY_20260511.md claims housekeeping and the error-envelope review are complete, which conflicts with the still-active post-g84 plan and the new plugin-implementation planning plan. That makes it a good archive candidate, not a keep-active control file.

Mixed-content caution: the g84 directory is mostly historical, but it still contains at least one explicitly in-progress planning file (q3-init6-type-improvement-strategy.yaml). Archive the obvious artifact subdirectories and closure/status files first, then split or re-home any still-live planning documents before archiving the remainder of the root.
