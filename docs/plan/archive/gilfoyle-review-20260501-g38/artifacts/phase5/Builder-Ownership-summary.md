# Builder-Ownership Summary: FIND-G38-ARCH-01 and FIND-G35-ARCH-02

## Agent
Builder-Ownership (implementation worker)

## Owned File Set
- src/prism/api.py
- src/prism/tests/test_api_cli_entrypoints.py
- src/prism/tests/test_gilfoyle_blockers_runtime.py

## Summary Artifact Path
docs/plan/gilfoyle-review-20260501-g38/artifacts/phase5/Builder-Ownership-summary.md

## Changed Files
1. src/prism/api.py
2. src/prism/tests/test_api_cli_entrypoints.py
3. src/prism/tests/test_gilfoyle_blockers_runtime.py

## Status
**COMPLETE** - Both findings remediated successfully

## Work Performed

### FIND-G38-ARCH-01: API boundary registry authority split
**Remediation**: Removed module-level `DEFAULT_PLUGIN_REGISTRY` and `_get_default_plugin_registry()` from api.py. The `run_scan()` entrypoint now calls `plugin_facade.get_default_plugin_registry()` directly, eliminating the API-local registry split.

**Changes**:
- Removed lines 59-66 in api.py (module-level aliases and registry singleton)
- Updated `run_scan()` to pass `plugin_facade.get_default_plugin_registry()` directly to `api_non_collection.run_scan()`
- No new indirection added; delegation goes directly through canonical lower-layer seam

### FIND-G35-ARCH-02: API leaks internal assembly helpers
**Remediation**: Removed module-level aliases `build_run_scan_options_canonical` and `route_scan_payload_orchestration` from api.py. The `run_scan()` entrypoint now passes `api_non_collection.build_run_scan_options_canonical` and `api_non_collection.route_scan_payload_orchestration` directly.

**Changes**:
- Removed module-level aliases (lines 59-60 in api.py)
- Updated `run_scan()` to pass function references through `api_non_collection` directly
- Reduced public API surface; no accidental exposure of internal helpers

### Test Updates
Updated all owned test files to patch at the canonical lower-layer seams instead of the removed API-level aliases:

**test_api_cli_entrypoints.py**:
- Updated `_patch_api_default_registry()` to patch `plugin_facade.get_default_plugin_registry` instead of `api_module._get_default_plugin_registry`
- Changed 10 test monkeypatches from `api_module.route_scan_payload_orchestration` to `api_module.api_non_collection.route_scan_payload_orchestration`
- Updated 8 references from `api_module.DEFAULT_PLUGIN_REGISTRY` to `api_module.plugin_facade.get_default_plugin_registry()`

**test_gilfoyle_blockers_runtime.py**:
- Updated 1 test monkeypatch from `api_module._get_default_plugin_registry` to `api_module.plugin_facade.get_default_plugin_registry`

## Narrow Gate Command and Result
```bash
pytest -q src/prism/tests/test_api_cli_entrypoints.py src/prism/tests/test_gilfoyle_blockers_runtime.py -k 'run_scan or runtime_boom'
```

**Result**: ✅ 14 passed, 32 deselected in 1.31s

## Additional Importer-Layer Tests Run
```bash
# Full test suite for owned files
pytest -q src/prism/tests/test_api_cli_entrypoints.py
```
**Result**: ✅ 22 passed in 1.82s

```bash
pytest -q src/prism/tests/test_gilfoyle_blockers_runtime.py
```
**Result**: ✅ 24 passed in 1.23s

## Invariants Preserved
✅ Public entrypoints `scan_collection`, `scan_role`, `scan_repo`, and `run_scan` maintain identical external behavior
✅ Runtime registry authority now resolves through canonical `plugin_facade.get_default_plugin_registry()` seam
✅ Public API surface reduced; no accidental exposure of internal helpers
✅ Tests now patch at lower-layer seams (api_non_collection, plugin_facade) instead of API-level aliases

## Artifact Write
**ok**
