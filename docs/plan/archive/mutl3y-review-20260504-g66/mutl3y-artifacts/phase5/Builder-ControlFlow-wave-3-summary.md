Builder-ControlFlow closed the G66-H02 fail-closed payload handoff slice inside the owned seam.

- execution_request_builder now rejects malformed role-notes buckets, invalid display-variable rows, non-string external-collections payloads, and malformed yaml-parse-failure rows instead of normalizing them into defaults.
- scanner_context now rejects non-dict metadata, non-dict display_variables payloads, malformed metadata.role_notes, and invalid requirements_display payloads instead of coercing them into empty containers.
- owned regressions were added for malformed role notes, display variables, metadata, external collections, and yaml parse failures.
- owned execution_request_builder test doubles were updated to return canonical empty role-notes buckets so the suite exercises the tightened contract rather than hidden fail-open defaults.

Validation:

- `pytest -q src/prism/tests/test_execution_request_builder.py src/prism/tests/test_scanner_context.py` -> 45 passed
- `pytest -q src/prism/tests/test_execution_request_builder.py src/prism/tests/test_scanner_context.py -k "role_notes or display_variables or metadata or external_collections"` -> 11 passed, 34 deselected
- same-slice repair after the refreshed wave-3 barrier: `_normalize_role_notes()` now validates each `RoleNotes` bucket through literal-key reconstruction instead of iterating TypedDict keys and assigning through a variable key, preserving the fail-closed H02 handoff without widening the contract.
- `python -m mypy src/prism/scanner_core/execution_request_builder.py` -> success: no issues found in 1 source file
- `python -m pytest -q src/prism/tests/test_execution_request_builder.py src/prism/tests/test_scanner_context.py` -> 45 passed in 1.25s

Regression pattern worth tracking: test doubles that return `{}` for structured role-notes payloads can hide fail-open coercion at the builder-to-ScannerContext boundary; canonical empty-bucket payloads should be used instead.
