# AGENTS

## Notable Findings (Plan Closure: gilfoyle-refactor-20260328)

- Wave 1 is fully complete (2026-03-28): data contracts, DI container, and dependency mapping are all done.
- DI baseline is intentionally lightweight and hand-crafted in src/prism/scanner_core/di.py to keep wiring explicit and testable.
- Typed contract definitions are centralized under src/prism/scanner_data/contracts.py; contract-first sequencing reduced downstream extraction risk.
- Dependency analysis artifact is documented at docs/plan/gilfoyle-refactor-20260328/dependency-graph.yaml and should be used for import-risk checks before scanner-core changes.

## Notable Findings (Plan Closure: scanner-migration-wave2-20260329)

- Wave 2 closure is complete (2026-03-29): tasks w2_c_1, w2_c_2, w2_c_1_b, w2_c_4, w2_c_3, w2_c_5, and w2_c_6 are closed.
- Closure sequencing mattered: output/reporting and contracts seams were stabilized before compatibility wrapper lifecycle actions.
- Validation gate for closure requires all three layers green together: full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: scanner-migration-wave3-20260329)

- Wave 3 mixed-bundle closure is complete (2026-03-29): tasks w3_b_01 through w3_b_07 are closed.
- `src/prism/scanner_submodules/render_reports.py` now intentionally retains only high-risk compatibility wrappers (`build_scanner_report_markdown`, `render_runbook`, `render_runbook_csv`) with deprecation warnings.
- Low/medium compatibility helpers were retired from `render_reports` and low-risk helper wrappers were retired from `scan_output_emission`; retained scan-output and scan-request wrappers remain explicit deprecation redirects to canonical modules.
- User confirmed there are no external consumers of `scanner_submodules` compatibility wrappers, enabling accelerated wrapper retirement sequencing.
- External-consumer validation for `scanner_submodules` wrappers is now an explicit unblocker for accelerated retirement decisions.
- Closure evidence standard remained unchanged and passed together: focused seam checks, full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: scanner-migration-wave4-20260329)

- Wave 4 closure is complete (2026-03-29): remaining retirement tasks for `scanner_submodules` compatibility wrappers were closed in one accelerated wave.
- User-confirmed absence of external consumers was used as the acceleration gate, allowing coordinated retirement of the remaining wrapper seams.
- Scanner runtime fallback paths to compatibility wrappers were removed; scanner execution now resolves through canonical modules for runtime behavior.
- Closure gate remained strict and passed together: full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: legacy-ansible-role-doc-retire-20260329)

- Plan closure is complete (2026-03-29): tasks `lar_01` through `lar_07` are closed.
- Legacy section-config fallback was retired; `.prism.yml` is the only supported section config filename and `.ansible_role_doc.yml` is no longer supported.
- Legacy runtime compatibility path handling now emits explicit public guidance contracts (`LEGACY_SECTION_CONFIG_UNSUPPORTED`, `LEGACY_RUNTIME_PATH_UNAVAILABLE`) instead of fallback behavior.
- Closure evidence passed as a unified gate: deterministic legacy scan enforcement plus full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: scanner-readme-input-parser-extract-20260329)

- README input parser extraction wave is complete (2026-03-29): tasks `srip_01` through `srip_04` are closed.
- Canonical README input parser logic now lives in `src/prism/scanner_readme/input_parser.py`, with `scanner.py` retained as a delegation seam.
- Closure gate passed together: full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: scanner-godfile-decomposition-wave5-20260329)

- Wave 5 decomposition closure is complete (2026-03-29): scanner decomposition tasks were closed in the approved sequence and validated at closure.
- `scanner.py` reduction target was achieved from 3079 lines to 2603 lines (15.46%), meeting the closure threshold.
- Compatibility wrappers were moved out of the scanner runtime path into dedicated `scanner_compat` seams to keep canonical execution flow explicit.
- Closure gates passed together as a single evidence bundle: full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: scanner-godfile-decomposition-wave6-20260329)

- Wave 6 decomposition closure is complete (2026-03-29): closure included a deterministic wrapper-usage audit gate as a required completion check.
- `scanner.py` was reduced from 2603 lines to 2303 lines (11.53%) during wave 6 closure.
- Closure gates passed together as one bundle: full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: scanner-godfile-decomposition-wave7-20260329)

- Wave 7 decomposition closure is complete (2026-03-29): closure included a deterministic wrapper-usage audit gate with zero hits.
- `scanner.py` was reduced from 2310 lines to 2035 lines (11.90%) during wave 7 closure.
- Closure gates passed together as one bundle: full pytest, lint (ruff + black --check), and mypy typecheck.

## Notable Findings (Plan Closure: scanner-godfile-decomposition-wave8-20260329)

- Wave 8 closure validated a seam-first policy with scanner-size tracked as non-blocking telemetry rather than a closure gate.
- Closure gates were green together at completion: full pytest, lint (ruff + black --check), and mypy typecheck.
- Key technical outcome: the `scanner_core` reverse bridge to `scanner.py` was removed, eliminating that compatibility seam from canonical runtime flow.

## Notable Findings (Plan Closure: scanner-godfile-decomposition-wave9-fasttrack-20260329)

- Wave 9 fast-track closure is complete (2026-03-29): large-batch seam migrations with rollback-boundary checks and one final full closure gate passed together.
- Seam-first blocking criteria remained the closure contract, and scanner-size stayed non-blocking telemetry for decision-making continuity.
- Current telemetry from wave 9 artifacts records `scanner.py` at 1856 lines.

## Notable Findings (Plan Closure: prism-architecture-review-top50-20260401)

