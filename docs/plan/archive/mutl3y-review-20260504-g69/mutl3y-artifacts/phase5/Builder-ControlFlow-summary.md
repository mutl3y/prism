## Builder-ControlFlow Wave 2

- Plan ID: `mutl3y-review-20260504-g69`
- Cycle: `g69`
- Wave: `2`
- Fix group: `strict-phase-failures.bool-coercion.public-seams`
- Status: `closed-ready`

### Local hypothesis

`strict_phase_failures` was entering canonical scan options as an arbitrary runtime object and then being reinterpreted with `bool(...)` in request assembly, bundle resolution, and `ScannerContext`. That allowed malformed truthy values such as `"false"` to silently force strict behavior instead of failing closed.

### Implemented fix

- Added shared `require_strict_phase_failures(...)` and `resolve_strict_phase_failures(...)` helpers in `scanner_data.contracts_request`.
- Replaced `bool(...)` coercion with explicit bool validation in `scanner_core.execution_request_builder`, `scanner_plugins.bundle_resolver`, and `scanner_core.scanner_context`.
- Updated the public `scan_role(...)` seam to validate `failure_policy.strict` instead of truthifying it.
- Added API regressions that prove malformed `strict_phase_failures` values are rejected and valid `False` survives public delegation unchanged.

### Validation

- Required narrow gate: `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_api_cli_entrypoints.py -k strict_phase_failures`
- Result: `2 passed, 36 deselected`

### Changed files

- `src/prism/api_layer/non_collection.py`
- `src/prism/scanner_core/execution_request_builder.py`
- `src/prism/scanner_plugins/bundle_resolver.py`
- `src/prism/scanner_core/scanner_context.py`
- `src/prism/scanner_data/contracts_request.py`
- `src/prism/tests/test_api_cli_entrypoints.py`
