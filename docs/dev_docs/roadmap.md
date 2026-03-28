---
layout: default
title: Roadmap and Backlog
---

This file summarizes delivered backlog themes and future direction.

## Delivered Themes

- richer role realism and README generation quality
- repo-source intake and style-guide support
- variable discovery and provenance improvements
- collection plugin inventory and CLI subcommand redesign
- annotation quality metrics and strict policy options
- modernization phase 1 complete: shared `repo_services.py` extracted; API and CLI share repo-intake, clone, fetch, sparse-checkout, and temp-workspace orchestration
- modernization phase 2 complete: `scanner.py` decomposed into 7 focused submodules (`scan_request`, `scan_context`, `scan_metrics`, `scan_output_emission`, `scan_discovery`, `scan_output_primary`, `scanner_report` additions); scanner is now an orchestrator
- modernization phase 3 complete: typed internal seam contracts (TypedDicts) throughout scan orchestration; full mypy gate (`tox -e typecheck`) covering all 25 source files; CI runs typecheck on every push/PR
- **modernization program v2 complete (2026-03-28):** Four rendering responsibilities extracted (`render_guide`, `render_readme`, `render_reports`, `emit_output`); scanner.py reduced by 800+ lines; 768 tests passing with 93.3% coverage; cross-repo compatibility verified with prism-learn (34/34 tests); formal sign-off document created with completion metrics and next steps

## Ongoing Focus

- reduce ambiguity in inferred variables
- maintain high test coverage on scanner and parser paths
- improve operator ergonomics for fleet-scale usage
