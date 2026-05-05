Agent: Builder-APISeam

Owned file set:

- /raid5/source/test/prism/src/prism/api.py
- /raid5/source/test/prism/src/prism/tests/test_api_cli_entrypoints.py
- /raid5/source/test/prism/src/prism/tests/test_g03_scan_cache_integration.py

Summary:

- Removed the top-level API backfill that mutated prism.scanner_core.di.ScannerContext.
- Removed the mirrored cache integration test setup hack.
- Added a focused regression test proving api.run_scan succeeds by forwarding scanner_context_cls explicitly without mutating prism.scanner_core.di.

Validation:

- PASS: pytest -q src/prism/tests/test_api_cli_entrypoints.py -k run_scan
- PASS: pytest -q src/prism/tests/test_g03_scan_cache_integration.py

Status:

- G59-H01 is ready for closure.
