# Modernization Plan v2

## Prism Modernization Program v2 (Active Operating Plan / Source of Truth)

This document is the only active operating plan for Prism modernization.

### Active Baseline

- Priority order is strict: correctness first, readability/maintainability second, reliability/type safety third, performance fourth.
- Breaking changes are allowed when they improve clarity or correctness; each intentional contract delta requires migration/changelog notes.
- TDD is mandatory: each slice starts with focused failing tests before implementation.

### Stop-The-Line and Rollback Triggers

- Stop immediately if focused failing tests are not written first for the declared slice.
- Stop immediately if extracted modules import back into `scanner.py`.
- Stop immediately if same-name wrapper/helper shadowing appears in extracted seams.
- Roll back or isolate the slice if focused tests cannot be made green without widening declared scope.
- Roll back or isolate the slice if full tests or typecheck fail and cannot be fixed within the slice.
- **Stop immediately** if scanner-report markdown format changes (section titles, column names, table structure) without a corresponding update to `prism-learn/plans/modernization-plan-v2.md` (the cross-repo contract is defined in the "Cross-Repo Contract Matrix" section of that file).

### Scanner Reduction Targets

- Baseline size: run `wc -l src/prism/scanner.py` at the start of each slice to get current line count. (Reference: 3926 lines measured at Phase C baseline on 2026-03-28.)
- Reduction target for rendering extraction program: reduce by at least 900 lines overall.
- Line-count target after slices 2a-2d: ≤3000 lines (measured against `wc -l` at slice start).
- Responsibility-removal target from `scanner.py`:
  - guide/body rendering composition
  - README composition and assembly
  - scanner-report and runbook rendering
  - output emission orchestration

### Anti-Regression Architecture Safeguards

- One-way dependency rule: `scanner.py` may import extracted modules; extracted modules must never import `scanner.py`.
- No reverse imports from extracted modules into `scanner.py`.
- No same-name wrapper/helper shadowing between imported helpers and compatibility wrappers.
- Run a cycle-check step each slice using:
  - `rg -n "from prism\.scanner import|import prism\.scanner" src/prism/scanner_submodules/`
- **Callback injection sites**: `render_section_body`, `render_readme`, `render_runbook`, and `render_runbook_csv` are passed as callable arguments (not imported) in `scan_output_emission.py` and `scanner_runbook_report.py`. These bypass the `rg` import-cycle check.
  Audit procedure: for each of the four callsites, confirm the callable is imported from the new render submodule (not from `scanner.py`), and that no function passed as a callback itself imports from `scanner.py`. Check: `rg -n "def render_section_body|def render_readme|def render_runbook|def render_runbook_csv" src/prism/scanner_submodules/` — each must appear in the target render submodule, not in `scanner.py` or any module that imports from `scanner.py`.

### TDD/Test-First Rule

- write or update focused failing tests first for the targeted slice
- implement only the minimal code change needed to satisfy those tests
- run focused tests, full tests, and typecheck gates before merge
- if behavior is intentionally changed, update contract tests and migration/changelog notes first
- keep correctness and readability ahead of optimization throughout the batch

### Mandatory Acceptance Gates (Every Slice)

- [ ] focused failing tests added first for the slice
- [ ] focused tests pass
- [ ] full tests pass
- [ ] typecheck passes
- [ ] architecture cycle check clean: `rg -n "from prism\.scanner import|import prism\.scanner" src/prism/scanner_submodules/` returns no results; verify callback injection sites (`render_section_body`, `render_readme`, `render_runbook`, `render_runbook_csv`) manually in `scan_output_emission.py` and `scanner_runbook_report.py`

### Slice Plan

**Status convention:** When a slice completes all acceptance gates, update its label to `(Complete)` and mark the next slice as `(Current)`. This must be done in the commit that closes the slice.

#### Slice 1: Wrapper Stability (Complete)

Status: COMPLETE

Scope:

- `src/prism/scanner.py`
- `src/prism/scanner_submodules/scan_context.py`
- `src/prism/scanner_submodules/scan_discovery.py`
- `src/prism/scanner_submodules/scan_output_emission.py`
- `src/prism/scanner_submodules/scan_output_primary.py`
- `src/prism/scanner_submodules/scan_request.py`
- wrapper parity tests under `src/prism/tests/`

#### Slice 2a: Guide/Body Rendering Extraction **(Complete)**

Scope:

- extract guide/body rendering helpers from `src/prism/scanner.py` into rendering-focused submodule(s)
- keep behavior parity through focused rendering tests

Target submodule(s): `src/prism/scanner_submodules/render_guide.py`

**Pre-work (TDD gate):** Before any extraction begins, create `src/prism/tests/test_render_guide.py` with focused unit tests for:

- `_render_guide_section_body`
- `_render_guide_identity_sections`
- Any other guide-rendering helpers to be extracted

These tests must fail (AttributeError or ImportError) before extraction and pass after. Slice 2a may not proceed without this file.

#### Slice 2b: README Composition Extraction **(Complete)**

Scope:

- extract README composition/assembly logic from `src/prism/scanner.py`
- keep markdown output contracts stable unless explicitly changed with migration notes

Target submodule(s): `src/prism/scanner_submodules/render_readme.py`

