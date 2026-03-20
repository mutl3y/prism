# TODO / Roadmap

## 1) Enrich documentation realism from role content

- [x] Expand the bundled `mock_role` to resemble a production role:
  - [x] Add richer defaults and vars with typed patterns and overrides
  - [x] Add multiple task paths (setup/deploy/validate/rollback)
  - [x] Add handlers, templates, files, molecule/test scaffolding
  - [x] Add realistic metadata (`meta/main.yml`, requirements, tags, platforms)
- [x] Improve generated README richness from discovered role signals:
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
- [x] Add guardrails:
  - [x] Timeout and size limits
  - [x] Shallow clone support
  - [x] Sparse/partial clone optimization for repo sub-path scans (with shallow fallback)
  - [x] Clear errors for private/missing repos
- [x] Add tests for GitHub intake flow (mocked clone + fixture repos)

## 4) Prepare for iterative learning loop (later phase)

- [x] Run pilot sample-repo learning pass and capture unmapped style headings report (`debug_readmes/STYLE_MISSED_SECTIONS_REPORT.md`)
- [x] Expose a stable library wrapper for external learning-loop/orchestration apps
- [x] Expose repo-url scanning through the same public library API surface
- [x] Persist extracted feature snapshots per role scan
- [x] Add batch-scan scaffolding with per-target success/failure capture
- [x] Add repo URL file ingestion and freshness-aware skipping (`--repo-url-file`, `--skip-if-fresh-days`, `--force-rescan`)
- [x] Add persisted section-title aggregation report generation (`scripts/learning_section_title_report.py`)
  - [x] Add backtick-wrapped title variant checks in section-title report output
- [x] Add LLM-based section title classification (`scripts/learning_resolve_unknowns.py`)
- [x] Add automated alias-learning workflow with subcommand-based helper (`scripts/learning_alias_helper.py`)
  - [x] `review` subcommand for triggering LLM classification
  - [x] `apply` subcommand with section-level thresholds (`--min-section-total`)
  - [x] `export-aliases` for DB → YAML dump
  - [x] `merge-aliases` for canonical alias integration
  - [x] Supporting utilities: `rename-section`, `suggest-canonical`, `apply-renames`, `apply-display-titles`
- [x] Track before/after doc quality metrics
  - Schema: per-snapshot docs (target, timestamp, variable_count, resolved_count, confidence_avg, ambiguity_count)
  - Persist quality snapshots alongside section snapshots
  - Compare consecutive snapshots for quality deltas
- [x] Add optional feedback loop for future ranking/tuning of generated sections
  - Track user feedback signals: section quality ratings, title helpfulness, content accuracy
  - Design ranking model: combine coverage %, confidence, feedback score, and frequency
  - Optional: integrate with learning_section_title_report.py for title-ranking feedback

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
- [x] Explore discovery from documented README inputs (variable tables in existing role READMEs)

## 7) Style-guide demo refresh workflow

- [x] Clear all generated review/demo artifacts before style comparison runs
- [x] Use available style guides to generate multiple mock-role demos for side-by-side style review
- [x] Group saved source/demo artifacts into style-source folders for easier comparison

## 8) Refine style-guide fidelity

- [x] Reduce remaining differences between source guide prose patterns and generated output structure
- [x] Expand style-aware rendering for additional source-specific sections when helpful
  - [x] Preserve source variable-section intro text when rendering simple lists and nested bullets
  - [x] Detect and render markdown-table variable sections from style guides

## 10) Evolve local style/policy source resolution

- [x] Ship a local default style guide source markdown with the package
- [x] Add `--style-guide-skeleton` mode to generate section/order-only README scaffolds
- [x] Resolve skeleton style source from cwd `STYLE_GUIDE_SOURCE.md` before bundled fallback
- [x] Support cwd policy overlay via `./.prism_patterns.yml`
- [x] Add phased mutable-data resolution for Linux hosts (user-level XDG path and optional system path)
- [x] Add env var precedence options for style/policy sources
- [x] Add explicit CLI-path options for style/policy sources

## 11) Close analysis coverage gaps and failure modes

