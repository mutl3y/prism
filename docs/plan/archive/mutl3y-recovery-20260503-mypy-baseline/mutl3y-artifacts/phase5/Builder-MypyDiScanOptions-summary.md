# Builder-MypyDiScanOptions

## Owned file set

- src/prism/scanner_core/di.py
- src/prism/tests/test_t3_03_scan_cache.py
- src/prism/tests/test_t3_01_scan_phase_events.py
- src/prism/tests/test_scanner_context.py

## Summary

Aligned the owned DI constructor seam and tests to the canonical `ScanOptionsDict` contract without weakening production signatures.

- `src/prism/scanner_core/di.py`: passed `ScanOptionsDict` directly into `VariableDiscovery` and `FeatureDetector`; fixed `factory_scanner_context()` to avoid a runtime `NameError` from a `TYPE_CHECKING`-only symbol in `cast(...)`.
- `src/prism/tests/test_t3_03_scan_cache.py`: stopped converting canonical scan options into loose plain dicts before constructor calls.
- `src/prism/tests/test_t3_01_scan_phase_events.py`: replaced loose `{}` constructor arguments with canonical scan options.
- `src/prism/tests/test_scanner_context.py`: no source edits required for the final green state.

## Validation

- Focused mypy: `./.venv/bin/python -m mypy src/prism/scanner_core/di.py src/prism/tests/test_t3_03_scan_cache.py src/prism/tests/test_t3_01_scan_phase_events.py src/prism/tests/test_scanner_context.py` -> `Success: no issues found in 4 source files`
- Focused pytest (first run): `./.venv/bin/python -m pytest -q src/prism/tests/test_t3_03_scan_cache.py src/prism/tests/test_t3_01_scan_phase_events.py src/prism/tests/test_scanner_context.py` -> failed in `test_fsrc_scanner_core_builds_non_collection_execution_request` with `NameError: name 'ScannerContext' is not defined` from `src/prism/scanner_core/di.py`
- Focused pytest (after local DI repair): `./.venv/bin/python -m pytest -q src/prism/tests/test_t3_03_scan_cache.py src/prism/tests/test_t3_01_scan_phase_events.py src/prism/tests/test_scanner_context.py` -> `46 passed in 1.14s`

## Status

Completed. Owned slice is green for both focused mypy and nearby pytest.
