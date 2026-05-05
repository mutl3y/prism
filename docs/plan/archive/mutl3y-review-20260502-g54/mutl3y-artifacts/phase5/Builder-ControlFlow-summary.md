# Builder-ControlFlow Summary

Hypothesis result: confirmed. `_assemble_execution_request()` now delegates the fused finalization cluster into `_finalize_execution_request()` while preserving the existing order and prepared-policy enforcement.

Files changed:

- `src/prism/scanner_core/execution_request_builder.py`
- `src/prism/tests/test_execution_request_builder.py`

Validation commands and outcomes:

- `pytest -q src/prism/tests/test_execution_request_builder.py -k finalization`
  - PASS: `2 passed, 15 deselected in 0.23s`
- `.venv/bin/python -m ruff check src/prism/scanner_core/execution_request_builder.py src/prism/tests/test_execution_request_builder.py`
  - PASS: `All checks passed!`
- `.venv/bin/python -m black --check src/prism/scanner_core/execution_request_builder.py src/prism/tests/test_execution_request_builder.py`
  - PASS: `2 files would be left unchanged.`

Residual risk:

- Low. This wave only exposes the finalization seam; runtime assembly and request construction are still coupled by `_assemble_execution_request()`, so any later ownership split will need fresh order-preservation checks at that boundary.
