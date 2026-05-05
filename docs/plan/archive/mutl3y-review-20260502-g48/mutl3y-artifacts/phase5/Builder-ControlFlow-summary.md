# Builder-ControlFlow Summary

- Plan ID: mutl3y-review-20260502-g48
- Finding: G48-H02
- Fix group: fallback-plugin-never-used-in-validation

## Change

Restored the documented non-strict fallback contract in `src/prism/scanner_plugins/defaults.py` so malformed prepared-policy plugins and constructor failures no longer discard `strict_mode` and `fallback_plugin` before raising. Strict mode still fails closed with `malformed_plugin_shape`, while non-strict mode now returns the fallback plugin explicitly and emits a warning.

Added scoped regression coverage in `src/prism/tests/test_defaults.py` for strict failure, non-strict DI fallback, and non-strict registry-construction fallback. Added an importer-layer parity proof in `src/prism/tests/test_plugin_kernel_extension_parity.py` to confirm the isolated import path also honors the documented fallback.

## Validation

- `pytest -q src/prism/tests/test_defaults.py -k validate_shape src/prism/tests/test_plugin_kernel_extension_parity.py`
- Result: `3 passed, 29 deselected in 0.19s`

## Regression Pattern

- When a resolver accepts both `strict_mode` and a `fallback_plugin`, treat deleting or ignoring either input before the failure branch as a fail-open regression: non-strict mode must either return the documented fallback explicitly or raise by contract, never silently drop the fallback path.
