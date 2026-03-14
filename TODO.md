# TODO / Roadmap

## 1) Enrich documentation realism from role content

- [ ] Expand the bundled `mock_role` to resemble a production role:
  - [ ] Add richer defaults and vars with typed patterns and overrides
  - [ ] Add multiple task paths (setup/deploy/validate/rollback)
  - [ ] Add handlers, templates, files, molecule/test scaffolding
  - [ ] Add realistic metadata (`meta/main.yml`, requirements, tags, platforms)
- [ ] Improve generated README richness from discovered role signals:
  - [x] Role purpose summary + capability bullets
  - [x] Inputs/variables table with inferred defaults and references
  - [x] Task/handler/module usage summaries
  - [x] Basic examples inferred from role structure

## 2) Support scanning a local role folder as a reference target

- [x] Add CLI option(s) to compare bundled mock output vs a local role path
- [x] Add role-quality scoring heuristics (coverage/completeness/readability)
- [x] Include comparison notes in generated review README

## 3) Add GitHub role-source intake for README generation and learning

- [x] Add CLI support for GitHub role sources:
  - [x] Accept repo URL and optional branch/tag
  - [x] Clone to temp workspace and scan safely
  - [x] Generate `REVIEW_README.md` (or user-specified output) from cloned role
  - [x] Validate end-to-end against `https://github.com/mutl3y/ansible_port_listener` for local testing
- [ ] Add guardrails:
  - [x] Timeout and size limits
  - [x] Shallow clone support
  - [x] Clear errors for private/missing repos
- [x] Add tests for GitHub intake flow (mocked clone + fixture repos)

## 4) Prepare for iterative learning loop (later phase)

- [ ] Persist extracted feature snapshots per role scan
- [ ] Track before/after doc quality metrics
- [ ] Add optional feedback loop for future ranking/tuning of generated sections

## 5) Add README style-guide support

- [x] Allow a local README to guide generated section order and heading style
- [x] Allow a README inside a cloned repo to guide generated section order and heading style
- [x] Keep scanner-derived content as the source of truth while reusing guide structure
- [x] Map common guide sections beyond the core defaults (testing, FAQ, contributing, sponsors, license/author)
- [x] Adapt variable rendering to source guide style patterns (for example YAML blocks and nested bullets)

## 6) Revisit variable discovery after style-guide support

- [x] Improve variable extraction for GitHub-scanned roles where defaults/vars are sparse or indirect
- [x] Discover variables from `include_vars` task references (static paths within the role)
- [x] Discover computed variable names from `set_fact` tasks
- [ ] Explore discovery from documented README inputs (variable tables in existing role READMEs)

## 7) Style-guide demo refresh workflow

- [x] Clear all generated review/demo artifacts before style comparison runs
- [x] Use available style guides to generate multiple mock-role demos for side-by-side style review
- [x] Group saved source/demo artifacts into style-source folders for easier comparison

## 8) Refine style-guide fidelity

- [ ] Reduce remaining differences between source guide prose patterns and generated output structure
- [ ] Expand style-aware rendering for additional source-specific sections when helpful

## 10) Evolve local style/policy source resolution

- [x] Ship a local default style guide source markdown with the package
- [x] Add `--style-guide-skeleton` mode to generate section/order-only README scaffolds
- [x] Resolve skeleton style source from cwd `STYLE_GUIDE_SOURCE.md` before bundled fallback
- [x] Support cwd policy overlay via `./.ansible_role_doc_patterns.yml`
- [x] Add phased mutable-data resolution for Linux hosts (user-level XDG path and optional system path)
- [x] Add env var precedence options for style/policy sources
- [ ] Add explicit CLI-path options for style/policy sources

## 11) Close analysis coverage gaps and failure modes

- [ ] Priority 1: Make scan scope and limitations explicit in docs:
  - [x] Add explicit scan-scope section in README
  - [x] Document known limitations and high-risk edge cases in README
  - [ ] Add scanner-report summary block that surfaces unresolved/ambiguous findings by category
- [ ] Priority 2: Expand variable source coverage beyond current defaults-focused heuristics:
  - [ ] Ensure consistent coverage for `defaults/`, `vars/`, and `meta/` variable signals
  - [ ] Track `include_vars` usage across static and role-relative include paths
  - [ ] Track `set_fact` definitions with confidence labels (static vs dynamic)
  - [ ] Surface role parameter inputs and task-level defaults when statically detectable
  - [ ] Add explicit provenance metadata per variable (source file, line, confidence)
