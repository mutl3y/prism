## Builder-Ownership Wave 1 Summary

- Plan ID: `mutl3y-review-20260504-g69`
- Cycle: `g69`
- Wave: `1`
- Fix group: `api_layer.non_collection.default_registry_authority`
- Finding: `G69-H01`
- Scope: owned implementation and regression test only

Implemented the direct `prism.api_layer.non_collection.run_scan` fallback through `plugin_facade.get_default_scan_pipeline_registry()` so the direct seam now shares the same isolated default scan-pipeline registry authority as the public API seam.

Caller-supplied `default_plugin_registry` precedence remains unchanged because the new fallback only applies when no registry is provided.

Added a focused regression test covering the direct non-collection caller path. The test poisons the raw default registry, stubs the isolated scan-pipeline registry seam, and asserts the execution request receives the seam-provided isolated registry without bypassing the facade.

### Changed Files

- `src/prism/api_layer/non_collection.py`
- `src/prism/tests/test_api_cli_entrypoints.py`

### Narrow Gate

Command:

```bash
cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_api_cli_entrypoints.py -k non_collection_run_scan
```

Result:

```text
3 passed, 33 deselected in 0.43s
```

### Status

`G69-H01` is closed-ready for this owned wave. No scope expansion was needed.
