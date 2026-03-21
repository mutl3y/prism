# Annotation Quality Workoff Plan

**Status**: In Progress
**Updated**: 2026-03-21

## Scope

Raise quality and consistency of marker-comment annotations (for example `# prism~runbook:`) so they are machine-parseable, reviewable, and usable as quality metrics.

## Completed in this cycle

- Added disabled annotation detection for commented-out task blocks.
- Added `disabled_task_annotations` feature counter.
- Added documentation guidance to use plain text or `key=value` hints and avoid YAML payloads in marker comments.
- Added YAML-like payload heuristic detection with annotation-level warning:
  - `format_warning: yaml-like-payload-use-key-equals-value`
- Added `yaml_like_task_annotations` feature counter.
- Added parser tests covering:
  - Disabled annotation detection.
  - YAML-like payload warning assignment.
  - YAML-like feature counter behavior.
- Surfaced annotation quality counters in scanner report markdown summary.
- Added strict-fail policy mode for YAML-like marker payloads (`.prism.yml`: `scan.fail_on_yaml_like_task_annotations`; CLI override: `--fail-on-yaml-like-task-annotations`).
- Added regression tests for scanner report rendering of annotation quality counters.
- Added README examples for valid `key=value` marker payload patterns.

## Remaining work

1. Evaluate threshold guidance for fleet reporting:
   - expected `yaml_like_task_annotations == 0`
   - expected `disabled_task_annotations` within team-defined baseline.

## Validation checklist

- Parser tests pass for annotation warning and disabled paths.
- Existing annotation extraction behavior remains backward-compatible for non-warning payloads.
- New counters are present in `extract_role_features` output.
- Scanner report summary includes annotation quality counters.
- Strict policy mode can fail scans when YAML-like marker payloads are detected.

## Risks / Notes

- YAML-like detection is heuristic and may produce occasional false positives on colon-heavy prose.
- Advisory mode remains default to avoid breaking existing repositories.
