Builder-RecoveryLintFix — concise summary

Edits made:

- src/prism/api_layer/non_collection.py: replaced stale type annotation `_NormalizedRunScanPayload` with `_NormalizedNonCollectionResult` (3 occurrences).
- src/prism/scanner_kernel/orchestrator.py: removed unused import `execute_scan_pipeline_plugin` to address F401.
- Formatted owned files that had Black drift (see list).

Files reformatted by Black:

- src/prism/scanner_plugins/__init__.py
- src/prism/scanner_core/scan_cache.py
- src/prism/scanner_core/di.py
- src/prism/scanner_plugins/defaults.py
- src/prism/scanner_plugins/registry.py
- src/prism/tests/test_di_registry_resolution.py

Validation results:

- `ruff check` on modified files: All checks passed for `src/prism/api_layer/non_collection.py` and `src/prism/scanner_kernel/orchestrator.py`.
- `black --check` on owned file set: initially 6 files would be reformatted; after formatting, `black --check` reports all owned files are clean.

Changed files:

- src/prism/api_layer/non_collection.py
- src/prism/scanner_kernel/orchestrator.py
- src/prism/scanner_plugins/__init__.py (reformatted)
- src/prism/scanner_core/scan_cache.py (reformatted)
- src/prism/scanner_core/di.py (reformatted)
- src/prism/scanner_plugins/defaults.py (reformatted)
- src/prism/scanner_plugins/registry.py (reformatted)
- src/prism/tests/test_di_registry_resolution.py (reformatted)

Status: SUCCESS — lint errors addressed; owned files formatted and black-clean.
