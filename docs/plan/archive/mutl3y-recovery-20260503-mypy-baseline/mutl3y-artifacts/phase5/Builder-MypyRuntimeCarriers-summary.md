# Builder-MypyRuntimeCarriers Summary

- Agent: Builder-MypyRuntimeCarriers
- Scope: `src/prism/scanner_core/execution_request_builder.py`, `src/prism/scanner_kernel/orchestrator.py`, `src/prism/api_layer/non_collection.py`, `src/prism/tests/test_kernel_plugin_runner.py`, `src/prism/tests/test_readme_renderer_registry_wiring.py`

## Changes

- Tightened the non-collection execution request carrier so runtime registry fields now use `PluginRegistry`, and wrapped `scanner_context.orchestrate_scan()` at the request boundary as a `RunScanOutputPayload` builder.
- Kept kernel preflight/runtime carriers inside the `ScanMetadata` and `ScanPipelineRouting` contracts instead of smuggling extra `plugin_name` state through metadata.
- Updated non-collection orchestration adapters to pass `ScanOptionsDict` and `ScanMetadata` through the kernel/plugin seam without downgrading to plain `dict[str, object]`.
- Added local typed narrowing helpers in the owned tests so kernel error payloads and default-registry access no longer rely on object-typed indexing or module `__getattr__` inference.

## Validation

- Focused mypy command run repeatedly on the owned set.
- Final focused mypy status for owned files: no remaining owned-file errors.
- Remaining blockers on the exact command are out of scope:
  - `src/prism/scanner_core/task_extract_adapters.py:183`
  - `src/prism/api_layer/plugin_facade.py:39`
- Nearby pytest bundle: `.venv/bin/python -m pytest -q src/prism/tests/test_kernel_plugin_runner.py src/prism/tests/test_readme_renderer_registry_wiring.py`
- Pytest result: `23 passed in 0.35s`
