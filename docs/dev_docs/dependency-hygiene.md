---
layout: default
title: Dependency Hygiene
---

Current dependency hygiene is intentionally simple and explicit:

- CI runs `.github/workflows/dependency-hygiene.yml` on pull requests, pushes to `main`, and manual dispatches.
- The workflow installs the project with dev dependencies and runs `pip-audit --strict`.
- Local review should use the same command path to keep CI and workstation checks aligned.

## Local Command

```bash
.venv/bin/python -m pip install -e .[dev]
.venv/bin/pip-audit --strict
```

## Current Scope

- Python package vulnerabilities in the resolved Prism environment
- drift detection when a new dependency or transitive advisory lands

## Follow-Up

- keep `project.optional-dependencies.dev` current so local and CI audit environments stay aligned
- expand with Node/package-manager audit coverage separately for plugin workspaces where needed
