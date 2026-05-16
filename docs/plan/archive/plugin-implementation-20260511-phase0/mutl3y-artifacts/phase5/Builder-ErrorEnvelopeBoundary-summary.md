# Builder-ErrorEnvelopeBoundary — Wave rem-2 Summary

**Plan**: g84-remediation-mutl3y-cycle-20260509  
**Wave**: rem-2  
**Status**: ✅ COMPLETE

## Problem Statement

Two failing tests revealed an error envelope contract violation and boundary policy breach:

1. **Test**: `test_fsrc_scanner_context_best_effort_records_error_envelope`  
   **Issue**: Missing `traceback` key in `scan_errors[0]`

2. **Test**: `test_no_new_raw_raises_at_module_boundaries`  
   **Issue**: New raw `ValueError` raises detected in:
   - `src/prism/scanner_core/marker_prefix_contract.py`
   - `src/prism/scanner_core/marker_prefix_enforcer.py`

## Solution

### Fix 1: Add Traceback Capture (scanner_context.py)

**Module**: `src/prism/scanner_core/scanner_context.py`  
**Method**: `_record_phase_error()`

**Change**: Capture and include traceback in error envelope.

```python
# Before:
entry: ScanErrorEntry = {
    "phase": phase,
    "error_type": error.__class__.__name__,
    "message": str(error),
}

# After:
tb_str = traceback.format_exc()
entry: ScanErrorEntry = {
    "phase": phase,
    "error_type": error.__class__.__name__,
    "message": str(error),
    "traceback": tb_str,  # Added for context preservation (GILF-NODE1-06)
}
```

**Rationale**: Test expects `traceback` key for context preservation during best-effort recovery. Traceback module already imported.

### Fix 2: Wrap ValueError in PrismRuntimeError (marker_prefix_contract.py)

**Module**: `src/prism/scanner_core/marker_prefix_contract.py`  
**Method**: `enforce_marker_prefix_available()`

**Change**: Replaced 3 raw `ValueError` raises with `PrismRuntimeError` wraps:

- `marker_prefix_invalid_type` — non-string or None marker_prefix
- `marker_prefix_empty` — empty string marker_prefix
- `marker_prefix_invalid_chars` — control characters in marker_prefix

**Rationale**: Boundary audit forbids raw exception raises at module boundaries. Wrapping in `PrismRuntimeError` satisfies layer contract and error boundary policy.

### Fix 3: Wrap ValueError in PrismRuntimeError (marker_prefix_enforcer.py)

**Module**: `src/prism/scanner_core/marker_prefix_enforcer.py`  
**Function**: `enforce_marker_prefix_available()`

**Change**: Replaced 4 raw `ValueError` raises with `PrismRuntimeError` wraps:

- `marker_prefix_bundle_invalid_type` — bundle not a dict
- `marker_prefix_bundle_missing_key` — `comment_doc_marker_prefix` key missing
- `marker_prefix_invalid_type` — marker_prefix not a string
- `marker_prefix_empty` — marker_prefix is empty string

**Rationale**: Same boundary audit compliance. This function is the enforcement gate for MP1 contract; errors must be wrapped at the boundary.

## MP1 Intent Preservation

All changes preserve the MP1 marker-prefix contract intent:

- Marker-prefix remains **fail-closed** (errors now raised as `PrismRuntimeError` instead of silent fallback)
- Marker-prefix remains **ingress-owned** (ingress is responsible for setting it; any absence triggers explicit error)
- Marker-prefix remains **immutable** (validation gates prevent runtime modifications)
- Boundary wrapping occurs only at the **public contract boundary** (internal ValueError validation logic is unchanged; only the exception type wrapper changes)

## Changed Files

1. `src/prism/scanner_core/scanner_context.py` — 1 method, 5 lines added
2. `src/prism/scanner_core/marker_prefix_contract.py` — 1 method, 9 lines modified
3. `src/prism/scanner_core/marker_prefix_enforcer.py` — 1 function, 18 lines modified

## Narrow Gate Results

```bash
============================= test session starts ==============================
PASSED: src/prism/tests/test_scanner_context.py::test_fsrc_scanner_context_best_effort_records_error_envelope
PASSED: src/prism/tests/test_t3_04_error_boundary_audit.py::test_no_new_raw_raises_at_module_boundaries

============================== 2 passed in 0.31s ===============================
```

### Additional Verification

- **Full scanner_context test suite**: 22/22 PASS
- **Full error boundary audit suite**: 3/3 PASS
- **Regressions**: None detected

## Compliance

✅ Error envelope now includes `traceback` key  
✅ No raw exception raises at module boundaries  
✅ MP1 marker-prefix contract intent preserved  
✅ All changes scoped to owned files  
✅ Boundary wrapping applied only at public interfaces

## Rationale

**Traceback addition** is necessary for best-effort recovery semantics: when a scan degrades, consumers need the full exception context to diagnose and retry. The test explicitly validates this contract.

**ValueError → PrismRuntimeError wrapping** is necessary for boundary audit compliance: error-raising code at module boundaries must use the framework's standard error type to enforce consistent error handling and prevent hidden exceptions that violate the error boundary policy.

Both changes are **minimal and explicit**, targeting only the contract violation points without refactoring existing logic or behavior.
