# Builder-Ownership Wave 6 Summary

- Task: `g62-wave6-builder-ownership`
- Finding: `G62-M02`
- Fix group: `api.normalized_result.type_alias_reexport`
- Owned files: `src/prism/api.py`, `src/prism/tests/test_api_cli_entrypoints.py`

## Invariant Preserved

The public API entrypoints continue to return the canonical non-collection output contract while avoiding any public re-export of the private normalized-result alias owned by `api_layer.non_collection`.

## Changes

- Removed the `NormalizedNonCollectionResult` alias re-export from `src/prism/api.py`.
- Updated the public `run_scan()` and `scan_role()` annotations in `src/prism/api.py` to use `RunScanOutputPayload`.
- Added a direct assertion in `src/prism/tests/test_api_cli_entrypoints.py` that `prism.api` no longer exposes `NormalizedNonCollectionResult` while the API entrypoint still delegates correctly.
- Contained the remaining lower-layer callback typing mismatch to a local cast at the `api_non_collection.scan_role()` seam instead of restoring the alias to the public surface.

## Validation

- Narrow gate: `pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'delegates_to_non_collection_api_layer or normalizes_payload_shape_from_non_collection_seam'` -> `4 passed, 29 deselected`
- Importer-layer gate: `.venv/bin/python -m mypy src/prism/api.py src/prism/tests/test_api_cli_entrypoints.py` -> `Success: no issues found in 2 source files`

## Status

`G62-M02` is closed-ready for the `api.normalized_result.type_alias_reexport` slice within the owned file set. No scope expansion was needed.
