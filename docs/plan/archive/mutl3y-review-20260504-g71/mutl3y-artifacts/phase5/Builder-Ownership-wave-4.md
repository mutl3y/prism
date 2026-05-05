# Builder-Ownership Wave 4

- Plan ID: `mutl3y-review-20260504-g71`
- Cycle: `g71`
- Wave: `4`
- Fix group: `variable-discovery.yaml-policy-ingress`
- Finding: `G71-H01`

## Scope

- Owned runtime change only in `src/prism/scanner_plugins/ansible/variable_discovery.py`
- Focused regression coverage only in `src/prism/tests/test_variable_discovery_pipeline.py`

## Implemented change

- Added a local `prepared_policy_bundle.yaml_parsing` getter in Ansible variable discovery and made canonical runtime YAML loads require that ingress-prepared policy.
- Routed `_load_yaml_mapping_with_metadata(...)` through the prepared YAML policy's `load_yaml_file(...)` and `parse_yaml_candidate(...)` members instead of reopening authority through `scanner_io.loader` fallback helpers.
- Threaded `options` through the local variable-discovery helper chain so defaults, vars, include-vars, and argument-spec YAML all stay on the ingress-prepared runtime path.
- Preserved the shared standalone loader contract by leaving `src/prism/scanner_io/loader.py` unchanged.

## Test changes

- Renamed and strengthened the focused regression to `test_fsrc_variable_discovery_yaml_loading_prefers_prepared_policy_bundle`.
- The regression now proves canonical variable discovery uses the prepared YAML policy for both task traversal and included vars loading, while the standalone loader fallback remains guarded by the existing DI registry resolution test.

## Validation

Command:

```bash
cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_di_registry_resolution.py::test_live_yaml_policy_resolution_preserves_loader_standalone_contract src/prism/tests/test_variable_discovery_pipeline.py::test_fsrc_variable_discovery_requires_ingress_prepared_policy_bundle src/prism/tests/test_variable_discovery_pipeline.py::test_fsrc_variable_discovery_yaml_loading_prefers_prepared_policy_bundle
```

Result:

```text
3 passed in 0.43s
```

## Recommendation

- Finding status: `demote`
- Rationale: the active high-severity runtime reopening in canonical variable discovery is removed, while the intentional standalone loader seam remains explicitly preserved for later review.