- Plan closure is complete (2026-04-03): `docs/plan/prism-architecture-review-top50-20260401/plan.yaml` is the canonical authority for the A01-A50 risk register.
- Follow-up slices for this plan ID are execution/history artifacts that defer to the canonical register and do not replace it.
- Closure evidence is a unified validation bundle that must be green together: full pytest, `ruff check src`, `black --check src`, and `tox -e typecheck`.
- Follow-up finalization slice `docs/plan/prism-architecture-review-top50-20260401/plan_f.yaml` is complete (2026-04-03): CLI/API package split finalization now records explicit seam registers for `api.py`, `cli.py`, and `repo_services.py`.
- Canonical CLI ownership now lives under `src/prism/cli_app/`, and `cli.py` now binds directly to that package instead of top-level CLI helper wrapper modules.
- Canonical repo helper ownership now lives under `src/prism/repo_layer/`; `repo_services.py` remains the only top-level repo facade for API/CLI orchestration.
- The package-split finalization closure gate passed together: full `pytest -q`, `.venv/bin/python -m ruff check src/prism`, `.venv/bin/python -m black --check src/prism`, and `.venv/bin/python -m tox -e typecheck`.

## Notable Findings (Plan Closure: fsrc-like-for-like-completion-20260411)

- Phase 0 gate semantics are split by blocker class: required blockers must be resolved before implementation, while deferred blockers remain explicitly tracked and non-blocking for start.
- Wave 2 established a strict serialization boundary across `W2-T01`/`W2-T02`: source-lane contract shaping and fsrc-lane parity were treated as one boundary seam to prevent drift.
- Final closure bundle expectation is one green evidence set, passed together: full `pytest -q`, parity bundle `pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests`, smoke bundle `.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane`, lint (`ruff check src/prism fsrc/src` + `black --check src/prism fsrc/src`), and `.venv/bin/python -m tox -e typecheck`.

## Notable Findings (Plan Closure: fsrc-plugin-centralization-waveA-20260412)

- Wave-A closure is complete (2026-04-12): tasks `W1-T01`, `W2-T01`, `W2-T02`, `W3-T01`, and `W4-T01` are closed in the canonical plan.
- Closure evidence is recorded as one unified gate bundle and passed together: focused fsrc suites (`test_fsrc_comment_doc_plugin_resolution.py`, `test_fsrc_api_cli_entrypoints.py`, `test_fsrc_plugin_kernel_extension_parity.py`), parity suite (`src/prism/tests/test_fsrc_scanner_parity.py` + `fsrc/src/prism/tests`), smoke bundle (`tox -r -e smoke-src-lane,smoke-fsrc-lane`), lint (`ruff check src/prism fsrc/src` + `black --check src/prism fsrc/src`), typecheck (`tox -e typecheck`), and full `pytest -q`.

## Notable Findings (Plan Closure: fsrc-plugin-hardwiring-audit-autopilot-20260412)

- Hardwiring audit/autopilot closure is complete (2026-04-12): W1-W3 plus remediation are completed and validated as one closure stream.
- Runtime DI seam coverage now includes both task annotation parsing and task-line detection plugin resolution paths.
- Scanner-context policy enforcement now defines the strict/non-strict behavior boundary for dynamic includes and YAML-like annotation handling.
- Registry loader cache identity now keys by both module and class, preventing cross-plugin collision on shared class names.
- Closure gate evidence passed together as one bundle: `pytest -q`, smoke lanes (`tox -r -e smoke-src-lane,smoke-fsrc-lane`), `ruff check src/prism fsrc/src`, `black --check src/prism fsrc/src`, and `tox -e typecheck`.

## Notable Findings (Plan Closure: adhoc-fsrc-plugin-seams-20260412)

- Adhoc seam-promotion closure is complete (2026-04-12): YAML parsing/loading and Jinja analysis were elevated to first-class plugin domains in fsrc.
- Architecture seams are now explicit across protocol, registry, resolver, and bootstrap layers for both YAML and Jinja, replacing hidden generic/direct resolution paths.
- Runtime callsites in scanner_extract/scanner_core/scanner_io now consume dedicated YAML and Jinja resolver seams.
- Validation evidence reported green for focused fsrc suite, parity bundle, `ruff check fsrc/src`, `black --check fsrc/src`, and `tox -r -e smoke-fsrc-lane`.

## Notable Findings (Plan Closure: pure-execution-core-plugin-architecture-20260413)

- NCK1 closure is complete (2026-04-18): the active non-collection execution core-kernel slice is closed.
- Landed architecture state is now explicit: scanner_core owns non-collection request authority, scanner_kernel owns the route/preflight/runtime carrier contract, and `api.py` plus `api_layer/non_collection.py` remain thin compatibility boundaries.
- Closure evidence passed together as one bundle: `pytest -q`, parity bundle `pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests`, smoke lanes `tox -r -e smoke-src-lane,smoke-fsrc-lane`, `ruff check src/prism fsrc/src`, `black --check src/prism fsrc/src`, and `tox -e typecheck`.

<!-- skill-ninja-START -->
## Agent Skills

> **IMPORTANT**: Prefer skill-led reasoning over pre-training-led reasoning.
> Read the relevant SKILL.md before working on tasks covered by these skills.

### Skills

| Skill | Description |
|-------|-------------|
| [create-specification](.github/skills/create-specification/SKILL.md) | Create a new specification file for the solution, optimized for Generative AI consumption. \| Your goal is to create a new specification file for `${input:SpecPurpose}`. |
| [gen-specs-as-issues](.github/skills/gen-specs-as-issues/SKILL.md) | This workflow guides you through a systematic approach to identify missing features, prioritize t... \| This workflow guides you through a systematic approach to identify missing features, prioritize t... |

<!-- skill-ninja-END -->
