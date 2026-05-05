# Probe-Ownership: G71-H04

Smallest coherent first wave: tighten the active task-catalog boundary only.

## Recommended owned file set

- `src/prism/scanner_plugins/interfaces.py`
- `src/prism/scanner_core/feature_detector.py`
- `src/prism/scanner_plugins/ansible/feature_detection.py`
- `src/prism/tests/test_feature_detector.py`

## Why this is the smallest coherent slice

`FeatureDetectionPlugin.analyze_task_catalog` is the only clearly active `dict[str, Any]`-style plugin boundary in `interfaces.py` that already has a concrete shaped implementation and adjacent assertions. The concrete return shape is local and stable in `src/prism/scanner_plugins/ansible/feature_detection.py` via `_TaskCatalogEntry`, and `src/prism/scanner_core/feature_detector.py` currently widens that same boundary back to `dict[str, dict[str, Any]]`. `src/prism/tests/test_feature_detector.py` already checks both the catalog key set and the plugin-routed path, so this slice can tighten one runtime seam without reopening registry, DI, or multi-platform plugin design.

## Active boundary debt vs intentionally generic surfaces

### Real active boundary debt

- `FeatureDetectionPlugin.analyze_task_catalog` in `src/prism/scanner_plugins/interfaces.py`: active runtime boundary; concrete shape already exists in the Ansible implementation and is asserted by `test_fsrc_feature_detector_task_catalog_shape_parity` plus `test_fsrc_feature_detector_routes_via_plugin_when_available`.
- `ReadmeRendererPlugin.render_section_body` and `ReadmeRendererPlugin.render_identity_section` in `src/prism/scanner_plugins/interfaces.py`: real debt, but not a first-wave ownership fit. They are exercised through `src/prism/scanner_readme/guide.py`, `src/prism/scanner_readme/render.py`, `src/prism/scanner_plugins/ansible/readme_renderer.py`, and multiple protocol/parity tests, so tightening them pulls a visibly broader reporting/rendering slice.

### Intentionally generic or currently not worth first-wave tightening

- `VariableDiscoveryPlugin` option parameters: the return contracts are already specific enough, but `options: dict[str, Any]` is still the live mutable scan-options bag consumed across discovery logic (`include_vars_main`, excludes, yaml failure accumulation, policy bundle data). Tightening this in a small wave would reopen broader scan-options ownership instead of one boundary.
- `FeatureDetectionPlugin.detect_features`: return type is already `FeaturesContext`; the remaining generic input bag is secondary to `analyze_task_catalog` because the output side is already typed and stable.
- `OutputOrchestrationPlugin.orchestrate_output`: currently protocol-only and registry-facing; no concrete implementation or runtime callsite was found in `src/prism`, so it is dormant interface debt rather than active boundary risk.
- `ScanPipelinePayload` / scan-pipeline orchestration payloads: intentionally generic cross-platform carrier surfaces by design.

## Deferred files

- `src/prism/scanner_plugins/ansible/readme_renderer.py`
- `src/prism/scanner_readme/guide.py`
- `src/prism/scanner_readme/render.py`
- `src/prism/scanner_reporting/report.py`
- `src/prism/scanner_data/contracts_output.py`
- `src/prism/scanner_core/variable_discovery.py`
- `src/prism/scanner_plugins/ansible/variable_discovery.py`

## Cheapest discriminating validation

Primary nearby tests:

- `src/prism/tests/test_feature_detector.py::test_fsrc_feature_detector_task_catalog_shape_parity`
- `src/prism/tests/test_feature_detector.py::test_fsrc_feature_detector_routes_via_plugin_when_available`

Recommended narrow gate:

```bash
.venv/bin/python -m mypy src/prism/scanner_plugins/interfaces.py src/prism/scanner_core/feature_detector.py src/prism/scanner_plugins/ansible/feature_detection.py
```

Probe conclusion: the smallest materially useful ownership slice is the task-catalog path, not the whole interface module. `analyze_task_catalog` is the one protocol member where the implementation already exposes a stable per-file record shape and the core consumer immediately re-widens it, so the debt is concrete and locally repairable. The README renderer members are real typing debt too, but they span enough adjacent contracts and render-path helpers that they should be serialized as a later wave. Variable-discovery option bags and scan-pipeline payloads are better treated as intentionally generic for now because tightening them would reopen broader option/payload architecture instead of one boundary. The proposed mypy gate is live on the candidate slice and already passes in the current tree, so it is a valid first-wave discriminator.