- [x] Priority 1: Make scan scope and limitations explicit in docs:
  - [x] Add explicit scan-scope section in README
  - [x] Document known limitations and high-risk edge cases in README
  - [x] Add scanner-report summary block that surfaces unresolved/ambiguous findings by category
- [x] Priority 2: Expand variable source coverage beyond current defaults-focused heuristics:
  - [x] Ensure consistent coverage for `defaults/`, `vars/`, and `meta/` variable signals
  - [x] Track `include_vars` usage across static and role-relative include paths
  - [x] Track `set_fact` definitions with confidence labels (static vs dynamic)
  - [x] Surface role parameter inputs and task-level defaults when statically detectable
  - [x] Add explicit provenance metadata per variable (source file, line, confidence)
- [x] Priority 3: Reduce false confidence in generated output:
  - [x] Add uncertainty annotations where source/provenance cannot be resolved
  - [x] Add README notes for precedence-sensitive or conditional defaults
  - [x] Add scanner-report counters for unresolved/ambiguous variables
- [x] Priority 4: Improve template parsing robustness:
  - [x] Replace/augment regex-based extraction with a Jinja2 AST-first path (`jinja2.Environment.parse`)
  - [x] Add focused tests for nested/default-filter AST handling, scope filtering, regex fallback, and duplicate suppression
  - [x] Add broader fixtures for macros/custom filters/tests and more complex control flow
  - [x] Gracefully degrade to “unresolved expression” or non-literal markers instead of omitting values
    - [x] Fall back to AST name collection when Jinja introspection fails on unsupported filters
- [x] Priority 5: Cover known edge cases:
  - [x] Role dependencies and dependency-provided variables
  - [x] Variable precedence interactions and override chains
  - [x] Templated filenames and dynamic include paths
  - [x] Conditional includes and task-path indirection
  - [x] Detect non-`ansible.*` collection usage and flag missing declarations in README/meta metadata
- [x] Priority 6: CLI/reporting ergonomics for analysis control:
  - [x] Verbose mode (`-v/--verbose`)
  - [x] Markdown/HTML output formats
  - [x] Add dry-run mode (scan and report intent without writing output files)
  - [x] Add JSON output format for machine-readable scanner data
  - [x] Add exclusion flags for directories/files/patterns (for example templates/tests/paths)
  - [x] Add tests covering new dry-run and JSON behaviors
  - [x] Add tests covering exclusion behaviors

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
- [x] Re-run coverage after each batch and update `docs/completed_plans/COVERAGE_WORKOFF_PLAN.md`
- [x] Optional stretch: add `--cov-fail-under` threshold to `tox` once a stable baseline is agreed
- [x] `cli.py` pushed to 100% line and branch coverage
- [x] Optional stretch: one additional micro-batch targeting remaining defensive exception branches in `scanner.py` to push toward 92%+ line / 88%+ branch

## 12) Next-phase feature expansion (assessed additions)

- [x] Add collection-root scanning mode (parse `galaxy.yml`, enumerate `roles/`, generate collection-level README plus per-role docs)
- [x] Parse and render Molecule scenario details (`driver`, `platforms`, `verifier`) in README testing sections
- [x] Add optional detailed task/handler catalog mode (task name/module/when and handler action tables)
- [x] Add PDF output path (`--format pdf`) via Markdown -> HTML -> PDF conversion fallback strategy
- [x] Add CI docs-generation starter workflow templates and docs (GitHub Actions / GitLab examples)

## 13) Design-goal expansion: role/collection docs + plugin coverage

Execution gates (recommended order):

- [x] Gate 1: Ship additive `plugin_catalog` payload scaffold with empty categories and summary counters
- [x] Gate 2: Ship filter-plugin AST extraction with confidence + failure reporting
- [x] Gate 3: Ship full plugin-directory inventory coverage for all required plugin types
- [x] Gate 4: Ship collection README redesign using payload-only rendering
- [x] Gate 5: Ship CLI UX redesign (`role`, `collection`, `repo`, `completion`) without compatibility shims
- [x] Gate 6: Ship context-flag naming migration + generated Bash completion + docs/demo refresh

