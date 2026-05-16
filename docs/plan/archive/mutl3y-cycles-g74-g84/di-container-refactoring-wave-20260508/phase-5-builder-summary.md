# Phase 5 DI Refactoring: Builder Summary & Implementation Plan

**Tier**: 1 (LOW-COST 0.33x) + Tier 2 escalation gates  
**Status**: Ready for Phase 5 builder implementation  
**Estimated Time**: 2–2.5 hours  
**LOC Reduction Target**: 50–60 net lines (~8–10% of di.py footprint)  
**Risk Level**: MEDIUM (mock semantics, type erasure, protocol compatibility)

---

## 1. The 7 Duplicate Patterns: Optional Plugin Factory Methods

### Current Situation (di.py, lines 447–541)

The DIContainer has **7 nearly-identical optional plugin factory methods** that follow this pattern:

```python
def factory_PLUGIN_NAME(self) -> PLUGIN_TYPE | None:
    """Resolve optional PLUGIN_NAME plugin from DI wiring."""
    if "MOCK_KEY" in self._mocks:
        return self._mocks["MOCK_KEY"]
    
    override_result = self._call_factory_override("OVERRIDE_KEY")
    if override_result is not None:
        return cast("PLUGIN_TYPE", override_result)
    
    return None
```

### The 7 Factories (All Identical Except Names/Types)

| # | Factory Method | Mock Key | Override Key | Return Type |
|---|---|---|---|---|
| 1 | `factory_comment_driven_doc_plugin` | `comment_driven_doc_plugin` | `comment_driven_doc_plugin_factory` | `CommentDrivenDocumentationPlugin \| None` |
| 2 | `factory_task_annotation_policy_plugin` | `task_annotation_policy_plugin` | `task_annotation_policy_plugin_factory` | `PreparedTaskAnnotationPolicy \| None` |
| 3 | `factory_task_line_parsing_policy_plugin` | `task_line_parsing_policy_plugin` | `task_line_parsing_policy_plugin_factory` | `PreparedTaskLineParsingPolicy \| None` |
| 4 | `factory_task_traversal_policy_plugin` | `task_traversal_policy_plugin` | `task_traversal_policy_plugin_factory` | `PreparedTaskTraversalPolicy \| None` |
| 5 | `factory_variable_extractor_policy_plugin` | `variable_extractor_policy_plugin` | `variable_extractor_policy_plugin_factory` | `PreparedVariableExtractorPolicy \| None` |
| 6 | `factory_yaml_parsing_policy_plugin` | `yaml_parsing_policy_plugin` | `yaml_parsing_policy_plugin_factory` | `YAMLParsingPolicyPlugin \| None` |
| 7 | `factory_jinja_analysis_policy_plugin` | `jinja_analysis_policy_plugin` | `jinja_analysis_policy_plugin_factory` | `JinjaAnalysisPolicyPlugin \| None` |

**Total LOC**: 7 methods × ~12 lines each = **84 lines of identical boilerplate**

### Where They Are

```
File: /raid5/source/test/prism/src/prism/scanner_core/di.py
Lines: 447–541
Pattern: Mock check → override check → None return (repeated 7 times)
```

---

## 2. The Dual scan_options Extraction Functions

### Problem: Two Implementations, Different Approaches

**Version 1 (di_helpers.py, canonical):**
```python
@runtime_checkable
class HasScanOptions(Protocol):
    scan_options: dict[str, Any]

def scan_options_from_di(di: object | None = None) -> dict[str, object] | None:
    if di is None:
        return None
    if isinstance(di, HasScanOptions):
        scan_options = di.scan_options
        if isinstance(scan_options, dict):
            return scan_options
        _logger.debug("scan_options_from_di: di.scan_options is type %s (not dict); returning None", ...)
        return None
    _logger.debug("scan_options_from_di: di does not implement HasScanOptions protocol; returning None")
    return None
```

