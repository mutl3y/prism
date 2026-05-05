## Foreman Recovery Wave 1

- Plan ID: `mutl3y-review-20260504-g71`
- Cycle: `g71`
- Wave: `1`
- Fix group: `scanner_kernel.preflight_plugin_enabled_fail_closed`
- Status: `closed-ready`

### Local hypothesis

`route_scan_payload_orchestration()` treated a missing `plugin_enabled` value as
implicitly enabled during preflight. That is a fail-open contract violation:
the plugin did not affirmatively enable itself, but the kernel still executed
the plugin path.

### Implemented fix

- Removed the `None -> True` coercion in `scanner_kernel.orchestrator`.
- Missing `plugin_enabled` now fails under the same invalid-preflight-contract
  path already used for non-bool values.
- Added a focused parity regression that proves a preflight payload missing the
  `plugin_enabled` key is rejected.

### Validation

- Required narrow gate: `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k 'plugin_enabled'`
- Result: `2 passed, 30 deselected`
- Narrow mypy: `cd /raid5/source/test/prism && .venv/bin/python -m mypy src/prism/scanner_kernel/orchestrator.py`
- Result: `Success: no issues found in 1 source file`

### Changed files

- `src/prism/scanner_kernel/orchestrator.py`
- `src/prism/tests/test_plugin_kernel_extension_parity.py`
