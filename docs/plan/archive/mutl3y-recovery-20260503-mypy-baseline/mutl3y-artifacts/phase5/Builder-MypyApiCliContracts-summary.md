## Builder-MypyApiCliContracts

- Restored API/CLI typing to the live non-collection and audit contracts without widening runtime surfaces to `Any`.
- Added typed collection adapters in `api.py`, fixed regex proxy defaults in `task_line_parsing.py`, and aligned owned tests to concrete mappings and full `ScanOptionsDict` fixtures.
- Contained two runtime seam issues inside the owned slice: seeded `ScannerContext` where direct factory wiring required it and isolated scan-pipeline plugin context mutation through an API-layer registry wrapper.

Validation:

- `.venv/bin/python -m mypy src/prism/api.py src/prism/cli.py src/prism/tests/test_api_cli_entrypoints.py src/prism/tests/test_api_cli_repo_parity.py src/prism/tests/test_g03_scan_cache_integration.py src/prism/tests/test_t3_03_scan_cache.py src/prism/scanner_extract/task_line_parsing.py`
- `.venv/bin/python -m pytest -q src/prism/tests/test_api_cli_entrypoints.py src/prism/tests/test_api_cli_repo_parity.py src/prism/tests/test_g03_scan_cache_integration.py src/prism/tests/test_t3_03_scan_cache.py`
