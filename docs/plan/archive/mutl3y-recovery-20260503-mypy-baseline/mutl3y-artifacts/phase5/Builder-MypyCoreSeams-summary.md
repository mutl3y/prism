# Builder-MypyCoreSeams Summary

- Scope: aligned owned core seam typing and nearby tests without widening runtime plugin or registry contracts.
- Runtime-facing changes:
  - `variable_discovery.py` and `feature_detector.py` now keep cloned scan options as `ScanOptionsDict` internally and cast only at legacy dict-validator and plugin protocol boundaries.
  - Event bus phase contexts in core seams are annotated as `dict[str, object]` to match the event bus protocol.
  - `task_extract_adapters.py` now types the YAML failure collector as `list[YamlParseFailure] | None`.
  - `plugin_facade.py` now resolves the default registry through the typed bootstrap accessor instead of the module `__getattr__` object path.
- Test updates:
  - Added typed `ScanOptionsDict` helpers in nearby tests instead of underspecified dict literals.
  - Switched the plugin API version smoke test to the typed registry accessor.
  - Fixed the feature-detector path helper context manager annotation and tightened local plugin stub signatures.
- Validation:
  - Focused mypy: `Success: no issues found in 8 source files`
  - Nearby pytest bundle: `30 passed in 0.66s`
