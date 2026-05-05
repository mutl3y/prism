# Builder-Ownership Summary

- Task: g62-wave1-builder-ownership
- Fix group: registry-dynamic-attr
- Invariant preserved: runtime default-registry authority still flows through `scanner_plugins.bootstrap.get_default_plugin_registry()` with lazy singleton initialization unchanged.
- Change: retired the package-root `DEFAULT_PLUGIN_REGISTRY` dynamic attribute export from `prism.scanner_plugins.__init__` and exported the explicit getter surface instead.
- Change: updated the owned importer and parity tests to call `get_default_plugin_registry()` directly rather than relying on package-root dynamic attribute access.
- Narrow gate: `pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k 'default_plugin_registry or bootstrap' src/prism/tests/test_di_registry_resolution.py -k 'through_registry or default_platform_key'` -> `5 passed, 56 deselected`
- Optional importer-layer gate: `pytest -q src/prism/tests/test_feature_detector.py src/prism/tests/test_variable_discovery_pipeline.py -k 'registry or plugin'` -> `3 passed, 14 deselected`
- Scope expansion: not needed for this slice.
- Regression pattern: none beyond the existing common-traps coverage.
