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

## Ongoing Focus

- reduce ambiguity in inferred variables
- maintain high test coverage on scanner and parser paths
- improve operator ergonomics for fleet-scale usage
