Builder-ScanCache summary for plan `mutl3y-review-20260503-g58`, Wave 1, finding `G58-C02`.

- Root cause fixed in `src/prism/scanner_core/scan_cache.py` by replacing `json.dumps(..., default=str)` with explicit canonicalization for cache-key inputs.
- Opaque objects now fingerprint by fully qualified type name instead of heap-address `repr`, so logically equivalent prepared-policy bundle contents produce stable cache keys.
- Focused regression coverage updated in `src/prism/tests/test_t3_03_scan_cache.py` to prove stability across equivalent opaque prepared-policy bundle instances while preserving option sensitivity.
- Preserved missing prepared-policy bundle cache-marker semantics; verified by the API-layer regression test.

Validation:

- `pytest -q src/prism/tests/test_t3_03_scan_cache.py::test_compute_scan_cache_key_is_stable_and_options_sensitive` -> passed
- `pytest -q src/prism/tests/test_api_cli_entrypoints.py::test_fsrc_api_run_scan_cache_key_preserves_missing_prepared_policy_bundle_state` -> passed
- `pytest -q src/prism/tests/test_g03_scan_cache_integration.py` -> passed
