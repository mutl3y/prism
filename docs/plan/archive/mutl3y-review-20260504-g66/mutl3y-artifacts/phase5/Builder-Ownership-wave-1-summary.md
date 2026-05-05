# Builder-Ownership Wave 1 Summary

- Finding: `G66-H04`
- Fix group: `api.scanner_core_assembly_symbol_leak`
- Invariant preserved: the public api facade no longer exposes raw scanner-core assembly classes as patch points, and the comment-doc role-notes seam remains injectable through an api-owned resolver contract.
- Code change: `src/prism/api.py` now exposes api-owned wrapper classes for `DIContainer`, `FeatureDetector`, and `ScannerContext` instead of re-exporting the raw scanner-core classes, and `run_scan()` now routes comment-doc plugin resolution through the api-owned `resolve_comment_driven_documentation_plugin()` seam.
- Test change: `src/prism/tests/test_comment_doc_plugin_resolution.py` now patches the api-owned resolver seam instead of monkeypatching `api.DIContainer`, and adds a regression guard that asserts the facade-owned runtime seam classes are not the raw `prism.scanner_core` identities.
- Validation:
  - `pytest -q src/prism/tests/test_comment_doc_plugin_resolution.py::test_run_scan_metadata_role_notes_uses_comment_doc_plugin_seam` -> PASS
  - `pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'run_scan'` -> PASS (`24 passed, 11 deselected`)
  - `pytest -q src/prism/tests/test_comment_doc_plugin_resolution.py -k 'api_public_facade_owns_scanner_core_runtime_seams'` -> PASS (`1 passed, 62 deselected`)
- Status: closed-ready for foreman review within owned scope.
