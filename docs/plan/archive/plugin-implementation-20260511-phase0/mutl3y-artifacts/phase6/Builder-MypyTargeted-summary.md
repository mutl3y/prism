# Builder Mypy Targeted Summary

## Scope

Owned files:
- `src/prism/api.py`
- `src/prism/scanner_core/di.py`
- `src/prism/scanner_core/scanner_context.py`
- `src/prism/tests/test_scanner_parity.py`
- `src/prism/tests/test_policy_integration.py`
- `src/prism/scanner_core/marker_prefix_contract.py`
- `src/prism/scanner_core/marker_prefix_enforcer.py`

## Mypy Counts

Owned-file mypy errors before edits: 0
Owned-file mypy errors after edits: 0

Repo-wide mypy errors after the slice: 93 errors in 17 files

## What Changed

- Removed the leftover overload stubs in `src/prism/scanner_core/di.py` so the concrete factory implementations are the only visible definitions.
- Tightened `src/prism/api.py` collection write helpers to use `ScanMetadata` at the facade boundary.
- Cast the optional CLI output only at the API seam in `src/prism/api.py` so the wrapper still accepts nullable output without widening downstream signatures.
- Made the mutable `policy_context` mutation in `src/prism/tests/test_policy_integration.py` explicit with a local `dict[str, object]` cast before the test mutates it.

## Remaining Non-Owned Mypy Debt

Current repo-wide debt is concentrated in these categories:
- scanner-extract protocol/attribute mismatch errors in `task_annotation_parsing.py`, `task_line_parsing.py`, `task_file_traversal.py`, and `task_catalog_assembly.py`
- marker-prefix policy return-type mismatch in `scanner_plugins/marker_prefix_policy.py`
- missing generic type variables in `scanner_io/loader.py`
- plugin resolver and service locator overload-stub cleanup needed in `scanner_core/plugin_resolver.py` and `scanner_core/service_locator.py`
- ansible feature-detection argument narrowing mismatches in `scanner_plugins/ansible/feature_detection.py`
- several TypedDict test-fixture mismatches and protocol alignment issues in `test_t1_02_coverage_lift_batch2.py`, `test_t1_02_coverage_lift_batch3.py`, `test_kernel.py`, `test_execution_request_builder.py`, `test_di_type_safety.py`, `test_mp1_compatibility.py`, and `test_plugin_kernel_extension_parity.py`
- one remaining typed container annotation issue in `test_real_world_scans.py`

## Test Status

- Targeted pytest: `27 passed, 6 skipped`
- The touched test slice is green after the edits.
- The owned-file mypy slice is clean.
