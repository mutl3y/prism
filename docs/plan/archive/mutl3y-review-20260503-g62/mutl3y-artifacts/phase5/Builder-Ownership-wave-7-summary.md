## Builder-Ownership wave 7 summary

- Finding: `G62-H03`
- Behavior fixed: the isolated scan-pipeline registry facade now forwards `is_reserved_unsupported_platform()`, so public API calls keep reserved unsupported platform semantics and raise `platform_not_supported` instead of `platform_not_registered`.
- Files changed: `src/prism/api_layer/plugin_facade.py`, `src/prism/tests/test_api_cli_entrypoints.py`
- Validation: focused API seam pytest, platform fail-closed pytest, and focused mypy for the owned files.
