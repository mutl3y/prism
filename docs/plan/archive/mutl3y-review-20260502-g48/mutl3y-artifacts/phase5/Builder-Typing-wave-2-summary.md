# Builder-Typing Wave 2 Summary

- Agent: Builder-Typing
- Plan ID: mutl3y-review-20260502-g48
- Finding: G48-M02
- Scope: owned typing/public-runtime-contract files only

## Changes

- Tightened scanner-core runtime protocols so the kernel boundary now uses explicit request/response/phase-output contracts instead of `Any`-typed callable edges.
- Removed the kernel runner's cast-based plugin lifecycle dispatch list and replaced it with runtime-checked phase handler adaptation that preserves the existing skipped-phase behavior.
- Replaced `dict(...)` copying at the scan-pipeline plugin execution seam with `copy.copy(...)` so TypedDict-shaped runtime inputs are preserved without lossy conversion.
- Narrowed collection API-layer protocol contracts to concrete public scanner-data contracts (`CollectionIdentity`, `CollectionDependencies`, `CollectionPluginCatalog`, `CollectionRoleEntry`, `CollectionFailureRecord`, `RunScanOutputPayload`, `ScanMetadata`).
- Expanded `prism.scanner_data` exports so the collection subcontracts are public and testable as part of the runtime surface.

## Validation

- Required narrow gate: `pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py src/prism/tests/test_api_cli_entrypoints.py` -> `58 passed`
- Additional focused importer-layer check: `pytest -q src/prism/tests/test_kernel_plugin_runner.py src/prism/tests/test_plugin_name_resolver.py` -> `15 passed`

## Scope

- No scope expansion needed.
- No new common-traps addition identified beyond the existing TypedDict-copy guidance.
