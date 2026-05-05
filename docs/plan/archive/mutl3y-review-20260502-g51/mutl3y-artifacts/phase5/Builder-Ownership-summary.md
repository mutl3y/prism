# Builder-Ownership Summary: G51-M01

**Agent:** Builder-Ownership
**Finding:** G51-M01 (registry_authority: defaults_loader_registry_resolution_split)
**Status:** Complete
**Date:** 2026-05-02

## Owned File Set

- src/prism/scanner_plugins/defaults.py
- src/prism/scanner_io/loader.py
- src/prism/tests/test_di_registry_resolution.py
- src/prism/tests/test_comment_doc_plugin_resolution.py

## Changes Summary

Consolidated duplicated registry resolution semantics between `defaults._resolve_registry` and `loader._resolve_plugin_registry` by extracting a shared `_get_registry_from_di` helper function.

### Key Changes

1. **Extracted shared seam** (`defaults.py`):
   - Added `_get_registry_from_di(di) -> PluginRegistry | None` that extracts `plugin_registry` from DI container
   - Refactored `_resolve_registry` to use shared helper while preserving bootstrap fallback behavior
   - Precedence remains: explicit registry > DI registry > bootstrap singleton

2. **Consolidated loader resolution** (`loader.py`):
   - Refactored `_resolve_plugin_registry` to delegate DI extraction to shared `_get_registry_from_di`
   - Preserved standalone loader contract: returns None when no DI registry (no bootstrap fallback)
   - Made fallback behavior difference explicit in docstring

3. **Added regression coverage** (`test_di_registry_resolution.py`):
   - `test_get_registry_from_di_shared_seam_returns_none_on_no_di`: shared helper returns None when di is None
   - `test_get_registry_from_di_shared_seam_returns_di_registry`: shared helper extracts DI.plugin_registry
   - `test_get_registry_from_di_shared_seam_returns_none_on_no_registry_attr`: shared helper returns None when no attr
   - `test_defaults_resolve_registry_uses_shared_seam`: defaults delegates to shared seam
   - `test_loader_resolve_plugin_registry_uses_shared_seam`: loader delegates to shared seam
   - `test_live_yaml_policy_resolution_preserves_loader_standalone_contract`: YAML policy resolution preserves loader contract

## Changed Files

- src/prism/scanner_plugins/defaults.py
- src/prism/scanner_io/loader.py
- src/prism/tests/test_di_registry_resolution.py

## Invariant Preservation

✅ Registry precedence stays explicit and consistent:

- `defaults._resolve_registry`: explicit > DI > bootstrap (always returns registry)
- `loader._resolve_plugin_registry`: DI only (returns None if no DI registry)

✅ Standalone loader contract unchanged:

- Loader does NOT fall back to bootstrap singleton
- Loader returns None when no DI registry is available
- YAML policy resolution continues to work in pre-scan discovery paths

✅ No fallback authority widening:

- Shared helper only extracts from DI, no bootstrap access
- Each consumer (defaults/loader) controls its own fallback behavior

## Gate Results

**Narrow gate:** PASS

```text
pytest -q src/prism/tests/test_di_registry_resolution.py -k 'loader_registry_resolution or live_yaml_policy_resolution'
3 passed in 0.41s
```

**New regression tests:** PASS (5/5)

```text
test_get_registry_from_di_shared_seam_returns_none_on_no_di
test_get_registry_from_di_shared_seam_returns_di_registry
test_get_registry_from_di_shared_seam_returns_none_on_no_registry_attr
test_defaults_resolve_registry_uses_shared_seam
test_loader_resolve_plugin_registry_uses_shared_seam
```

**Comment doc plugin resolution:** PASS (60/60)

**Scanner core DI yaml_parsing:** PASS (4/4)

## Scope Expansion

None required. All work completed within owned file set.
