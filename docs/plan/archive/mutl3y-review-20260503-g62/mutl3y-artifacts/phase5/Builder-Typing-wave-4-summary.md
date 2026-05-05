# Builder-Typing Wave 4 Summary

- Task: `g62-wave4-builder-typing`
- Finding: `G62-H02`
- Fix group: `prepared-policy-bundle.dict-acceptance`
- Invariant preserved: non-collection cache-key metadata still distinguishes missing versus malformed prepared policy bundle state, does not fingerprint malformed dict placeholders as valid prepared bundles, does not mutate ingress scan options, and does not relax the stricter `scanner_context` fail-closed boundary.
- Implementation: tightened `src/prism/api_layer/non_collection.py` cache-marker validation so only bundle shapes that satisfy the canonical `task_line_parsing` and `jinja_analysis` prepared-policy members receive a fingerprint; invalid dict placeholders now emit `__prepared_policy_bundle_state__ = "malformed"`.
- Tests: added direct entrypoint coverage in `src/prism/tests/test_api_cli_entrypoints.py` for malformed prepared policy bundle cache-state handling alongside the existing missing-state assertion.
- Narrow gate: `pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'prepared_policy_bundle_state'` -> `2 passed, 31 deselected`.
- Optional importer gate: `.venv/bin/python -m mypy src/prism/api_layer/non_collection.py src/prism/tests/test_api_cli_entrypoints.py` -> `Success: no issues found in 2 source files`.
- Scope expansion: none.
- Regression pattern: cache-key helpers must validate prepared-policy bundle member shape before fingerprinting dict-valued placeholders, or malformed ingress state becomes indistinguishable from canonical prepared bundles.
