# Auditor-Regression: g64 Wave-2 Regression Audit (Refreshed)

**Agent:** Auditor-Regression
**Plan ID:** mutl3y-review-20260504-g64
**Result:** PASS

---

## Summary

Wave-2 fixes for **G64-H02** (runtime wiring identity for cache correctness) and **G64-H03** (listener isolation) are **CONFIRMED REPAIRED AND STABLE**. Both prior regression risks have been fixed. All validation gates passing.

---

## G64-H02 Status: REPAIRED ✓

**Finding:** non_collection.run_scan must fingerprint semantics-bearing runtime wiring inputs in cache identity to prevent cached payloads from being replayed across distinct orchestration or registry behavior.

**Prior Risk:** `build_runtime_wiring_identity()` raised raw `TypeError` instead of wrapping in `PrismRuntimeError` — violating error-boundary audit.

**Repair Confirmed:**

- [src/prism/scanner_core/scan_cache.py](src/prism/scanner_core/scan_cache.py#L151-L165): All error cases properly wrapped in `PrismRuntimeError`
- [src/prism/api_layer/non_collection.py](src/prism/api_layer/non_collection.py#L684-L691): runtime wiring identity included in cache key
- Tests: 24/24 cache tests passing

---

## G64-H03 Status: REPAIRED ✓

**Finding:** execution_request_builder runtime assembly must NOT inherit process-global event listeners to prevent telemetry/progress leakage across overlapping requests.

**Prior Risk:** Test container mock (`_TestContainer`) skipped parent `__init__`, causing false-green test.

**Repair Confirmed:**

- [src/prism/tests/test_execution_request_builder.py](src/prism/tests/test_execution_request_builder.py#L204): `_TestContainer.__init__` now calls `super().__init__(...)`
- [src/prism/scanner_core/execution_request_builder.py](src/prism/scanner_core/execution_request_builder.py#L595): `inherit_default_event_listeners=False`
- [src/prism/scanner_core/di.py](src/prism/scanner_core/di.py#L220): DI respects the flag
- Tests: 4/4 listener-isolation tests passing

---

## Top Remaining Risks: None

No new regressions identified. All validation gates passed.

**Scope verified:**

✓ src/prism/api_layer/non_collection.py
✓ src/prism/scanner_core/scan_cache.py
✓ src/prism/scanner_core/execution_request_builder.py
✓ src/prism/tests/test_execution_request_builder.py
✓ src/prism/tests/test_t3_03_scan_cache.py
✓ src/prism/tests/test_g03_scan_cache_integration.py
✓ src/prism/tests/test_api_cli_entrypoints.py

- Test false-green masks listener isolation assurance.
- Error-boundary violation breaks caller error handling contract.
