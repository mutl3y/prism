# Builder-ControlFlow Wave 1 Summary

- Task: `g64-wave1-builder-controlflow`
- Finding: `G64-H01`
- Owned scope: `src/prism/scanner_io/loader.py`, `src/prism/tests/test_di_registry_resolution.py`

## Change

Collapsed `loader._get_yaml_parsing_policy()` to a single registry-authority decision by routing the fallback path through `_resolve_policy_with_registry(...)` instead of re-implementing the registry/no-registry branch inline. This keeps the loader path explicit about the DI-derived registry it resolved while preserving the standalone contract when no DI registry exists.

## Test coverage

Updated the focused YAML policy regression to assert `_get_yaml_parsing_policy()` passes the loader-resolved `DI.plugin_registry` explicitly into `defaults.resolve_yaml_parsing_policy_plugin(...)` and does not treat `scan_options["plugin_registry"]` as an alternate authority.

## Validation

- `pytest -q src/prism/tests/test_di_registry_resolution.py -k 'yaml_policy_resolution'` -> `2 passed, 28 deselected`
