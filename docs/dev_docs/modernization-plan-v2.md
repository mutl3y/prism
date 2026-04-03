# Modernization Plan v2

## Prism Modernization Program v2 (Current Architecture Baseline)

This document is the architecture-status companion to `docs/dev_docs/architecture.md`.
It captures the post-modernization ownership model and the guardrails that remain active for future slices.

### Document Status

- Active guidance: this file and `docs/dev_docs/architecture.md` describe the current architecture baseline.
- Historical guidance: scanner_submodules-era execution notes are archived context only and are not active implementation instructions.
- Plan authority: architecture backlog authority for `prism-architecture-review-top50-20260401` remains in `docs/plan/prism-architecture-review-top50-20260401/plan.yaml`.

### Current Module Ownership Model

Prism scanner runtime behavior is package-owned and facade-driven.
`src/prism/scanner.py` remains a public facade, while canonical behavior is implemented in package boundaries under `src/prism/`.

| Package | Ownership boundary |
| --- | --- |
| `scanner_core/` | request normalization, orchestration, runtime/context assembly, variable-discovery coordination |
| `scanner_data/` | typed contracts and builders for scan inputs/outputs, report metadata, and variable rows |
| `scanner_extract/` | task/YAML traversal, variable and reference extraction, role feature collection, requirements/discovery loaders |
| `scanner_readme/` | README rendering, style parsing/normalization, section composition, documentation insights |
| `scanner_analysis/` | scanner metrics, report shaping, runbook generation, dependency analysis helpers |
| `scanner_io/` | output rendering/writing, emission orchestration, YAML candidate loading and parse-failure reporting |
| `scanner_config/` | policy/config loading, marker/style behavior, runtime policy switches, legacy retirement handling |
| `scanner_compat/` | isolated compatibility bridges outside canonical runtime flow |

### Architecture Guardrails (Active)

- One-way dependency rule: canonical packages must not reverse-import `prism.scanner`.
- Public-cross-package import rule: private cross-package imports are blocked except explicit seam allowlists.
- Compatibility isolation rule: compatibility helpers remain in `scanner_compat/` and must not re-enter canonical runtime paths.
- Contract stability rule: scanner-report markdown/table contracts consumed by `prism-learn` require coordinated updates when changed.

### Validation Gates (Active)

- Full tests: `PYTHONPATH=src .venv/bin/python -m pytest -q`
- Lint and format checks: `.venv/bin/python -m ruff check src` and `.venv/bin/python -m black --check src`
- Typecheck: `tox -e typecheck -q`
- Architecture guardrails: `src/prism/tests/test_scanner_architecture_guardrails.py`

### Current Reduction Policy

- Scanner size can be tracked as telemetry, but seam integrity and contract correctness are the blocking criteria.
- For any new extraction/refactor slice, prioritize:
  - correctness and contract parity first
  - explicit package boundary ownership second
  - performance improvements third unless declared as the primary slice objective

### Historical Execution Notes (Archived)

The prior slice execution details based on `scanner_submodules/` paths are archived historical guidance only.
They are intentionally retained in plan artifacts under `docs/plan/` for auditability and should not be used as the current module map.

Historical framing now archived:

- scanner_submodules-era target paths and callback-audit commands
- slice 2a-2d extraction checklists tied to `scanner_submodules/`
- scanner_submodules-specific cycle checks

Use `docs/dev_docs/architecture.md` plus this file as the published source of truth for active ownership boundaries.
