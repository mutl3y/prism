- Code changes
  - Tightened non-strict defaults fallback in `scanner_plugins.defaults` so Ansible-only fallback plugins are rejected when DI scan options select a non-Ansible platform, instead of silently substituting Ansible defaults.
  - Kept registry authority aligned with DI ingress by deriving fallback safety from the same platform-selection chain used by `resolve_platform_key`.
  - Moved `ensure_prepared_policy_bundle_fn` validation to `_assemble_execution_request()` so missing enforcement fails before runtime participant assembly starts.
  - Added focused regressions for wrong-platform malformed-plugin fallback and the earlier execution-request fail-fast point.

- Touched files
  - `src/prism/scanner_plugins/defaults.py`
  - `src/prism/scanner_core/execution_request_builder.py`
  - `src/prism/tests/test_comment_doc_plugin_resolution.py`
  - `src/prism/tests/test_di_registry_resolution.py`
  - `src/prism/tests/test_execution_request_builder.py`

- Validation
  - `pytest -q src/prism/tests/test_comment_doc_plugin_resolution.py::test_task_line_plugin_validation_falls_back_in_non_strict_mode src/prism/tests/test_comment_doc_plugin_resolution.py::test_task_annotation_plugin_validation_falls_back_in_non_strict_mode src/prism/tests/test_comment_doc_plugin_resolution.py::test_task_line_plugin_validation_rejects_wrong_platform_fallback src/prism/tests/test_comment_doc_plugin_resolution.py::test_task_annotation_plugin_validation_rejects_wrong_platform_fallback src/prism/tests/test_di_registry_resolution.py::test_get_registry_from_di_shared_seam_returns_none_on_no_di src/prism/tests/test_di_registry_resolution.py::test_defaults_non_strict_fallback_uses_selected_platform_authority src/prism/tests/test_execution_request_builder.py::TestRuntimeAssemblySeam::test_execution_request_finalization_seam_requires_prepared_policy_enforcement` -> `7 passed`
  - `pytest -q src/prism/tests/test_scanner_context.py::test_fsrc_scanner_core_builds_non_collection_execution_request src/prism/tests/test_t1_02_coverage_lift_batch3.py::test_parse_yaml_candidate_uses_default_policy src/prism/tests/test_platform_execution_bundle.py src/prism/tests/test_defaults.py -k 'strict or malformed or fallback'` -> `3 passed, 12 deselected` (filter applied too broadly for `test_platform_execution_bundle.py`, so the remaining importer checks were rerun separately)
  - `pytest -q src/prism/tests/test_platform_execution_bundle.py && pytest -q src/prism/tests/test_defaults.py -k 'strict or malformed or fallback'` -> `9 passed`; then `3 passed, 1 deselected`

- Finding status
  - `G58-H03`: closure-ready
  - `G58-H04`: closure-ready within owned scope; defaults fallback now follows the selected platform authority instead of silently borrowing Ansible defaults.
  - `G58-H05`: closure-ready

## Post-Wave-3 regression repair

- Repaired the local `_Container` test double in `src/prism/tests/test_di_registry_resolution.py` so the execution-request seam accepts `inherit_default_event_listeners`, matching the runtime constructor contract introduced in Wave 2.
- Repaired `src/prism/scanner_plugins/defaults.py` by inlining the DI-ingress platform-selection chain locally instead of importing `resolve_platform_key` from `prism.scanner_core.di`, preserving fallback behavior without violating the plugin-layer boundary.
- Validation: `pytest -q src/prism/tests/test_di_registry_resolution.py::test_execution_request_builder_uses_default_registry_over_scan_options_bypass src/prism/tests/test_plugin_kernel_extension_parity.py::test_fsrc_scanner_plugins_package_does_not_import_scanner_core` -> `2 passed in 0.25s`
