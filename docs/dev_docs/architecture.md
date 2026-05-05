---
layout: default
title: Architecture
---

Prism is a source-driven automation knowledge and policy engine.

The live package scans roles, collections, and repositories to produce
README content, runbooks, reports, and machine-readable payloads that can
feed review and Policy-as-Code workflows.

The implementation is organized around stable public entry surfaces and
package-owned layers so request shaping, runtime orchestration, rendering,
and policy evaluation stay in their owning packages.

## Public Surfaces

- `prism.api`: public library entrypoint for role, collection, repo, and audit flows
- `prism.cli`: CLI entrypoint, parser construction, top-level exit handling, and policy/audit invocation
- `prism.repo_services`: shared repository-intake helpers used by API and CLI flows

These modules are intentionally stable for callers. They should stay small and
should not become the default home for new multi-step implementation.

## Package Ownership

| Package | Owns |
| --- | --- |
| `prism.api_layer` | API-specific request parsing, result normalization, scan orchestration, and audit/plugin facade seams |
| `prism.cli_app` | CLI parser, commands, presenters, runtime helpers, and shared option handling |
| `prism.repo_services` | repository clone/workspace lifecycle, repo target resolution, and repo-scan execution helpers |
| `prism.scanner_core` | runtime orchestration, DI wiring, scan context assembly, and feature/variable coordination |
| `prism.scanner_kernel` | routing, preflight, and strict versus non-strict runtime behavior |
| `prism.scanner_plugins` | platform-specific and policy-specific plugin implementations |
| `prism.scanner_data` | typed contracts and builders shared across the pipeline |
| `prism.scanner_extract` | YAML, task, Jinja, and dependency extraction |
| `prism.scanner_readme` | README composition, style parsing, and documentation rendering helpers |
| `prism.scanner_reporting` | scanner reports, counters, runbooks, collection reporting, and provenance issue shaping |
| `prism.scanner_io` | output rendering, file emission, and YAML candidate loading |
| `prism.scanner_config` | config loading, policy loading, audit-rule types, and style/section resolution |
| `prism.scanner_compat` | isolated compatibility helpers outside canonical runtime flow |

## Runtime Flow

1. `prism.cli` or `prism.api` accepts a scan or audit request.
2. `prism.api_layer`, `prism.cli_app`, or `prism.repo_services` normalizes inputs and selects the appropriate execution path.
3. `prism.scanner_core` assembles typed runtime state and DI-backed collaborators.
4. `prism.scanner_kernel` resolves plugin routing, preflight behavior, and strict versus non-strict failure handling.
5. `prism.scanner_extract` gathers source facts and task-level signals.
6. `prism.scanner_readme`, `prism.scanner_reporting`, and `prism.scanner_io` render and emit documentation and structured outputs.
7. Policy rules are loaded through `prism.api_layer` and typed in `prism.scanner_config` so audits stay at the public boundary instead of leaking into core runtime ownership.

## Architecture Rules

- Prefer package-owned implementation over top-level facade growth.
- Keep request shaping and public compatibility handling at the edges.
- Keep platform-specific behavior in plugin-owned modules rather than `scanner_core`.
- Keep audit-rule loading and policy entry handling at public/package seams rather than inside `scanner_core`.
- Keep typed contracts in `prism.scanner_data` when a boundary is shared across packages.
- Treat `prism.repo_services` as the live shared repo-intake owner unless an explicit package split is introduced.

## Extension Guidance

- Add new public-library behavior in `prism.api_layer` first.
- Add new CLI behavior in `prism.cli_app` first.
- Add new repository-intake behavior in `prism.repo_services` first.
- Add new scan runtime behavior in the owning `prism.scanner_*` package first.
- Re-export from a top-level module only when the behavior belongs on the supported public surface.
