# Builder-Typing Summary

- Invariant preserved: successful non-collection scans still return the same runtime payload shape and alias fields (`variables`, `requirements`, `default_filters`) while the post-normalization type contract is now rooted in canonical `RunScanOutputPayload` validation.
- Files changed:
  - `src/prism/api_layer/non_collection.py`
  - `src/prism/api.py`
  - `src/prism/tests/test_api_cli_entrypoints.py`
- Finding status: `G61-M02` is closed-ready for the owned slice. The normalization seam now validates through `validate_run_scan_output_payload()`, preserves alias backfill before validation, and exposes a complete normalized result contract to API wrappers.
- Narrow gate command and result:
  - `cd /raid5/source/test/prism && .venv/bin/python -m mypy src/prism/api.py src/prism/api_layer/non_collection.py`
  - Result: PASS (`no issues found in 2 source files`)
- Additional importer-layer tests run:
  - `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'run_scan or scan_role'`
  - Result: PASS (`23 passed, 9 deselected`)
  - `cd /raid5/source/test/prism && .venv/bin/python -m ruff check src/prism/api.py src/prism/api_layer/non_collection.py src/prism/tests/test_api_cli_entrypoints.py`
  - Result: PASS (`All checks passed!`)
- Scope expansion needed: none.