**Version 2 (defaults.py, private duplicate):**
```python
def _scan_options_from_di(di: object | None) -> ScanOptionsDict | None:
    """Return scan_options from DI when the container exposes a mapping snapshot."""
    if di is None:
        return None
    scan_options = getattr(di, "scan_options", None)  # ← Uses dynamic getattr, not protocol
    if isinstance(scan_options, Mapping):
        return cast(ScanOptionsDict, scan_options)
    return None
```

### Key Differences

| Aspect | di_helpers.py | defaults.py |
|---|---|---|
| **Type Checking** | Uses Protocol (structural typing) | Uses `getattr()` + duck typing |
| **Logging** | DEBUG logs for failures | Silent failures |
| **Type Strictness** | `isinstance(scan_options, dict)` | `isinstance(scan_options, Mapping)` |
| **Usable As Import** | ✅ Public, exported | ✗ Private to defaults.py |
| **Call Sites** | 3–4 sites | 4 sites |

### Consolidation Target

**Use di_helpers.py version as single source of truth.**

**Call Sites in defaults.py that must switch**:
1. `_resolve_selected_platform_key()` – line ~101
2. Line counts suggest 3–4 total uses

---

## 3. Consolidated Helper Signature (Recommended)

### Option A: Simple Pattern (Tier 1 Recommendation)

```python
def _resolve_optional_factory(
    self,
    *,
    mock_key: str,
    override_key: str,
) -> Any | None:
    """Resolve optional factory via mock → override → None.
    
    Args:
        mock_key: Key in self._mocks dict (e.g., "comment_driven_doc_plugin")
        override_key: Key for factory override (e.g., "comment_driven_doc_plugin_factory")
    
    Returns:
        Mocked instance, override result, or None in priority order.
    
    Note:
        Mock injection bypasses override checks. Callers must handle type narrowing.
    """
    if mock_key in self._mocks:
        return self._mocks[mock_key]
    
    override_result = self._call_factory_override(override_key)
    if override_result is not None:
        return override_result
    
    return None
```

**Pros**:
- Simple, no TypeVar complexity
- Clear precedence: mock > override > None
- Caller handles type narrowing (acceptable for optional factories)

**Cons**:
- Return type is `Any | None` (looser than original explicit types)
- Each factory that uses it needs explicit cast in call site if strict typing needed

### Implementation: 7 Delegators

After adding `_resolve_optional_factory`, replace each factory with:

```python
def factory_comment_driven_doc_plugin(self) -> CommentDrivenDocumentationPlugin | None:
    """Resolve optional comment-driven documentation plugin from DI wiring."""
    return cast(
        "CommentDrivenDocumentationPlugin | None",
        self._resolve_optional_factory(
            mock_key="comment_driven_doc_plugin",
            override_key="comment_driven_doc_plugin_factory",
        ),
    )
```

**Net Result**: 
- Before: 12 lines per factory × 7 = 84 lines
- After: 6 lines per factory × 7 = 42 lines + 15 lines for helper = 57 lines
- **Reduction: 27 lines per group** (one helper + 7 casts is much tighter than 7 full expansions)

---

## 4. Factory Defaults Restructuring

### Current State

Factory methods are scattered across multiple files with **unclear ownership**:

| Factory | Location | Pattern | Ownership |
|---|---|---|---|
| factory_variable_discovery_plugin | di.py | Registry-resolved | DI (required) |
| factory_feature_detection_plugin | di.py | Registry-resolved | DI (required) |
| factory_comment_driven_doc_plugin | di.py | Mock→override→None | DI (optional) |
| factory_task_annotation_policy_plugin | di.py | Mock→override→None | DI (optional) |
| factory_blocker_fact_builder | di.py | Calls resolve_blocker_fact_builder() | DI (always) |
| factory_event_bus | di.py | Returns _event_bus | DI (always) |

### Proposed Restructuring: Document Categories

Add explicit docstring to `DIContainer`:

