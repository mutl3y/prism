# Jinja2 AST Expansion Workoff Plan

**Status**: Completed
**Date**: 20 March 2026
**Archive State**: Archived

## Scope

- [x] Expand AST filter scanning from `default()` only to all filters.
- [x] Keep backward compatibility for default-only callers.
- [x] Integrate all-filter scanning into `scanner.py`.
- [x] Add and pass unit/integration tests.
- [x] Validate full test suite and coverage.

## Completed Work

### Phase 1: Core Refactor

- [x] Removed default-only AST restriction.
- [x] Added `filter_name` to AST filter occurrence rows.
- [x] Added `_scan_text_for_all_filters_with_ast(...)` in `src/prism/_jinja_analyzer.py`.

### Phase 2: Backward Compatibility

- [x] Kept `_scan_text_for_default_filters_with_ast(...)` as a wrapper.
- [x] Wrapper filters all-filter results to `filter_name == "default"`.
- [x] Updated analyzer module public-name documentation.

### Phase 3: Scanner Integration

- [x] Imported all-filter AST helper in `src/prism/scanner.py`.
- [x] Added `scan_for_all_filters(...)` public API.
- [x] Added `_scan_file_for_all_filters(...)` with malformed-template regex fallback.
- [x] Preserved existing `scan_for_default_filters(...)` behavior.

### Phase 4: Tests

- [x] Added all-filter AST tests in `src/prism/tests/test_scanner_internals.py`.
- [x] Added scanner-level all-filter tests in `src/prism/tests/test_scan.py`.
- [x] Covered AST detection, filter chains, exclude-path behavior, and fallback parsing.

### Phase 5: Validation

- [x] Ran task test suite: `502 passed`.
- [x] Ran repo validation: `tox -q`.
- [x] Confirmed coverage target exceeded: `91.66%` total.

## Notes

- [x] Backward compatibility maintained for default-filter workflows.
- [x] New all-filter output rows include: `file`, `line_no`, `line`, `match`, `args`, `filter_name`.
- [x] No regressions found in full-suite verification.
- [x] Plan closed and archived under `docs/completed_plans/`.
