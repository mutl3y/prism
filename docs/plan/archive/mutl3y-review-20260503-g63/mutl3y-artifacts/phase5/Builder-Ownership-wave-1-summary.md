# Builder-Ownership Wave 1 Summary

Finding: G63-M01
Task: g63-wave1-builder-ownership
Category: test_fixture_coupling
Status: closed-ready

Change summary:

- Replaced direct private mutation of `plugin_registry` internals in `test_comment_doc_plugin_resolution.py` with a snapshot/restore context manager built on the public `snapshot_state()` and `replace_state()` seam.
- Added a small helper for removal scenarios so fallback-path tests can clear registry entries without touching private registry maps.
- Preserved the existing test contract around DI-over-registry precedence and canonical-DI enforcement.

Validation:

- Narrow gate: `.venv/bin/python -m pytest -q src/prism/tests/test_comment_doc_plugin_resolution.py` -> PASS (`62 passed, 12 warnings`).
- Optional importer-layer gate: `.venv/bin/python -m pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k comment_driven_doc` -> no selected tests (`31 deselected`, exit code 5).

Scope:

- No scope expansion needed.
- No blockers in the owned file set.
