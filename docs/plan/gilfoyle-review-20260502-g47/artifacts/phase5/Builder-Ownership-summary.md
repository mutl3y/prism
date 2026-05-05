# Builder-Ownership Summary

- Findings addressed: `G46-H07`, `G46-H08`
- Owned files changed: `src/prism/api.py`, `src/prism/api_layer/collection.py`, `src/prism/tests/test_api_cli_entrypoints.py`, `src/prism/tests/test_collection_contract.py`
- Owned files not changed: `src/prism/scanner_config/readme.py`, `src/prism/scanner_config/style_parser.py`
- Concise changes: added shared API-boundary validation so sibling file-bearing public inputs now go through the same path-safety confinement as the primary role or collection path, including repo-scan file-bearing inputs.
- Concise changes: narrowed collection recovery to actual role-content defects and stopped demoting role-scan runtime failures plus collection README/runbook control-plane failures into partial-success collection payloads.
- Gate result: `pytest -q src/prism/tests/test_api_cli_entrypoints.py src/prism/tests/test_collection_contract.py` -> `36 passed, 12 failed`.
- Gate detail: the H07/H08 slice tests added or updated here now pass; the remaining failures are pre-existing focused-gate failures in `src/prism/tests/test_api_cli_entrypoints.py` on the `run_scan` path (`scan_pipeline_plugin_disabled` and missing `prepared_policy_bundle`), which were present before this slice and are outside the requested H07/H08 ownership change.