Scope note: this slice covers README rendering helpers that generate markdown content (Jinja2 template rendering, section body construction). Style-guide/display-title normalization helpers in `scan_output_primary.py` are out of scope for this slice.

**Pre-work (TDD gate):** Before any extraction begins, create `src/prism/tests/test_render_readme.py` with focused unit tests for:

- README section body construction helpers
- Jinja2 template rendering helpers to be extracted

These tests must fail (AttributeError or ImportError) before extraction and pass after. Slice 2b may not proceed without this file.

#### Slice 2c: Scanner-Report and Runbook Rendering Extraction **(Complete)**

Scope:

- extract scanner-report markdown and runbook/render CSV logic from `src/prism/scanner.py`
- maintain scanner-report and runbook contract parity unless explicitly versioned

Target submodule(s): `src/prism/scanner_submodules/render_reports.py`

**Pre-work (TDD gate):** Before any extraction begins, create `src/prism/tests/test_render_reports.py` with focused unit tests for:

- Scanner-report markdown generation helpers
- Runbook rendering helpers
- Any section title, table structure, or column name that prism-learn depends on

These tests must fail (AttributeError or ImportError) before extraction and pass after. **Slice 2c may not proceed without this file. A format change in scanner-report markdown output is a cross-repo breaking change — stop-the-line applies.**

#### Slice 2d: Output Orchestration Extraction **(Current - Pre-Work)**

Scope:

- extract output emission/orchestration flow from `src/prism/scanner.py`
- centralize orchestration in dedicated submodule(s) with one-way dependencies

Target submodule(s): `src/prism/scanner_submodules/emit_output.py`

**Pre-work (TDD gate):** Before any extraction begins, create `src/prism/tests/test_render_output.py` with focused unit tests for:

- Output emission orchestration helpers to be extracted

These tests must fail (AttributeError or ImportError) before extraction and pass after. Slice 2d may not proceed without this file.

### Per-Slice Validation Commands

Focused tests first (write failing tests before implementation), then run:

- Slice 2a: `pytest -q src/prism/tests/test_render_guide.py src/prism/tests/test_scan_output_primary.py -k "render or guide"`
- Slice 2b: `pytest -q src/prism/tests/test_render_readme.py src/prism/tests/test_scan_output_primary.py -k "render or readme"`
- Slice 2c: `pytest -q src/prism/tests/test_render_reports.py src/prism/tests/test_scan_output_emission.py -k "render or report or runbook or scanner_report"`
- Slice 2c callback audit: `rg -n "def render_section_body|def render_readme|def render_runbook|def render_runbook_csv" src/prism/scanner_submodules/`
- Slice 2d: `pytest -q src/prism/tests/test_render_output.py src/prism/tests/test_scan_output_emission.py -k "emit or output or orchestration"`
- Slice 2d callback audit: `rg -n "def render_section_body|def render_readme|def render_runbook|def render_runbook_csv" src/prism/scanner_submodules/`
- Wrapper/parity regression set when compatibility seams move: `pytest -q src/prism/tests/test_scan_context.py -k "wrapper or payload or finalize"`
- Wrapper/parity regression set when discovery seams move: `pytest -q src/prism/tests/test_scan_discovery.py -k "wrapper or resolve_scan_identity"`
- Wrapper/parity regression set when primary output seams move: `pytest -q src/prism/tests/test_scan_output_primary.py -k "render_primary_scan_output or render_and_write_scan_output"`
- Wrapper/parity regression set when emission seams move: `pytest -q src/prism/tests/test_scan_output_emission.py -k "emit_scan_outputs or write_optional_runbook_outputs or scanner_report"`

Full and type gates:

- `PYTHONPATH=src .venv/bin/python -m pytest -q`
- `tox -e typecheck -q`

Architecture safeguard gate:

- `rg -n "from prism\.scanner import|import prism\.scanner" src/prism/scanner_submodules/`

### Execution Workflow

- [ ] pick one modernization batch and define explicit out-of-scope items
- [ ] **Before starting:** record the pre-slice SHA: `export PRE_SLICE_SHA=$(git rev-parse HEAD)` — use this for rollback if the acceptance gate fails: `git checkout $PRE_SLICE_SHA`
- [ ] **Isolation:** Use a feature branch per slice (`git checkout -b slice-2a`). If a slice fails the acceptance gate, revert to the pre-slice-start commit: `git checkout $PRE_SLICE_SHA` and discard the branch.
- [ ] write or update focused failing tests first for the targeted slice
- [ ] capture baseline performance on target commands when performance is a stated batch target (Not applicable for Slices 2a–2d — performance is not a stated target for rendering extraction slices)
- [ ] if behavior is intentionally changed, update contract tests and migration/changelog notes first
- [ ] implement the minimal code change needed to satisfy the tests
- [ ] run focused tests, full tests, and typecheck gates
- [ ] capture post-change performance and compare when performance is a stated batch target (Not applicable for Slices 2a–2d — performance is not a stated target for rendering extraction slices)
- [ ] write migration/changelog notes
  - Migration and breaking-change notes go in `docs/changelog.md` under a `## Modernization v2 — Slice <N>` heading.
- [ ] merge and queue the next single batch
