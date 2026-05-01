# Builder-ControlFlow Summary

- Plan ID: gilfoyle-review-20260501-g38
- Finding: FIND-G38-CF-01
- Scope: src/prism/scanner_kernel/orchestrator.py, src/prism/tests/test_plugin_kernel_extension_parity.py, src/prism/tests/test_platform_routing_fail_closed.py
- Model: GPT-5.4
- Model fallback: none

## Change

Tightened the scan-pipeline runtime contract in `orchestrate_scan_payload_with_selected_plugin()` so a plugin that returns a non-dict runtime payload now fails closed with `PrismRuntimeError` instead of silently returning the original payload unchanged. Existing dict-returning plugins keep the prior metadata merge behavior.

## Tests

- Added a focused invalid-output test that asserts the runtime path raises `scan_pipeline_execution_failed` with `failure_mode=invalid_plugin_output`.
- Added a focused valid-output test that proves dict-returning plugins still merge metadata without overwriting existing values.
- Validation passed:
  - `pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k scan_pipeline`
  - `pytest -q src/prism/tests/test_platform_routing_fail_closed.py -k scan_pipeline`

## Status

Implemented and validated inside the assigned scope.
