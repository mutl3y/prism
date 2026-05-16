# Builder-CollectionRunbook Summary

Plan: g84-remediation-mutl3y-cycle-20260509
Wave: rem-2
Worker: Builder-CollectionRunbook
Artifact recovery: recovered by foreman from worker receipt (worker returned success without writing summary file).

## Changed Files
- src/prism/api.py

## Change
- Restored monkeypatchable collection runbook seam by passing module-level `write_collection_runbook_artifacts` into `api_collection.scan_collection` instead of an inline lambda that called the facade directly.

## Narrow Gate
- Command: `PYTHONPATH=src .venv/bin/python -m pytest src/prism/tests/test_collection_contract.py::test_fsrc_api_scan_collection_demotes_invalid_metadata_on_runbook_path -q`
- Result: `1 passed`

## Rationale
- The failing test monkeypatches `prism.api.write_collection_runbook_artifacts`; prior lambda bypassed this seam and reached Jinja template rendering with invalid metadata. Using the module-level seam restores expected demotion path while preserving API behavior.
