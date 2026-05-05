Builder: Foreman-Recovery
Cycle: g56
Wave: 1

Owned files:

- src/prism/scanner_plugins/defaults.py
- src/prism/tests/test_defaults.py
- src/prism/tests/test_comment_doc_plugin_resolution.py
- src/prism/tests/test_plugin_kernel_extension_parity.py
- src/prism/tests/test_gilfoyle_blockers_runtime.py
- src/prism/scanner_extract/variable_extractor.py
- src/prism/tests/test_hypothesis_yaml_parser.py
- src/prism/cli.py
- src/prism/scanner_plugins/bundle_resolver.py
- src/prism/scanner_plugins/ansible/feature_flags.py
- src/prism/tests/test_plugin_extract_boundary.py
- src/prism/tests/test_package_export_parity.py

Changes landed:

- Repaired the non-strict defaults fallback seam for G56-H01 and updated the nearest fallback-contract tests.
- Repaired adjacent stale guardrail tests to match the restored fallback and routing behavior.
- Restored graceful degradation for corrupt optional seed YAML by catching the wrapped loader error channel.
- Aligned the YAML parser property test with the documented yaml_load_error contract.
- Removed the forbidden CLI import of api_layer.plugin_facade by routing the audit helper through scanner_plugins.audit.
- Synchronized DI scan_options after prepared policy bundle resolution so feature-detector and task-traversal hot paths see the prepared bundle.
- Removed the private kernel constant import from the ansible feature-flags helper.
- Updated two stale guardrail ledgers: defaults.py is no longer treated as an extract-utils caller, and scanner_data export parity now includes the collection runtime contracts already exported by the package.

Focused validation:

- docs/plan/mutl3y-review-20260503-g56/.mutl3y-gate/phase5-wave1-focused.log: 8 passed
- docs/plan/mutl3y-review-20260503-g56/.mutl3y-gate/phase5-wave1-ruff.log: pass
- docs/plan/mutl3y-review-20260503-g56/.mutl3y-gate/phase5-wave1-black.log: pass after formatter recovery
- docs/plan/mutl3y-review-20260503-g56/.mutl3y-gate/phase5-wave1-mypy.log: unchanged external baseline in scanner_core/metadata_merger.py
