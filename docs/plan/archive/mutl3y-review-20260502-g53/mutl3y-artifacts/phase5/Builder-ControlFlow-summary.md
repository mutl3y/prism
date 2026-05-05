# Builder-ControlFlow Summary

Finding: `G53-H01`
Fix group key: `execution-request-assembly-split`

Hypothesis result: confirmed.
`_assemble_execution_request()` had two responsibilities. Wave 1 extracted runtime participant assembly into `_assemble_runtime_participants()` and left request finalization in `_assemble_execution_request()` without changing registry authority, prepared-policy enforcement, or the bridge-slot circularity workaround.

Files changed:

- `src/prism/scanner_core/execution_request_builder.py`
- `src/prism/tests/test_execution_request_builder.py`
- `src/prism/tests/test_di_registry_resolution.py`

Validation commands and outcomes:

- `pytest -q src/prism/tests/test_execution_request_builder.py src/prism/tests/test_di_registry_resolution.py -k 'execution_request or authoritative_registry'`
  - PASS: `17 passed, 28 deselected in 0.29s`
- `.venv/bin/python -m ruff check src/prism/scanner_core/execution_request_builder.py src/prism/tests/test_execution_request_builder.py src/prism/tests/test_di_registry_resolution.py`
  - PASS
- `.venv/bin/python -m black --check src/prism/scanner_core/execution_request_builder.py src/prism/tests/test_execution_request_builder.py src/prism/tests/test_di_registry_resolution.py`
  - PASS

Residual risk:

- The split is intentionally narrow. `_assemble_execution_request()` still owns prepared-policy finalization, container scan-option replacement, `ScannerContext` creation, and request return assembly in one step; any later DI typing or ownership cleanup remains out of scope for this wave.
