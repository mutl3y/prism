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
- shared repo facade complete: `prism.repo_services` is the canonical repo-intake boundary over package-owned `prism.repo_layer` internals
- scanner package decomposition complete: `prism.scanner` now delegates canonical runtime behavior to `prism.scanner_core`, `prism.scanner_data`, `prism.scanner_extract`, `prism.scanner_readme`, `prism.scanner_reporting`, `prism.scanner_io`, `prism.scanner_config`, and `prism.scanner_compat`
- typed seam contracts complete: `prism.scanner_data` centralizes TypedDict contracts and builder helpers, with `tox -e typecheck` enforced in CI
- CLI/API package split complete (2026-04-03): `prism.api` and `prism.cli` remain stable facades over `prism.api_layer` and `prism.cli_app`, with seam registers and reverse-import guardrails frozen
- VS Code extension lane active in-repo: `plugins/prism-comment-highlighter` is now linted, typechecked, and tested in CI as a first-class plugin package

## Ongoing Focus

- reduce ambiguity in inferred variables
- maintain high test coverage on scanner and parser paths
- improve operator ergonomics for fleet-scale usage
- keep architecture and capability docs aligned with package-owned extension boundaries
