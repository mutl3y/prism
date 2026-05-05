---
layout: default
title: Package Capabilities
---

Current package capability map for the live Prism package.

## Current Snapshot

- `prism.api`, `prism.cli`, and `prism.repo_services` are the stable top-level entry surfaces.
- Scanner behavior is package-owned across the `prism.scanner_*` packages rather than funneled through a single `prism.scanner` module.
- Repository intake currently lives directly in `prism.repo_services`; there is no separate `prism.repo_layer` package in the live tree.
- New behavior should land in the owning package first and only be re-exported from a top-level module when it is part of the intended public contract.

## Naming Standard

Use fully qualified Python package names when documenting ownership, imports, or extension targets.

- prefer `prism.api_layer`, `prism.cli_app`, and `prism.repo_services`
- prefer `prism.scanner_core`, `prism.scanner_readme`, and other full `prism.*` package names
- use bare directory labels such as `api_layer/` or `scanner_core/` only for filesystem discussion

## Stable Entry Surfaces

| Surface | Current capability |
| --- | --- |
| `prism.api` | public library API for role, collection, and repo scans |
| `prism.cli` | CLI entrypoint, parser construction, and top-level exit handling |
| `prism.repo_services` | shared repository-intake and repo-scan helpers used by API and CLI flows |

Entry-surface rule:

- keep these modules stable for callers
- avoid placing new multi-step implementation in them unless the public boundary itself is changing
- prefer package-owned helpers behind these surfaces whenever a package already owns the behavior

## Package-Owned Capabilities

### `prism.api_layer`

Owns package-first API orchestration behind `prism.api`.

- `prism.api_layer.common`: payload parsing, result normalization, and failure-record shaping at the API boundary
- `prism.api_layer.non_collection`: role-scan execution flow and DI-backed run-scan assembly
- `prism.api_layer.collection`: collection-scan orchestration, dependency aggregation, and per-role README/runbook helpers
- `prism.api_layer.plugin_facade`: comment-doc and audit plugin resolution exposed through the API boundary

### `prism.cli_app`

Owns package-first CLI behavior behind `prism.cli`.

- parser construction and option registration
- role, collection, repo, and completion command handlers
- runtime persistence, exit-code mapping, and top-level error formatting
- presenter and shared option-resolution helpers

### `prism.repo_services`

Owns the live repository-intake implementation and repo-scan helpers.

- repository clone and temporary workspace lifecycle
- repo-relative path validation and repo-scan target resolution
- repo scan payload normalization and downstream role-scan execution helpers
- shared callable seams used by both API and CLI entry flows

### `prism.scanner_core`

Owns scan orchestration and runtime assembly.

- DI container and explicit composition wiring
- scan request normalization and scanner-context assembly
- feature detection, variable discovery orchestration, and event/telemetry hooks
- output orchestration handoff into rendering and emission layers

### `prism.scanner_data`

Owns typed contracts and builders shared across the scan pipeline.

- request, context, output, report, collection, error, and variable contracts
- builder helpers for payload and variable-row construction
- typed boundaries consumed across API, scanner, and reporting seams

### `prism.scanner_extract`

Owns source traversal and extraction logic.

- YAML and task traversal
- variable and Jinja reference extraction
- task catalog and molecule scenario discovery
- role feature extraction plus dependency-source extraction

### `prism.scanner_readme`

Owns README rendering and documentation composition.

- style guide parsing and heading normalization
- README section composition and merge behavior
- documentation insights and README-input parsing
- notes, variables, and guide rendering helpers

### `prism.scanner_reporting`

Owns reporting artifacts, counters, and report shaping.

- scanner counters and provenance issue classification
- scanner report row shaping and markdown rendering
- runbook and runbook CSV generation
- collection dependency aggregation

### `prism.scanner_io`

Owns rendering, file emission, and YAML loading support.

- output rendering and output-path resolution
- scanner-report and runbook sidecar emission
- collection markdown rendering and artifact persistence
- YAML candidate iteration and parse-failure collection

### `prism.scanner_config`

Owns configuration, policy, and style-resolution behavior.

- README section config loading and visibility rules
- marker-prefix and scan-policy loading
- pattern-policy loading and unknown-heading logging
- style-guide source and section-title resolution

### `prism.scanner_compat`

Owns isolated compatibility bridges that stay outside canonical runtime flow.

- retained compatibility helpers for README/style-guide merge behavior
- transitional wrapper surfaces kept separate from scanner execution paths

### `plugins/prism-comment-highlighter`

Owns the VS Code extension for Prism comment-driven documentation.

- Prism marker highlighting and contiguous comment-block handling
- folding helpers and Prism-only fold/unfold commands
- extension commands, settings, and activation wiring
- dedicated format, lint, typecheck, and test coverage

## Extension Rule

- add new library API behavior in `prism.api_layer` first
- add new CLI parser, command, presenter, or runtime behavior in `prism.cli_app` first
- add new shared repo intake behavior in `prism.repo_services` unless a real package split is introduced
- add new scanner runtime behavior in the owning `prism.scanner_*` package first
- keep top-level entry surface edits limited to public export decisions, compatibility seams, and entry handling
