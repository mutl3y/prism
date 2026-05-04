# Fresh Review Remediation Wave A

Date: 2026-05-04
Plan: `mutl3y-review-20260504-g73`

## Scope

- Closed `FIR-H01` by unifying platform selector precedence across kernel-adjacent runtime assembly and DI.
- Closed `FIR-H04` by preserving orchestration support for callable factories returned from isolated scan-pipeline registries.
- Reduced the folded cache-risk slices under `G73-H04`/`G73-H05` by adding registry state fingerprints to runtime wiring identity and making stateful prepared-policy bundles bypass cache use unless they expose a semantic fingerprint.

## Validation

```text
.venv/bin/python -m pytest -q src/prism/tests/test_scanner_core_di.py src/prism/tests/test_execution_request_builder.py -k 'platform_option or authoritative_registry or from_policy_context'
4 passed, 78 deselected

.venv/bin/python -m pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'plugin_facade_isolates_orchestrated_payload_mutation or preserves_orchestration_for_callable_factories'
2 passed, 38 deselected

.venv/bin/python -m pytest -q src/prism/tests/test_t3_03_scan_cache.py src/prism/tests/test_api_cli_entrypoints.py -k 'runtime_wiring_identity or registry_state_revision or cache_key_tracks_runtime_wiring_identity'
3 passed, 56 deselected

.venv/bin/python -m pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'missing_prepared_policy_bundle_state or malformed_prepared_policy_bundle_state or uncacheable_prepared_policy_bundle'
3 passed, 38 deselected
```