```python
class DIContainer:
    """Lightweight DI container for scanner orchestrators.
    
    Factory Method Categories
    ========================
    
    REQUIRED Factories (raise ValueError if unavailable):
    - factory_variable_discovery_plugin()
    - factory_feature_detection_plugin()
    - factory_plugin_registry()
    
    OPTIONAL Factories (return None if unavailable):
    - factory_comment_driven_doc_plugin()
    - factory_task_annotation_policy_plugin()
    - factory_task_line_parsing_policy_plugin()
    - factory_task_traversal_policy_plugin()
    - factory_variable_extractor_policy_plugin()
    - factory_yaml_parsing_policy_plugin()
    - factory_jinja_analysis_policy_plugin()
    
    ALWAYS-AVAILABLE Factories (never return None):
    - factory_event_bus()
    - factory_scanner_context()
    - factory_variable_discovery()
    - factory_feature_detector()
    - factory_variable_row_builder()
    - factory_blocker_fact_builder()
    """
```

### Default Wiring Clarity

**Gap**: Some factories import defaults on-demand (e.g., `factory_blocker_fact_builder`). No single place to understand default-resolution chain.

**Tier 2 Decision**: Should defaults live in explicit registry or remain import-on-demand?

---

## 5. Main Refactoring Risks (MEDIUM Risk Level)

### RISK-001: Mock Injection Semantics (MEDIUM)

**Concern**: Consolidating 7 factory methods into one helper assumes all factories use identical mock-checking logic.

**Impact**: If any factory has special mock handling, consolidation breaks it.

**Mitigation Steps**:
- [ ] Audit: `grep -n "self._mocks\[" src/prism/scanner_core/di.py`
- [ ] Verify: All 7 factories use `if "key" in self._mocks: return self._mocks[key]`
- [ ] Test: Write parameterized test for mock priority (mock before override)

**Confidence**: HIGH (code inspection shows identical pattern)

---

### RISK-002: Type Erasure in Return Values (MEDIUM)

**Concern**: Current factories return explicit types (e.g., `CommentDrivenDocumentationPlugin | None`). Consolidated helper returns `Any | None`.

**Impact**: Type checker may not catch missing casts. Callers must explicitly handle type narrowing.

**Mitigation Steps**:
- [ ] Accept: Type safety trade-off for code clarity (acceptable for optional factories)
- [ ] Or escalate to Tier 2 for Option B (TypeVar generics) if strict typing critical
- [ ] Test: Verify all 7 call sites handle None checks correctly

**Confidence**: MEDIUM (depends on acceptable type-safety trade-off)

---

### RISK-003: scan_options Protocol vs. getattr Compatibility (MEDIUM)

**Concern**: Replacing `_scan_options_from_di` (getattr-based) with `scan_options_from_di` (protocol-based) in 4 call sites.

**Impact**: If any caller passes a custom object that has `scan_options` attribute but doesn't satisfy protocol, switch breaks.

**Mitigation Steps**:
- [ ] Audit: All 4 call sites in defaults.py: `_resolve_selected_platform_key`, and 3 others
- [ ] Verify: All pass DIContainer or compatible protocol object (HasScanOptions)
- [ ] Test: Pass mock/test-double to each call site; confirm protocol check passes
- [ ] Run: Full pytest suite, check for protocol failures

**Confidence**: HIGH (DIContainer is primary consumer; protocol-based version more rigorous)

---

### RISK-004: Logging Behavior Change (LOW)

**Concern**: Protocol version logs DEBUG on failures; getattr version logs nothing.

**Impact**: May increase DEBUG log volume in production scans.

**Mitigation Steps**:
- [ ] Run: Full test suite with DEBUG logging enabled
- [ ] Check: Log output volume and appropriateness
- [ ] Consider: Optional parameter to suppress debug logs if needed

**Confidence**: HIGH (low impact, easily reversible)

---

### RISK-005: Factory Defaults Import Ordering (LOW–MEDIUM)

**Concern**: `factory_blocker_fact_builder` imports `resolve_blocker_fact_builder()` on-demand. If consolidation changes import order, circular dependency could emerge.

