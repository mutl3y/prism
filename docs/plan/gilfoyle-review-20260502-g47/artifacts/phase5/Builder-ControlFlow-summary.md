# Builder-ControlFlow Summary

- Findings addressed: `G46-H10`, `G46-H13`
- Owned files changed: `src/prism/scanner_plugins/defaults.py`, `src/prism/tests/test_comment_doc_plugin_resolution.py`
- Concise changes: malformed prepared-policy plugins in `scanner_plugins.defaults` now raise explicit `PrismRuntimeError(code="malformed_plugin_shape")` even when `strict_mode=False`, instead of substituting fallback plugins after construction or shape faults.
- Concise changes: `scanner_plugins.defaults` helper flows no longer fabricate a standalone DI/prepared-policy runtime path; comment-doc helper calls without a canonical DI context now fail closed, and the owned tests were updated to assert the new fail-closed behavior.
- Gate result: `pytest -q src/prism/tests/test_comment_doc_plugin_resolution.py src/prism/tests/test_platform_routing_fail_closed.py` -> slice fixes passed, but the gate still has one unrelated failure in `src/prism/tests/test_comment_doc_plugin_resolution.py::test_run_scan_metadata_role_notes_uses_comment_doc_plugin_seam` because `api.run_scan()` currently fails with `PrismRuntimeError(code="scan_pipeline_plugin_disabled")` from `src/prism/scanner_kernel/orchestrator.py`, which is outside this worker's allowed write set.
