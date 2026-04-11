---
layout: default
title: User Changelog
---

All notable user-facing documentation and behavior changes are tracked here.

This changelog follows Keep a Changelog and Semantic Versioning conventions.

## [Unreleased]

### Added

- New unified documentation set for average users and DevOps professionals.
- Quick-start-first docs structure with dedicated user and DevOps tracks.
- Dedicated Prism-friendly role authoring guidance.
- Dedicated feedback integration guide for local and API workflows.
- Source evaluation matrix confirming coverage of all original docs artifacts.
- Implementation-authorizing plan bundle for a new fsrc/prism build at docs/plan/prism-next-fsrc-build-20260408/.

### Changed

- Reorganized documentation information architecture with a clearer navigation model.
- Clarified policy-enforcement and CI usage guidance.
- Renamed provenance category `ambiguous_defaults_vars_override` to `precedence_defaults_overridden_by_vars` to reflect its informational (non-noise) semantics; legacy alias key emitted alongside new key during deprecation window.
- Added explicit `unresolved_noise_variables` counter to scanner report, excluding informational/precedence categories from noise totals.
- Added developer-facing Wave 1 scanner seam migration notes documenting canonical seam ownership, retained compatibility wrappers, deferred retirement criteria, and validation outcomes.

## [0.1.0] - 2026-03-15

### Added (0.1.0)

- Initial public Prism release and changelog baseline.
