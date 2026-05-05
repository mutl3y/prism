---
layout: default
title: Roadmap
---

This file summarizes durable product direction rather than execution-wave history.

## Delivered Themes

- stable top-level API, CLI, and shared repo entry surfaces
- repository-intake ownership consolidated in `prism.repo_services` rather than a separate repo layer
- package-owned scanner decomposition across core, kernel, extract, config, IO, README, reporting, and plugin layers
- runtime ownership split clearly across `prism.scanner_core`, `prism.scanner_kernel`, and `prism.scanner_plugins`
- typed contract boundaries centralized in `prism.scanner_data`
- role, collection, and repo scanning flows with README, runbook, and machine-readable outputs
- public audit-rule and policy hooks exposed through API and CLI seams for local workflows or CI
- VS Code extension support for Prism comment-driven annotations

## Current Focus

- keep architecture and capability docs aligned with the live package layout
- maintain high confidence in parser, scanner, and rendering paths
- improve operator ergonomics for fleet-scale usage
- keep public policy, audit, and repo-intake guidance aligned with the supported seams
- continue reducing avoidable ambiguity in inferred variable and provenance output

## Deferred Or Future Expansion

- Kubernetes and Terraform plugin implementations remain future work
- deeper fleet-learning and `prism-learn` integrations remain separate-repo concerns
- avoid reopening compatibility behavior on the canonical runtime path unless a new public seam is intentionally introduced
