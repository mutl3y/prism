# Plan Inventory

Updated: 2026-05-11

## Active Plans

- [g84-remediation-mutl3y-cycle-20260509](g84-remediation-mutl3y-cycle-20260509) is the completed reference cycle for consolidation and closure evidence.
- [post-g84-arch-refactor-20260511](post-g84-arch-refactor-20260511) is the active post-g84 architecture follow-up surface.
- [plugin-implementation-20260511](plugin-implementation-20260511) is the active multi-platform plugin implementation and hygiene plan.

## Active Plan Surfaces

- [FUTURE_INITIATIVES.md](FUTURE_INITIATIVES.md) tracks deferred and upcoming initiative sequencing.
- [future-initiatives](future-initiatives) stores initiative plans under active review before promotion to a primary execution plan.
- [mutl3y-lessons-g74-g84-consolidated.md](mutl3y-lessons-g74-g84-consolidated.md) is the consolidated lesson rollup.
- [.mutl3y-lessons](.mutl3y-lessons) remains the canonical lessons and review-history surface.

## Archive Structure

Top-level archive groups currently retained:

- [archive/mutl3y-cycles-g74-g84](archive/mutl3y-cycles-g74-g84)
- [archive/architecture-reviews](archive/architecture-reviews)
- [archive/plugin-implementation-20260511-phase0](archive/plugin-implementation-20260511-phase0)
- [archive/20260425-readme-renderer-plugin-design](archive/20260425-readme-renderer-plugin-design)
- [archive/gilfoyle-remediation-20260423](archive/gilfoyle-remediation-20260423)
- [archive/README.md](archive/README.md)

## Cleanup Policy

- Move closed execution slices to archive groups when no active plan depends on them.
- Keep only active plans and active roadmap/lessons surfaces at docs/plan top level.
- Keep detailed execution history in git and grouped archive folders rather than re-expanding top-level plan clutter.
