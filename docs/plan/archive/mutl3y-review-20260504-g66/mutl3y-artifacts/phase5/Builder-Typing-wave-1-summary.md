# Builder-Typing Wave 1 Summary

- Agent: Builder-Typing
- Finding: G66-H05
- Fix group: repo-scan.protocolize-orchestration-seam
- Invariant preserved: repo-scan intake still delegates through the canonical repo-scan behavior, but the intake seam is now a named protocol-owned contract instead of loose variadic callable bundles.

## Changes

- Added explicit repo-scan protocols and typed intake components in [src/prism/repo_services.py](src/prism/repo_services.py).
- Replaced the non-collection `scan_repo` variadic lambda with a named keyword-only adapter in [src/prism/api_layer/non_collection.py](src/prism/api_layer/non_collection.py).
- Added a parity regression that pins the forwarded repo-scan adapter signature to `role_path`, `style_readme_path`, and `role_name_override` without `**kwargs` in [src/prism/tests/test_api_cli_repo_parity.py](src/prism/tests/test_api_cli_repo_parity.py).

## Validation

- Narrow gate: `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_api_cli_repo_parity.py -k repo_scan` -> `2 passed, 22 deselected`
- Additional importer-layer test: `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_api_cli_repo_parity.py -k forwards_role_name_override_to_scan_role_fn` -> `1 passed, 23 deselected`

## Scope

- No scope expansion required.
- No new common-traps entry identified from this slice.