- [ ] Priority 3: Reduce false confidence in generated output:
  - [ ] Add uncertainty annotations where source/provenance cannot be resolved
  - [ ] Add README notes for precedence-sensitive or conditional defaults
  - [ ] Add scanner-report counters for unresolved/ambiguous variables
- [ ] Priority 4: Improve template parsing robustness:
  - [x] Replace/augment regex-based extraction with a Jinja2 AST-first path (`jinja2.Environment.parse`)
  - [x] Add focused tests for nested/default-filter AST handling, scope filtering, regex fallback, and duplicate suppression
  - [ ] Add broader fixtures for macros/custom filters/tests and more complex control flow
  - [ ] Gracefully degrade to “unresolved expression” or non-literal markers instead of omitting values
- [ ] Priority 5: Cover known edge cases:
  - [ ] Role dependencies and dependency-provided variables
  - [ ] Variable precedence interactions and override chains
  - [ ] Templated filenames and dynamic include paths
  - [ ] Conditional includes and task-path indirection
- [ ] Priority 6: CLI/reporting ergonomics for analysis control:
  - [x] Verbose mode (`-v/--verbose`)
  - [x] Markdown/HTML output formats
  - [x] Add dry-run mode (scan and report intent without writing output files)
  - [x] Add JSON output format for machine-readable scanner data
  - [ ] Add exclusion flags for directories/files/patterns (for example templates/tests/paths)
  - [x] Add tests covering new dry-run and JSON behaviors
  - [ ] Add tests covering exclusion behaviors

## 9) Raise automated test coverage

- [x] Add `pytest-cov` coverage reporting to `tox`
- [x] Capture a baseline coverage report for the current codebase
- [x] Cover Batch 1 low-risk paths:
  - [x] clone timeout and clone failure handling in `cli._clone_repo()`
  - [x] missing/invalid style guide paths in `cli._save_style_comparison_artifacts()`
  - [x] invalid repo role subpaths in `cli.main()`
  - [x] HTML output path handling in `run_scan()`
  - [x] markdown import fallback branch in `run_scan()` when HTML conversion dependencies are unavailable
  - [x] invalid comparison and style-guide paths in `run_scan()`
- [x] Cover remaining CLI and artifact edge paths:
  - [x] extra `cli._repo_name_from_url()` parsing branches
  - [x] non-markdown generated demo artifact variants in `cli._save_style_comparison_artifacts()` / `cli.main()`
- [x] Cover Batch 2 scanner robustness paths:
  - [x] missing `tasks/` and fallback task entrypoint discovery in `scanner._collect_task_files()`
  - [x] YAML parse failures and dynamic include targets in `scanner._load_yaml_file()` / `scanner._resolve_task_include()`
  - [x] include target parsing for dict-style `file` / `_raw_params` task includes
  - [x] empty or malformed metadata/requirements/defaults files in `load_meta()`, `load_requirements()`, and `build_variable_insights()`
  - [x] sparse-role collection and zero-task feature extraction in `collect_role_contents()` / `extract_role_features()`
- [x] Cover Batch 3 style-guide rendering branches:
  - [x] setext heading parsing and unknown section retention in `parse_style_readme()` / `_render_readme_with_style_guide()`
  - [x] `license`, `author_information`, `license_author`, `sponsors`, `faq_pitfalls`, and empty-variable branches in `_render_guide_section_body()`
  - [x] simple-list fallback rendering in `_render_role_variables_for_style()`
- [x] Cover Batch 4 rendering and reporting branches:
  - [x] quality/comparison helpers in `_compute_quality_metrics()` and `build_comparison_report()`
  - [x] default fallback branches in `_render_guide_section_body()` for comparison, task summary, example usage, role contents, and features
  - [x] direct render paths in `render_readme()` and `run_scan()`
- [x] Cover remaining high-value gaps:
  - [x] remaining `cli.py` branches in repo-name parsing and artifact copy edge cases
  - [x] remaining `scanner.py` helper branches around `_describe_variable()`, `_detect_task_module()`, and metadata/detail render combinations
- [x] Re-run coverage after each batch and update `COVERAGE_WORKOFF_PLAN.md`
- [ ] Optional stretch: add `--cov-fail-under` threshold to `tox` once a stable baseline is agreed
- [x] `cli.py` pushed to 100% line and branch coverage
- [ ] Optional stretch: one additional micro-batch targeting remaining defensive exception branches in `scanner.py` to push toward 92%+ line / 88%+ branch
