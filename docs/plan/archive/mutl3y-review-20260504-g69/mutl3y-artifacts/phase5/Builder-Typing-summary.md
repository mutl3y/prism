# Builder-Typing Summary

- Plan ID: mutl3y-review-20260504-g69
- Cycle: g69
- Wave: 3
- Fix group: plugin-interfaces.canonical-contract-typing
- Finding: G69-H02
- Scope: `src/prism/scanner_plugins/interfaces.py`, `src/prism/scanner_plugins/ansible/__init__.py`, `src/prism/tests/test_platform_execution_bundle.py`
- Model: GPT-5.4

## Change

Tightened the public scan-pipeline and execution-bundle protocol surfaces to use canonical request and metadata contracts where this seam already has them: `PlatformExecutionBundleProvider.build_execution_bundle()` now accepts `ScanOptionsDict`, the ansible scan-pipeline implementation now advertises `ScanOptionsDict`, `ScanMetadata`, `ScanPipelinePreflightContext`, and `ScanPipelinePayload`, and the shared preflight TypedDict now includes the runtime-stable `ansible_plugin_enabled` flag already emitted by the ansible plugin.

The fix stayed inside the owned slice and did not widen into the ansible kernel lifecycle seam. The scan-pipeline payload alias remained `dict[str, object]` because the runtime payload metadata still carries plugin-routing fields beyond the narrower output-payload contract, so narrowing that alias would have misdescribed the live seam.

## Tests

- Added a focused contract test that inspects public annotations directly and verifies the owned protocol and ansible implementation expose the canonical typed surfaces.
- Preserved the existing execution-bundle behavior checks.

## Validation

- `.venv/bin/python -m mypy src/prism/scanner_plugins/interfaces.py src/prism/scanner_plugins/ansible/__init__.py`
  - PASS
- `.venv/bin/python -m pytest -q src/prism/tests/test_platform_execution_bundle.py`
  - PASS (`10 passed`)

## Outcome

G69-H02 is closed-ready from the owned typing slice. No scope expansion was required.
