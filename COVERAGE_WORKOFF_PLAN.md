# Coverage Workoff Plan

Baseline captured on 2026-03-13 from `tox` using `pytest-cov`.

## Current snapshot

- Total line coverage: 86.6%
- Total branch coverage: (branch data in coverage.xml — full report from `tox`)
- Coverage artifact: `debug_readmes/coverage.xml`

Per-file snapshot:

- `cli.py`: **100% line, 100% branch** ✅
- `scanner.py`: 84.4% line, ~85.7% branch (remaining gaps are defensive/uncommon branches)

All 57 tests passing as of 2026-03-13.

Progress note:

- Batch 1 low-risk coverage tests are now in place.
- The first interim target of 50% total line coverage has been reached.
- Batch 2 scanner robustness tests are now in place.
- The second interim target has been reached for `cli.py` branch coverage and `scanner.py` line coverage.
- Batch 3 style-guide rendering tests are now in place.
- The later target of 60%+ total line coverage has now been exceeded.
- Batch 4 comparison and direct render-path tests are now in place.
- Branch coverage has now moved into the mid-70% range overall.
- Additional helper/edge-branch tests are now in place for CLI and scanner internals.
- Overall coverage is now beyond the 85% line and 80% branch target.
- Bug fixed: `_save_style_comparison_artifacts` no longer double-nests style directory when output is already inside the style folder.

## Biggest current gaps

### 1. Remaining gaps are now narrow and low risk

Most uncovered logic is now in small defensive branches and uncommon fallback paths.

Current likely candidates:

- defensive exception branches around file I/O and subprocess boundaries
- uncommon metadata/detail combinations not seen in fixtures
- some branch-only paths in helper conditionals where behavior is already straightforward

### 2. `cli.py` and `scanner.py` are now both in high coverage range

- `cli.py` is above 98% line / 92% branch coverage
- `scanner.py` is above 90% line / 85% branch coverage

## Suggested work batches

### Batch 1 — cheap wins

Goal: improve confidence quickly without changing production code.

Status: complete.

Completed tests:

1. `cli._clone_repo()` timeout and command failure paths
2. `cli._save_style_comparison_artifacts()` missing file and self-copy scenarios
3. invalid cloned repo role subpath handling in `cli.main()`
4. `run_scan()` invalid comparison path and invalid style-guide path
5. `run_scan(output_format='html')` success path
6. `run_scan()` HTML fallback when `markdown` import is unavailable

Observed impact: total line coverage rose from 30.3% to 55.1% and total branch coverage rose from 18.2% to 39.8%.

### Batch 2 — scanner robustness

Status: complete.

Add tests for:

1. roles without `tasks/main.yml`
2. task includes using dict form with `file` and `_raw_params`
3. dynamic include paths that should be ignored
4. unreadable or malformed YAML files returning safe defaults
5. empty defaults/vars/meta/requirements files

Observed impact: total line coverage rose from 55.1% to 58.0% and total branch coverage rose from 39.8% to 43.4%.

Completed tests also covered sparse-role content collection and zero-task feature extraction.

### Batch 3 — style-guide branches

Status: complete.

Add tests for:

1. setext-style README headings
2. unknown guide sections being retained
3. `license`, `author`, `sponsors`, and `faq` section render paths
4. roles with no variables for style-guided rendering
5. style guides without recognized variable formatting

Observed impact: total line coverage rose from 58.0% to 74.3% and total branch coverage rose from 43.4% to 61.6%.

Completed tests also covered simple-list variable rendering fallback and setext-based unknown section retention.

### Batch 4 — comparison and output conversion

Status: complete.

Add tests for:

1. `_compute_quality_metrics()` with sparse and rich roles
2. `build_comparison_report()` with measurable deltas
3. HTML fallback path when `markdown` import is unavailable
4. non-`.md` output suffix handling for generated demo artifacts

Observed impact: total line coverage rose from 74.3% to 84.1% and total branch coverage rose from 61.6% to 75.4%.

Completed tests also covered:

- `_render_guide_section_body()` fallback branches for comparison, task summary, example usage, role contents, features, and default filters
- direct `render_readme()` branches with `write=False`, template override, and style-guide rendering
- `run_scan()` role-name override for sparse roles

## Recommended stopping points

Practical interim targets:

- first target: 50% total line coverage ✅
- second target: 70% coverage for `cli.py` branches and 40% line coverage for `scanner.py` ✅
- later target: 60%+ total line coverage after scanner/style-guide batches ✅

Next practical target:

- push remaining helper and CLI edge branches high enough to reach ~85% total line coverage and ~80% total branch coverage ✅

Stretch target (optional):

- reach 92%+ line and 88%+ branch coverage while preserving test maintainability

Likely next candidates:

- additional fixture variants for unusual metadata and requirements shapes
- explicit tests for defensive error branches where dependency/file failures are simulated

## Notes

- This plan is intentionally incremental; it prioritizes stable regression tests over forcing a hard coverage gate immediately.
- Once the low-risk branches are covered, a minimum coverage threshold can be added to `tox` if desired.
