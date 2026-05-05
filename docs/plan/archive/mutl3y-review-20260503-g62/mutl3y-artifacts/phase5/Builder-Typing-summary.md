Builder-Typing wave 3 summary

- Finding: G62-H02
- Fix group: prepared-policy-bundle.dict-acceptance
- Owned scope: src/prism/scanner_core/scanner_context.py, src/prism/tests/test_scanner_context.py
- Invariant preserved: ScannerContext still fails closed on missing or malformed prepared policy state without mutating ingress scan_options and without widening the prepared policy contract.
- Change summary: tightened ScannerContext runtime validation so prepared_policy_bundle only accepts task_line_parsing values with the canonical task-line policy members and jinja_analysis values with the canonical Jinja analyzer member; updated direct tests to assert fail-closed rejection for malformed dict placeholders.
- Narrow gate: `pytest -q src/prism/tests/test_scanner_context.py -k 'requires_prepared_policy_bundle_without_mutating_ingress_options or prepared_policy_bundle_rejects_invalid_bundle'` -> 3 passed, 16 deselected
- Importer-layer gate: `.venv/bin/python -m mypy src/prism/scanner_core/scanner_context.py src/prism/tests/test_scanner_context.py` -> Success: no issues found in 2 source files
- Scope expansion: none
- Regression pattern candidate: runtime TypeGuard helpers for TypedDict-carried protocol instances must validate the required protocol surface, not only `isinstance(value, dict)`.
