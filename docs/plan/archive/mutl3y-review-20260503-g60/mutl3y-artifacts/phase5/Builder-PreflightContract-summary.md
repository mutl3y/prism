G60-H01 summary

- Updated `route_scan_payload_orchestration()` to require `plugin_enabled` to be a `bool` when present.
- Preserved existing behavior for `plugin_enabled=None` by defaulting to `True`.
- Preserved existing behavior for `plugin_enabled=False` by raising `scan_pipeline_plugin_disabled`.
- Added a focused regression proving a malformed truthy non-bool `plugin_enabled` value fails closed with `scan_pipeline_execution_failed` and `invalid_preflight_contract` routing metadata.

Validation

- `pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k plugin_enabled` -> PASS (`1 passed, 30 deselected`)
- `pytest -q src/prism/tests/test_api_cli_entrypoints.py -k plugin_enabled` -> FAIL (`31 deselected`, exit code 5 because the filter matched no tests)

Closure readiness

- G60-H01 is closure-ready for this owned slice.
