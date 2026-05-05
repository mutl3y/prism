# Probe-ControlFlow: G71-H01

Smallest coherent first wave: remove the runtime variable-discovery path from the standalone loader seam, but leave the standalone loader API in place.

## Recommended owned file set

- `src/prism/scanner_plugins/ansible/variable_discovery.py`
- `src/prism/tests/test_variable_discovery_pipeline.py`

## Why this is the smallest coherent slice

`src/prism/scanner_plugins/ansible/variable_discovery.py` is the active runtime consumer that still reaches into `scanner_io.loader.load_yaml_file(...)` for defaults, vars, include-vars payloads, and argument-spec YAML, even though the same runtime slice already requires ingress `prepared_policy_bundle` for task-line and Jinja policy. That makes this plugin the smallest place where ownership can be tightened without changing the intentional standalone loader contract used by pre-bootstrap discovery helpers. `src/prism/scanner_io/loader.py` should stay untouched in the first wave because current tests prove its no-bundle fallback is still the deliberate standalone contract, not accidental runtime behavior.

## Boundary to preserve

Allowed standalone fallback: callers that are intentionally pre-bootstrap or standalone and may run without an ingress-prepared bundle may continue to use `scanner_io.loader.load_yaml_file(...)` / `parse_yaml_candidate(...)`, with DI-registry-aware fallback and no bootstrap-registry widening beyond the current documented behavior.

Disallowed runtime ownership reopening: canonical runtime execution that already requires `prepared_policy_bundle` to exist must not route YAML parsing authority back through `scanner_io.loader._get_yaml_parsing_policy(...)`. In this finding, that means Ansible variable discovery should load YAML through the already-ingress-owned prepared `yaml_parsing` policy, just as task-file traversal already does.

## Deferred files

- `src/prism/scanner_io/loader.py`
- `src/prism/scanner_extract/discovery.py`
- `src/prism/tests/test_di_registry_resolution.py`
- `src/prism/tests/test_comment_doc_plugin_resolution.py`

## Cheapest discriminating validation

Primary nearby tests:

- existing boundary proof: `src/prism/tests/test_di_registry_resolution.py::test_live_yaml_policy_resolution_preserves_loader_standalone_contract`
- existing runtime-boundary proof: `src/prism/tests/test_variable_discovery_pipeline.py::test_fsrc_variable_discovery_requires_ingress_prepared_policy_bundle`
- cheapest first-wave addition: a new focused regression in `src/prism/tests/test_variable_discovery_pipeline.py` asserting variable-discovery YAML loads use `prepared_policy_bundle.yaml_parsing` and do not fall back to loader-side resolver authority

Recommended narrow gate:

```bash
.venv/bin/python -m pytest -q src/prism/tests/test_di_registry_resolution.py::test_live_yaml_policy_resolution_preserves_loader_standalone_contract src/prism/tests/test_variable_discovery_pipeline.py::test_fsrc_variable_discovery_requires_ingress_prepared_policy_bundle src/prism/tests/test_variable_discovery_pipeline.py::test_fsrc_variable_discovery_yaml_loading_prefers_prepared_policy_bundle
```

## Probe conclusion

The best first wave is not a loader rewrite; it is a local runtime-routing fix in `src/prism/scanner_plugins/ansible/variable_discovery.py`. Existing evidence already brackets the intended distinction: the standalone loader fallback is live and tested, while the canonical runtime traversal path already prefers prepared policy and variable discovery already rejects missing ingress bundles. That means the exact defect is runtime variable discovery reopening YAML policy ownership through the standalone helper after ingress policy preparation should already control the slice. After this first wave, G71-H01 should be demoted rather than closed: the high-severity runtime reopening is reduced, but the shared standalone loader contract remains intentionally separate and should only be revisited in a later explicit standalone-loader API decision. One extra note from the probe: the finding's current suggested gate points to a missing `src/prism/tests/test_yaml_policy_resolution.py`, so the active plan should switch to live tests in `test_variable_discovery_pipeline.py` and `test_di_registry_resolution.py`.
