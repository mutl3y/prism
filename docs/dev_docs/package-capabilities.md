---
layout: default
title: Package Capabilities
---

Current package capability map for the active Prism architecture.

## Current Progress Snapshot

- scanner runtime ownership is package-first, with `prism.scanner` retained as the stable public facade
- API, CLI, and shared repo intake now follow the same facade pattern through `prism.api`, `prism.cli`, and `prism.repo_services`
- package-owned extension work should now land in the owning package first, then be surfaced through a facade only when that behavior is intentionally public
- the `prism-architecture-review-top50-20260401` closure finalized the CLI/API/repo package split and froze the seam registers for the retained top-level facades

## Naming Standard

Use fully qualified Python package names when documenting ownership, imports, guardrails, or extension targets.

- prefer `prism.api_layer`, `prism.cli_app`, and `prism.repo_layer`
- prefer `prism.scanner_core`, `prism.scanner_readme`, and other full `prism.*` package names
- use bare directory labels such as `api_layer/` or `scanner_core/` only when you are explicitly talking about filesystem layout
- do not use shorthand package labels in architecture guidance when the import package name is the real contract

## Stable Facades

| Facade | Current capability |
| --- | --- |
| `prism.scanner` | stable scan entrypoint and public facade over scanner packages |
| `prism.api` | stable library API for role, collection, and repo scans |
| `prism.cli` | stable CLI entrypoint, parser export, and top-level exit handling |
| `prism.repo_services` | stable shared repo-intake facade used by both API and CLI layers |

## Package-Owned Capabilities

### `prism.api_layer`

Owns package-first API orchestration behind `prism.api`.

- `prism.api_layer.common`: payload parsing, result normalization, and failure record shaping at the API boundary
- `prism.api_layer.role`: role-scan API behavior
- `prism.api_layer.collection`: collection-scan orchestration, dependency aggregation, per-role README/runbook helpers
- `prism.api_layer.repo`: repo-scan API orchestration over the shared repo facade

### `prism.cli_app`

Owns package-first CLI behavior behind `prism.cli`.

- `prism.cli_app.parser`: parser construction, option registration, and shell completion support
- `prism.cli_app.commands`: role, collection, repo, and completion command handlers
- `prism.cli_app.runtime`: exit-code mapping, output path resolution, persistence helpers, and top-level error formatting
- `prism.cli_app.presenters`: success messaging, output rendering helpers, content capture, and truncation/redaction helpers
- `prism.cli_app.shared`: shared CLI option resolution such as vars context, feedback-driven collection checks, and effective README config selection

### `prism.repo_layer`

Owns package-first repository intake behind `prism.repo_services`.

- `prism.repo_layer.intake`: clone, sparse checkout, workspace lifecycle, checkout-target resolution, and repo scan preparation
- `prism.repo_layer.metadata`: repo path normalization, repo metadata fetch helpers, style README candidate discovery, and scan metadata normalization

### `prism.scanner_core`

Owns scan orchestration and runtime assembly.

- DI container and explicit composition wiring
- scanner context construction and runtime request normalization
- variable discovery orchestration and feature detection
- output orchestration handoff into rendering and emission layers

### `prism.scanner_data`

Owns typed contracts and builders shared across the scanner pipeline.

- request, context, output, report, collection, error, and variable contracts
- builder helpers for payload and variable-row construction
- canonical typed boundary definitions for API and scanner seams

### `prism.scanner_extract`

Owns source traversal and extraction logic.

- YAML and task traversal
- variable and Jinja reference extraction
- task catalog and molecule scenario discovery
- role feature extraction
- requirements and collection dependency source extraction

### `prism.scanner_readme`

Owns README rendering and documentation composition.

- style guide parsing and heading normalization
- README section composition and merge behavior
- documentation insights and README-input parsing
- guide, notes, and variable rendering helpers

### `prism.scanner_analysis`

Owns reporting and analysis helpers.

- scanner counters and provenance issue classification
- scanner report row shaping and markdown rendering
- runbook and runbook CSV generation
- collection dependency aggregation

### `prism.scanner_io`

Owns output rendering, file emission, and YAML loading.

- primary output rendering and output-path resolution
- scanner-report and runbook sidecar emission
- collection markdown rendering and runbook artifact persistence
- YAML candidate iteration and parse-failure collection

### `prism.scanner_config`

Owns configuration, policy, and style-resolution behavior.

- README section config loading and visibility rules
- marker-prefix loading
- runtime scan policy loading
- pattern-policy loading and unknown-heading logging
- style-guide source and section-title resolution

### `prism.scanner_compat`

Owns isolated compatibility bridges that are intentionally outside canonical runtime flow.

- retained compatibility helpers for README/style-guide merge behavior
- transitional wrapper surfaces kept separate from scanner canonical execution paths

### `plugins/prism-comment-highlighter`

Owns the VS Code extension for Prism comment-driven documentation.

- Prism marker matching across contiguous comment blocks
- folding helpers and Prism-only fold/unfold commands
- palette, custom color, and multicolor rendering behavior
- extension commands, settings, and activation wiring
- dedicated format, lint, typecheck, and test workflow coverage

## Extension Rule

- add new scanner runtime behavior in the owning `prism.scanner_*` package first
- add new library API behavior in `prism.api_layer` first
- add new CLI parser, command, presenter, or runtime behavior in `prism.cli_app` first
- add new shared repo intake behavior in `prism.repo_layer` first
- keep facade edits limited to public export decisions, compatibility seams, and top-level entry handling
