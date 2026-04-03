# Modernization Plan v2

This page is retained as an archived modernization baseline.
For current ownership guidance, use [Architecture](./architecture.md) and
[Package Capabilities](./package-capabilities.md).

## Prism Modernization Program v2 (Current Architecture Baseline)

This document is the architecture-status companion to `docs/dev_docs/architecture.md`.
It captures the post-modernization ownership model and the guardrails that remain active for future slices.

### Document Status

- Current guidance: `docs/dev_docs/architecture.md` and
  `docs/dev_docs/package-capabilities.md` describe the active ownership model.
- Archived baseline: this file records the modernization landing point and the
  guardrails that survived into the current architecture.
- Historical guidance: scanner_submodules-era execution notes are archived context only and are not active implementation instructions.
- Plan authority: architecture backlog authority for `prism-architecture-review-top50-20260401` remains in `docs/plan/prism-architecture-review-top50-20260401/plan.yaml`.

### Modernization Landing State

Prism scanner runtime behavior is package-owned and facade-driven.
`src/prism/scanner.py` remains a public facade, while canonical behavior is implemented in package boundaries under `src/prism/`.

Use fully qualified package names when the ownership contract matters.
Bare directory labels are for filesystem discussion only.

| Package | Ownership boundary |
| --- | --- |
| `prism.scanner_core` | request normalization, orchestration, runtime/context assembly, variable-discovery coordination |
| `prism.scanner_data` | typed contracts and builders for scan inputs/outputs, report metadata, and variable rows |
| `prism.scanner_extract` | task/YAML traversal, variable and reference extraction, role feature collection, requirements/discovery loaders |
| `prism.scanner_readme` | README rendering, style parsing/normalization, section composition, documentation insights |
| `prism.scanner_analysis` | scanner metrics, report shaping, runbook generation, dependency analysis helpers |
| `prism.scanner_io` | output rendering/writing, emission orchestration, YAML candidate loading and parse-failure reporting |
| `prism.scanner_config` | policy/config loading, marker/style behavior, runtime policy switches, legacy retirement handling |
| `prism.scanner_compat` | isolated compatibility bridges outside canonical runtime flow |

### Guardrails That Remain Active

- One-way dependency rule: canonical packages must not reverse-import `prism.scanner`.
- Public-cross-package import rule: private cross-package imports are blocked except explicit seam allowlists.
- Compatibility isolation rule: compatibility helpers remain in `prism.scanner_compat` and must not re-enter canonical runtime paths.
- Contract stability rule: scanner-report markdown/table contracts consumed by `prism-learn` require coordinated updates when changed.

### Validation Gates Retained From The Modernization Baseline

- Full tests: `PYTHONPATH=src .venv/bin/python -m pytest -q`
- Lint and format checks: `.venv/bin/python -m ruff check src` and `.venv/bin/python -m black --check src`
- Typecheck: `tox -e typecheck -q`
- Architecture guardrails: `src/prism/tests/test_scanner_architecture_guardrails.py`

### Ongoing Policy Carried Forward

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

Use `docs/dev_docs/architecture.md` and
`docs/dev_docs/package-capabilities.md` as the current source of truth.
Use this page only for modernization baseline context.
