Finding: G49-H11

Files changed:

- /raid5/source/test/prism/src/prism/scanner_extract/discovery.py
- /raid5/source/test/prism/src/prism/tests/test_dataload.py
- /raid5/source/test/prism/src/prism/tests/test_t1_02_coverage_lift_batch3.py

Concrete behavioral change:

- Preserved the fail-closed YAML-loading contract by aligning tests with the current `load_yaml_file()` behavior: bad or missing YAML now remains observable as `RuntimeError` rather than a `None` success shape.
- Removed stale ambiguity in discovery by replacing `or {}` normalization with explicit `None` handling for valid empty YAML documents only, and removed the unreachable metadata warning path that implied loader failures could arrive as `None`.
- Added a focused regression proving that an empty `meta/main.yml` still normalizes to an empty mapping without warning, separating valid empty-document behavior from loader failure behavior.

Validation command and result:

- Command: `cd /raid5/source/test/prism && pytest -q src/prism/tests/test_dataload.py src/prism/tests/test_t1_02_coverage_lift_batch3.py`
- Result: `37 passed in 0.24s`

Residual risks:

- Other non-owned tests or docs outside this wave may still encode the older `None`-as-failure expectation and were not touched in this scoped slice.