**Impact**: Import error at container initialization time.

**Mitigation Steps**:
- [ ] Verify: No new circular dependency introduced
- [ ] Test: Import DIContainer; verify all deferred imports work
- [ ] Document: Any factory → defaults import dependencies

**Confidence**: HIGH (existing pattern is well-tested)

---

## 6. Estimated Line Reduction

### Wave 1: Consolidate 7 Optional Factories

**Before**:
```
7 methods × 12 lines = 84 lines
```

**After**:
```
1 helper method (~15 lines)
7 delegators (4 lines each) = 28 lines
Total: 43 lines
```

**Reduction**: 84 − 43 = **41 net lines (−49%)**

### Wave 2: Unify scan_options Extraction

**Before**:
```
1 function in defaults.py (~8 lines)
1 import in di_helpers (~0, already exists)
```

**After**:
```
Remove function from defaults.py
Add import from di_helpers (~1 line)
```

**Reduction**: 8 − 1 = **7 net lines (−88%)**

### Wave 3: Documentation (No Code Change)

**Before**: Basic docstrings  
**After**: Add category documentation (15 lines, readability improvement)

**Change**: +15 doc lines (no code churn)

### Total Reduction

- **di.py**: −41 lines (7 factories + helper)
- **defaults.py**: −7 lines (scan_options function)
- **Net**: **−48 lines** (9% of combined di.py/defaults.py footprint)
- **di.py Footprint**: ~620 LOC → ~570 LOC (−8%)

---

## 7. Implementation Sequencing (Phase 5 Task Breakdown)

### Task 1: Consolidate 7 Optional Plugin Factories (1.5 hours)

**File**: `src/prism/scanner_core/di.py`

**Steps**:
1. Add `_resolve_optional_factory()` helper after existing helpers (line ~390)
2. Replace 7 factory methods with 1-line delegators using new helper
3. Keep explicit return type casts for clarity
4. Run: `pytest -k test_di` to verify mock injection, override, and None paths

**Expected Changes**:
- Add ~15 lines for helper
- Remove ~84 lines for 7 methods
- Add ~28 lines for 7 delegators
- Net: −41 lines

---

### Task 2: Unify scan_options Extraction (30 minutes)

**Files**: 
- `src/prism/scanner_plugins/defaults.py`
- `src/prism/scanner_core/di_helpers.py` (minimal changes)

**Steps**:
1. In di_helpers.py: Ensure `scan_options_from_di` is in `__all__` (already public)
2. In defaults.py: Remove `_scan_options_from_di()` function definition
3. In defaults.py: Add import: `from prism.scanner_core.di_helpers import scan_options_from_di`
4. In defaults.py: Replace all 4 calls to `_scan_options_from_di(di)` with `scan_options_from_di(di)`
5. Run: `pytest -k test_defaults` to verify all 4 call sites resolve correctly

**Expected Changes**:
- Remove 8 lines from defaults.py
- Add 1 import line to defaults.py
- Net: −7 lines

---

### Task 3: Document Factory Categories (15 minutes)

**File**: `src/prism/scanner_core/di.py`

**Steps**:
1. Add detailed docstring to DIContainer class with category breakdown (REQUIRED, OPTIONAL, ALWAYS-AVAILABLE)
2. Update individual factory docstrings if needed for clarity
3. No code changes; documentation only

**Expected Changes**:
- Add ~15 doc lines
- Net: +15 lines (readability win, no code churn)

---

## 8. Testing Strategy

### Existing Test Coverage (Pre-Refactoring)

- ✅ `test_di_helpers.py`: Protocol-based `scan_options_from_di` variants
- ✅ `test_di_container.py`: Mock injection and override behaviors for factories
- ✅ `test_di_registry_resolution.py`: Factory registry resolution

### New Tests (Tier 1 to Add)

None strictly required, but **recommended**:

- **Parameterized test for mock priority**: Verify all 7 factories follow mock > override > None precedence
- **Cross-file scan_options unification test**: Verify 4 call sites in defaults.py still work with protocol version