- [x] Redesign CLI UX around subcommands
  - [x] Introduce `prism role` for local role documentation workflows
  - [x] Introduce `prism collection` for collection-root documentation workflows
  - [x] Introduce `prism repo` for repository intake and remote scan workflows
  - [x] Introduce `prism completion bash` for generated shell completion output
  - [x] Do not keep top-level legacy invocation paths; require subcommand mode (`role`, `collection`, `repo`, `completion`)
  - [x] Route subcommands through shared helpers to avoid duplicating option wiring and scan logic
  - [x] Re-scope help output so role/collection/repo users only see relevant options
- [x] Reframe variable context UX and naming
  - [x] Add `--group-vars-context` (or generalized `--vars-context-path`) as primary context flag
  - [x] Keep `--vars-seed` as backward-compatible alias with deprecation messaging
  - [x] Ensure external context is labeled as non-authoritative in output metadata/docs
- [x] Add CLI shell completion support
  - [x] Decide delivery model: generated-on-demand subcommand (not a checked-in static script)
  - [x] Add generated-on-demand Bash completion via `prism completion bash`
  - [x] Generate completion from the live parser/subparser structure so it stays aligned with parser changes and aliases
  - [x] Decide whether completion should depend on `argcomplete` or use a project-local generator
  - [x] Document installation/usage for local shells and CI/devcontainer environments
- [x] Expand collection scan payload beyond role roster/dependencies
  - [x] Add collection plugin inventory model with typed records (type/path/symbols/summary/confidence)
  - [x] Add stable `plugin_catalog` payload contract with `schema_version`, `summary`, `by_type`, and `failures`
  - [x] Keep `by_type` keys present even when plugin categories are empty
  - [x] Add typed schema definitions in code (`PluginRecord`, `PluginCatalog`, `PluginScanFailure`)
  - [x] Capture plugin coverage for `plugins/filter`, `plugins/modules`, `plugins/lookup`, `plugins/inventory`, `plugins/callback`, `plugins/connection`, `plugins/strategy`, `plugins/test`, `plugins/doc_fragments`, `plugins/module_utils`
  - [x] Keep output deterministic and bounded for stable README diffs
- [x] Implement filter plugin extraction depth
  - [x] Parse common `FilterModule.filters()` patterns via AST-first extraction
  - [x] Extract filter names from dict literals and simple named-dict indirection in `filters()`
  - [x] Capture filter function docstrings for short descriptions when available
  - [x] Add fallback heuristics and confidence labels for partial extraction
  - [x] Render concise filter capability summaries in collection output
- [x] Implement broader Python AST extraction for collection plugins
  - [x] Extract module plugin `DOCUMENTATION`/`EXAMPLES`/`RETURN` blocks when statically assigned
  - [x] Extract class/method capability hints for lookup/inventory/callback/strategy plugins
  - [x] Record extraction method and confidence in plugin records (`ast`, `fallback`, `mixed`)
- [x] Redesign collection README generation
  - [x] Replace current index-like markdown with structured sections (metadata, dependencies, roles, plugins, filters, failures/limitations)
  - [x] Add per-role quick stats links in collection README
  - [x] Add bounded rendering limits and overflow notes for large plugin catalogs
  - [x] Ensure generated collection docs remain readable for large collections
- [x] Align role README behavior to role-source truth
  - [x] Keep role variable sections tied to role-local/static sources
  - [x] Avoid treating inventory-owned `group_vars` as discovered role source of truth
  - [x] Improve detailed task/handler catalog with compact parameter details
- [x] Add test and fixture coverage for new collection/plugin paths
  - [x] Add collection fixtures with representative plugin trees and sample filter plugins
  - [x] Add fixture cases for syntax-failing plugin files and dynamic/indirect filter maps
  - [x] Add scanner/API/CLI/render tests for plugin inventory and filter extraction
  - [x] Add payload contract tests for `plugin_catalog` shape and deterministic ordering
  - [x] Add compatibility tests for context-flag alias and deprecation path
- [x] Update docs, demos, and migration notes
  - [x] Update README/docs examples to subcommand form (`prism role`, `prism collection`, `prism repo`, `prism completion bash`)
  - [x] Update README examples to new context-flag naming
  - [x] Add README/docs section for `prism completion bash` generation and installation
  - [x] Update CLI help text and limitations language
  - [x] Refresh demo scenarios to include collection plugin/filter documentation output
