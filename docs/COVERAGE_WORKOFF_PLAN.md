# Coverage Workoff Plan

Current snapshot updated on 2026-03-15 from local `tox`.

## Current snapshot

- Test status: `176 passed`
- Total line coverage: `82.56%`
- Coverage gate: `--cov-fail-under=80` (passing)
- Coverage artifact: `debug_readmes/coverage.xml`

Per-file snapshot from the latest run:

- `src/prism/cli.py`: 88.0%
- `src/prism/pattern_config.py`: 68.8%
- `src/prism/scanner.py`: 81.4%
- `src/prism/style_guide.py`: 81.7%

## Status summary

- The test suite has expanded significantly and now covers role-path and repo-url learning-loop scaffolding paths.
- The project remains above the enforced minimum coverage threshold.
- Current gaps are concentrated in larger scanner/pattern branches and defensive fallback paths.

## Next practical targets

1. Raise `pattern_config.py` coverage by exercising override precedence and error-handling branches more thoroughly.
2. Add focused scanner fixtures for unresolved-variable edge cases that still dominate uncovered lines.
3. Keep `tox` as the source of truth and update this file only when snapshot values materially change.

## Notes

- This plan tracks practical maintenance goals, not a hard requirement to maximize every defensive branch.
- Any future threshold increase should follow measured stability across a few consecutive runs.