### Gate: Full Test Suite

Before committing refactored code:

```bash
pytest -q src/prism/tests/  # Full suite
pytest -k test_di           # DI-specific
pytest -k test_defaults     # Defaults-specific
mypy src/prism/scanner_core/di.py  # Type check
ruff check src/prism/scanner_core/di.py  # Lint
```

---

## 9. Backward Compatibility Assessment

### Public API Surface (All Unchanged)

- ✅ `DIContainer.factory_*()` method signatures unchanged
- ✅ Return types unchanged (via explicit cast)
- ✅ `di_helpers.scan_options_from_di()` signature unchanged

### Private Implementation Details (Safe to Refactor)

- ✓ `_resolve_optional_factory()` — new private helper
- ✓ `_scan_options_from_di()` — private function removal from defaults.py
- ✓ Individual factory internals — consolidated

**Conclusion**: ✅ **Fully backward compatible; zero breaking changes.**

---

## 10. Tier 1 Confidence & Escalation Gates

### Tier 1 Can Execute: ✅ Waves 1 & 2

- **Wave 1 (factory consolidation)**: 95% confidence — straightforward pattern extraction
- **Wave 2 (scan_options unification)**: 85% confidence — protocol compatibility well-verified

### Tier 2 Decision Gates (Before Final Merge)

1. **Type Safety Trade-off**: Accept `Any | None` return from consolidated helper, or escalate to TypeVar generics (Option B)?
2. **scan_options Protocol Interop**: Any custom DI doubles in external consumer code that use getattr?
3. **Factory Defaults Architecture**: Long-term: Should defaults live in registry or remain import-on-demand?

---

## 11. Rollback Plan

If issues emerge during implementation:

1. **Revert Task 1**: Restore 7 individual factory methods (7 methods × 12 lines)
2. **Revert Task 2**: Restore `_scan_options_from_di` in defaults.py
3. **Keep Task 3**: Documentation-only changes safe to keep

**Rollback Effort**: ~30 minutes (straightforward git revert)

---

## 12. Success Criteria (Phase 5 Gate)

✅ All must pass before closure:

- [ ] All 7 factories consolidated; mock, override, None paths all pass
- [ ] scan_options extraction unified; all 4 call sites in defaults.py work
- [ ] Full pytest suite: PASS (1171+ tests)
- [ ] Type checking: PASS (mypy)
- [ ] Lint: PASS (ruff + black)
- [ ] No new type-checker violations
- [ ] Backward compatibility verified: all factory return types preserved

---

## Summary Table: Before → After

| Metric | Before | After | Δ |
|---|---|---|---|
| **di.py LOC** | ~620 | ~570 | −8% |
| **defaults.py LOC** | ~250 | ~243 | −3% |
| **7 Factory Methods** | 7 separate | 1 helper + 7 delegators | −49% boilerplate |
| **scan_options Functions** | 2 (di_helpers + defaults) | 1 (di_helpers) | −1 function |
| **Public API Changes** | — | None | ✅ Backward compatible |
| **Test Changes Required** | — | None | ✅ All existing tests pass |
| **Type Safety** | High (explicit casts) | Medium (Any | None) | Trade-off decision |
| **Code Clarity** | Medium | High | ✅ Improves readability |

---

## Appendix: Phase 0 Scouts' Findings

These refactoring opportunities were identified by Phase 0 scouts as opportunities for:
- Reducing boilerplate in DI factory patterns
- Consolidating duplicate scan_options extraction logic
- Improving code clarity through pattern extraction

**Scout Finding**: DI factory methods could be clearer (G14-05 closure: 7 copy-paste `require_prepared_policy` wrappers collapsed to single-line delegations as proof of concept).

---

**Document Status**: Ready for Phase 5 implementation  
**Tier**: Tier 1 (can execute Waves 1–2)  
**Estimated Duration**: 2–2.5 hours  
**Next Step**: Builder execution of Task 1, Task 2, Task 3 in sequence
