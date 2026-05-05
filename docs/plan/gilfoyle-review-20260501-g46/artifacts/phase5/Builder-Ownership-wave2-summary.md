# Builder-Ownership Wave 2 Summary

Owned findings addressed: `G46-H04`, `G46-H05`.

Implementation summary:

- Made `prism.scanner_plugins` import side-effect free by replacing eager `DEFAULT_PLUGIN_REGISTRY` initialization with a lazy module attribute facade.
- Changed bootstrap registry access to initialize lazily on first explicit access and to fail closed when entry-point discovery raises.
- Set the built-in registry default platform explicitly to `ansible` during bootstrap.
- Removed order-based scan-pipeline default selection so registry default resolution now requires an explicit default or a single candidate.
- Updated owned regression tests to cover lazy bootstrap, strict discovery failure, explicit default-platform behavior, and the new route-selection contract.

Validation:

- `python3 -m pytest -q src/prism/tests/test_scanner_guardrails.py src/prism/tests/test_plugin_kernel_extension_parity.py src/prism/tests/test_t2_03_entry_point_discovery.py src/prism/tests/test_di_registry_resolution.py src/prism/tests/test_scanner_core_di.py`
- Result: `127 passed, 2 warnings`

Warnings observed:

- Two focused tests intentionally register lightweight scan-pipeline doubles without `PLUGIN_IS_STATELESS = True`; the registry warning remains expected for those test fixtures.
