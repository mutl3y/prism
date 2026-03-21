# Prism Demos

This folder contains small, runnable demos that showcase Prism's core app flows:

- `role` scans
- `collection` scans
- library API usage (`scan_role`, `scan_collection`)
- runbook rendering from scanned role metadata

All commands below assume you run them from the repository root (`prism/`).

## Contents

- `fixtures/role_demo/`: richer Ansible role fixture with tasks, handlers, and templates
- `fixtures/collection_demo/`: collection fixture with two roles and multiple plugin types
- `run_cli_demos.sh`: CLI demo runner for role, collection, and runbook outputs
- `api_demo.py`: Python API demo showing role and collection functions
- `api_runbook_demo.py`: Python API demo that renders runbook markdown and CSV
- `output/`: generated artifacts when you run demos

## Quick Start

Run both CLI demos:

```bash
bash demos/run_cli_demos.sh
```

Run API demo:

```bash
PYTHONPATH=src python demos/api_demo.py
```

Run API runbook demo:

```bash
PYTHONPATH=src python demos/api_runbook_demo.py
```

## Role and Collection Functions Shown

The API demo explicitly calls both core functions:

- `scan_role(...)`
- `scan_collection(...)`

The runbook API demo also shows:

- `render_runbook(...)`
- `render_runbook_csv(...)`

The CLI demo also runs both matching commands:

- `prism role ...`
- `prism collection ...`

## Expected Outputs

After running `run_cli_demos.sh`, output files are written to `demos/output/`:

- `role_demo_README.md`
- `role_demo_detailed.md`
- `role_demo_RUNBOOK.md`
- `role_demo_RUNBOOK.csv`
- `role_demo.json`
- `collection_demo.md`
- `collection_demo_detailed.md`
- `collection_demo.json`

Additional per-role runbook files are written under:

- `demos/output/collection_runbooks/`
- `demos/output/collection_runbooks_csv/`

The API demo prints a short JSON summary that includes:

- role scan counters
- collection metadata
- collection role names and plugin types

The fixtures are intentionally padded out so demo output includes:

- imported task files
- handlers
- templates
- multiple collection roles
- multiple lookup plugins
- inventory plugins
- multiple callback plugins
- modules, connections, strategies, tests, doc fragments, and module_utils helpers

This makes the collection demo a better example of why automated documentation matters:

- plugin families are inventoried consistently
- role and plugin breadth can be summarized without manual README upkeep
- generated docs can surface collection capabilities that are easy to miss by inspection alone
