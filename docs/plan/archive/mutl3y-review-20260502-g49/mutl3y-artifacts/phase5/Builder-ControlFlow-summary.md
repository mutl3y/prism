# Builder-ControlFlow Summary

- Finding id: G49-H10
- Files changed:
  - `src/prism/scanner_plugins/defaults.py`
  - `src/prism/tests/test_defaults.py`
  - `src/prism/tests/test_plugin_kernel_extension_parity.py`
- Concrete behavioral change: prepared-policy resolver integrity defects now fail closed even with `strict_mode=False`. If a selected DI or registry plugin is malformed or its constructor raises, `scanner_plugins.defaults` now raises `PrismRuntimeError(code="malformed_plugin_shape")` instead of substituting the documented fallback. Fallback behavior remains unchanged for true absence or unavailability, where no selected plugin is present.
- Exact validation command and result:
  - `cd /raid5/source/test/prism && pytest -q src/prism/tests/test_defaults.py src/prism/tests/test_comment_doc_plugin_resolution.py -k malformed`
  - Result: `6 passed, 57 deselected in 0.45s`
  - Additional owned-slice check: `cd /raid5/source/test/prism && pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k non_strict_shape_validation`
  - Result: `1 passed, 29 deselected in 0.20s`
- Residual risks: this slice intentionally does not change plugin-factory invocation failures before shape validation, and it does not widen coverage beyond the owned defaults/prepared-policy surfaces.
