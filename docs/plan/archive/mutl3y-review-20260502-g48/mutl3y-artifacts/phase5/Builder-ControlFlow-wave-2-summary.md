# Builder-ControlFlow Wave 2 Summary

- Plan ID: `mutl3y-review-20260502-g48`
- Finding: `G48-M01`
- Fix group: `metadata-discovery-silent-fallbacks`
- Owned files: `src/prism/scanner_extract/discovery.py`, `src/prism/tests/test_dataload.py`

## Change

Tightened the discovery loader error channel so strict metadata shape failures now raise instead of returning `{}`, and non-strict metadata/requirements shape and YAML-parse fallbacks now always emit an observable warning path through logging and the optional warning collector. Added focused regressions for strict metadata shape rejection, strict invalid requirements YAML rejection, and non-strict warning collection on shape failures.

## Validation

- Narrow gate: `pytest -q src/prism/tests/test_dataload.py` -> `12 passed`

## Scope notes

- No scope expansion was needed.
- Potential gate escape outside owned scope: importer-layer tests that consume `load_meta()` or `load_requirements()` warning behavior may be worth a follow-up check if downstream warning normalization changes are under review.

## Trap candidate

- Discovery loaders with `strict=True` can still miss shape-invalid branches if only parse/IO paths are tested; add dedicated regression coverage for strict shape rejection rather than relying on invalid-YAML cases alone.
