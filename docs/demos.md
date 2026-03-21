---
layout: default
title: Demos
---

Use these runnable demos to see Prism behavior end-to-end with realistic role
and collection fixtures.

## Demo Index

- [Demos Overview](https://github.com/mutl3y/prism/blob/main/demos/README.md)
- [Demo Folder](https://github.com/mutl3y/prism/tree/main/demos)
- [Role Fixture](https://github.com/mutl3y/prism/tree/main/demos/fixtures/role_demo)
- [Collection Fixture](https://github.com/mutl3y/prism/tree/main/demos/fixtures/collection_demo)

## Quick Start

Run CLI demos:

```bash
bash demos/run_cli_demos.sh
```

Run API demos:

```bash
PYTHONPATH=src python demos/api_demo.py
PYTHONPATH=src python demos/api_runbook_demo.py
```

## What The Demos Cover

- `prism role` and `prism collection` command flows
- `scan_role(...)` and `scan_collection(...)` API functions
- runbook markdown/csv rendering
- plugin inventory extraction across multiple plugin families

## Expected Artifacts

Generated outputs are written under:

- `demos/output/`
- `demos/output/collection_runbooks/`
- `demos/output/collection_runbooks_csv/`

## Why This Matters

The demos provide copy/paste-ready command patterns and realistic outputs that
can be reused in onboarding, CI validation, and documentation quality reviews.
