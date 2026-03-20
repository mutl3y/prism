# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Unreleased)

- New CLI flag `--keep-unknown-style-sections` / `--no-keep-unknown-style-sections`.
- README-driven variable discovery from role `README.md` variable/input sections (including markdown tables and list formats).
- README config support for per-section content handling via `readme.section_content_modes` (`generate`, `replace`, `merge`).
- Auto-generated style sidecar `ROLE_README_CONFIG.yml` for style demo outputs when a role config is not present.
- Capture metadata for synthesized sidecars under `readme.capture_metadata` (`schema_version`, `captured_at_utc`, `style_source_path`, `truncated`).
- Optional bundled data file `section_display_titles.yml` containing human-friendly display labels for all known section IDs (used by "popular" heading render mode).
- Expanded branch-focused regression test coverage across scanner helpers, task parser helpers, CLI repo/error paths, API rendering paths, feedback loading, and output format fallback handling.
- Archived-plan index under `docs/completed_plans/README.md` covering closed workoff and schedule plans.

### Changed (Unreleased)

- Learning-loop orchestration, Postgres persistence, and related helper scripts moved to the companion add-on repository: `prism-learn`.
- Unknown style-guide sections are now kept by default during style-guided rendering.
- Style-guided variable rendering now preserves variable-section intro prose and can mirror markdown-table variable layouts.
- `readme.section_content_modes` selectors now resolve by configured `include_sections` title labels first, then aliases/canonical ids.
- Merge mode for style sections is now idempotent across repeated ingest/regenerate passes (previous generated merge payload is replaced, not repeatedly appended).
- Unknown style sections now preserve source body content when available, with fallback placeholder text only when section body is empty.
- README overview language now explicitly keeps the refracted-documentation vision as the product end goal while clarifying current static-analysis delivery boundaries.
- Completed workoff/schedule plan documents were moved into `docs/completed_plans/` as archived records.

### Fixed (Unreleased)

- Style-guide parsing now ignores fenced code blocks when detecting headings, preventing false unknown sections such as ````yaml`.
- Simple-list variable rendering now formats values as markdown-safe inline code, reducing parser/render breakage for multiline values.
- Jinja variable introspection now falls back to AST name scanning when unsupported filters are present (for example `ternary`, `to_nice_yaml`), preventing repo-scan failures.
- Synthesized style sidecar capture now applies truncation, secret-like token redaction, dedupe/sort stability, and no-op writes for unchanged files.
- Documentation links that referenced `docs/COVERAGE_WORKOFF_PLAN.md` now point to the archived plan path under `docs/completed_plans/`.

## [0.1.0] - 2026-03-15

### Added (0.1.0)

- Heading rendering mode controls for README config selectors via CLI flag `--adopt-heading-mode {canonical,style,popular}`.
- Heading rendering mode controls for README config selectors via config key `readme.adopt_heading_mode`.
- Optional tox environment `readmes` to generate demo artifacts on demand.
- Demo generation for all built-in output variants, including in-role config fixture output.
- Sparse/partial clone optimization for repo sub-path scans using `git clone --filter=blob:none --sparse` with sparse checkout targets.
- Fallback to regular shallow clone when sparse checkout setup fails.

### Changed (0.1.0)

- Default tox workflow is now focused on tests and coverage; README/demo generation moved to `tox -e readmes`.
- Test fixtures reorganized under `src/prism/tests/roles/` with a symlinked base role fixture.
- Test path usage centralized via fixture constants for easier maintenance.
- Pipeline/docs references updated to include current CLI options (`json`, `--dry-run`, `--adopt-heading-mode`).

### Fixed (0.1.0)

- Tests aligned with updated mock role metadata description output.
- Style heading behavior clarified so section selection and heading renaming can be controlled independently.
- Demo-readmes make target generation flow corrected and validated.

[Unreleased]: https://github.com/mutl3y/prism/compare/0.1.0...HEAD
[0.1.0]: https://github.com/mutl3y/prism/releases/tag/0.1.0
