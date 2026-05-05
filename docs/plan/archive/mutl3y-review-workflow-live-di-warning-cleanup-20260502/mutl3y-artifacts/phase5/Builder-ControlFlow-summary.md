agent name: Builder-ControlFlow
owned file set: src/prism/tests/test_di_registry_resolution.py
invariant preserved: Registry default-selection behavior remains unchanged; only the fake plugin in the test was updated to satisfy the scan_pipeline stateless-marker contract.
changed files: src/prism/tests/test_di_registry_resolution.py
focused validation result: `.venv/bin/python -m pytest -q src/prism/tests/test_scanner_core_di.py src/prism/tests/test_di_registry_resolution.py` -> 78 passed in 2.44s
concise status: The warning source was removed by making the test fake plugin stateless; the focused DI slice passed with no failures.
