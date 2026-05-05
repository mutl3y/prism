# Builder-ControlFlow Summary

- Plan ID: gilfoyle-review-20260501-g39
- Finding: FIND-G39-CF-01
- Scope: src/prism/scanner_kernel/orchestrator.py, src/prism/tests/test_plugin_kernel_extension_parity.py, src/prism/tests/test_platform_routing_fail_closed.py
- Model: GPT-5.4
- Model fallback: none

## Change

Added the missing fail-closed runtime contract check in `orchestrate_scan_payload_with_selected_plugin()` so plugins that implement `orchestrate_scan_payload()` directly now raise the same `PrismRuntimeError` shape as the fallback helper when they return a non-dict result. Dict-returning direct plugins still pass through unchanged.

## Tests

- Added focused direct-path coverage for invalid non-dict output and valid dict pass-through in `src/prism/tests/test_plugin_kernel_extension_parity.py`.
- Validation passed:
  - `.venv/bin/python -m pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k scan_pipeline`
  - `.venv/bin/python -m pytest -q src/prism/tests/test_platform_routing_fail_closed.py -k scan_pipeline`

## Status

Implemented and validated inside the assigned scope.
