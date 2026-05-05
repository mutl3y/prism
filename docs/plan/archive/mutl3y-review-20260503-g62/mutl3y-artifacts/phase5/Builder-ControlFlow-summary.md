# Builder-ControlFlow Summary

- Task: `g62-wave5-builder-controlflow`
- Finding: `G62-M01`
- Fix group: `scan_cache.io_error_masking`
- Invariant preserved: readable single-file cache hashes remain content-derived and stable for valid inputs.
- Change: `compute_path_content_hash()` now salts the unreadable single-file fallback with the absolute file path before the unreadable sentinel, so distinct unreadable files no longer collapse to the same digest.
- Tests: added direct coverage proving readable single-file hash stability and proving two distinct unreadable single-file paths do not hash identically when both raise `OSError`.
- Narrow gate: `pytest -q src/prism/tests/test_t3_03_scan_cache.py -k 'unreadable or content_hash'` -> `3 passed, 14 deselected`
- Optional importer gate: `.venv/bin/python -m mypy src/prism/scanner_core/scan_cache.py src/prism/tests/test_t3_03_scan_cache.py` -> `Success: no issues found in 2 source files`
- Scope expansion: none required.
- Common-traps follow-up: none beyond the existing note to re-run fresh focused gates after local test-shim changes.
