# Builder-Typing wave 2 summary

- Finding: G66-H01
- Fix group: `scan-pipeline.protocol-facade-contract-alignment`
- Status: closed-ready pending foreman ledger/barrier update

## What changed

- Moved the canonical scan-pipeline contract surface into `scanner_plugins.interfaces` so the plugin interface layer now owns the shared plugin, orchestration, factory, payload, and runtime-registry types.
- Tightened the scan-pipeline contract away from `dict[str, Any]` at the public seam by using typed request metadata/options contracts plus a shared payload alias, while preserving the existing runtime behavior and isolation wrapper logic.
- Removed the facade-local duplicate scan-pipeline Protocol/factory/registry definitions in `api_layer.plugin_facade` and rewired the isolation wrapper to consume the interface-owned contract.
- Updated `api.py` and `scanner_core.execution_request_builder` to use the shared scan-pipeline runtime-registry contract for the API/runtime handoff instead of casting the isolated registry wrapper back to `PluginRegistry`.

## Validation

- Same-slice barrier repair (2026-05-04): aligned `api_layer.non_collection.run_scan()` to accept `plugin_facade.ScanPipelineRuntimeRegistry | None`, removed the redundant `ScanPipelineRuntimeRegistry` cast in `api.py`, and replaced `execution_request_builder`'s call to the concrete `scanner_core.di.resolve_platform_key()` helper with a local runtime-registry-compatible resolver that preserves the same selection order.
- Same-slice repair (2026-05-04): removed the unused `Any` import from `api_layer.plugin_facade` and replaced two stale `PluginRegistry` annotations in `scanner_core.execution_request_builder` with the interface-owned `ScanPipelineRuntimeRegistry` contract.
- Focused lint gate: `.venv/bin/python -m ruff check src/prism/scanner_plugins/interfaces.py src/prism/api_layer/plugin_facade.py src/prism/api.py src/prism/scanner_core/execution_request_builder.py src/prism/tests/test_plugin_kernel_extension_parity.py src/prism/tests/test_api_cli_entrypoints.py` -> `All checks passed!`
- Narrow gate: `pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k scan_pipeline` -> `7 passed, 24 deselected`
- Importer-layer gate: `pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'run_scan'` -> `24 passed, 11 deselected`

## Scope

- Scope expansion not needed.
- No H02 payload fail-closed behavior changes were made.

## Regression note

- No new common regression pattern identified beyond the existing H01 lesson: avoid redefining scan-pipeline Protocols in facade layers when the interface layer already owns the seam.
