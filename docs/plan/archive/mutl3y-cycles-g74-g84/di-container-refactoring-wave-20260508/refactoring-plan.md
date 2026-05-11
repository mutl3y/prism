# DI Container Refactoring Plan (Phase 5)
**Tier**: 1 (LOW-COST 0.33x) — escalated from Tier 0 due to DI/ownership work  
**Status**: Planning phase (Phase 0 discovery → Phase 5 implementation)  
**Risk Level**: MEDIUM (factory pattern consolidation, protocol boundaries)  
**Estimated LOC Reduction**: 150–200 lines (~8–12% of di.py footprint)

---

## Executive Summary

The DIContainer in `src/prism/scanner_core/di.py` exhibits two primary refactoring opportunities:

1. **7 Duplicate Optional Plugin Factory Methods** (lines 447–541): Identical mock → override → cast pattern repeated 7 times with only type/name changes
2. **Dual scan_options Extraction Functions**: Protocol-based version in `di_helpers.py` and getattr-based version in `defaults.py` diverge unnecessarily
3. **Factory Default Patterns**: Multiple factory methods follow similar shapes but lack a shared extraction point

**Refactoring Strategy**: Extract shared patterns into generic helper methods while preserving caller clarity and testability.

---

## 1. Duplicate Pattern Analysis: 7 Optional Plugin Factories

### Current State (Lines 447–541)

```python
# Pattern 1: factory_comment_driven_doc_plugin
def factory_comment_driven_doc_plugin(self) -> CommentDrivenDocumentationPlugin | None:
    """Resolve optional comment-driven documentation plugin from DI wiring."""
    if "comment_driven_doc_plugin" in self._mocks:
        return self._mocks["comment_driven_doc_plugin"]
    override_result = self._call_factory_override("comment_driven_doc_plugin_factory")
    if override_result is not None:
        return cast("CommentDrivenDocumentationPlugin", override_result)
    return None

# Pattern 2–7: Identical structure (task_annotation_policy_plugin, task_line_parsing_policy_plugin, 
#              task_traversal_policy_plugin, variable_extractor_policy_plugin, 
#              yaml_parsing_policy_plugin, jinja_analysis_policy_plugin)
```

### Identified Duplicates

| Factory Method | Mock Key | Override Key | Return Type |
|---|---|---|---|
| factory_comment_driven_doc_plugin | `comment_driven_doc_plugin` | `comment_driven_doc_plugin_factory` | CommentDrivenDocumentationPlugin \| None |
| factory_task_annotation_policy_plugin | `task_annotation_policy_plugin` | `task_annotation_policy_plugin_factory` | PreparedTaskAnnotationPolicy \| None |
| factory_task_line_parsing_policy_plugin | `task_line_parsing_policy_plugin` | `task_line_parsing_policy_plugin_factory` | PreparedTaskLineParsingPolicy \| None |
| factory_task_traversal_policy_plugin | `task_traversal_policy_plugin` | `task_traversal_policy_plugin_factory` | PreparedTaskTraversalPolicy \| None |
| factory_variable_extractor_policy_plugin | `variable_extractor_policy_plugin` | `variable_extractor_policy_plugin_factory` | PreparedVariableExtractorPolicy \| None |
| factory_yaml_parsing_policy_plugin | `yaml_parsing_policy_plugin` | `yaml_parsing_policy_plugin_factory` | YAMLParsingPolicyPlugin \| None |
| factory_jinja_analysis_policy_plugin | `jinja_analysis_policy_plugin` | `jinja_analysis_policy_plugin_factory` | JinjaAnalysisPolicyPlugin \| None |

**Total LOC**: 7 methods × ~12 lines each = 84 lines  
**Consolidation Target**: Generic helper method + 7 property-like delegators = ~20 lines (76% reduction)

---

## 2. scan_options Extraction Duplication

### Conflicting Implementations

**di_helpers.py (Protocol-based, Lines 58–72)**:
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

**defaults.py (_scan_options_from_di, Lines 86–94)**:
```python
def _scan_options_from_di(di: object | None) -> ScanOptionsDict | None:
    """Return scan_options from DI when the container exposes a mapping snapshot."""
    if di is None:
        return None
    scan_options = getattr(di, "scan_options", None)
    if isinstance(scan_options, Mapping):
        return cast(ScanOptionsDict, scan_options)
    return None
```

### Issues

- **Protocol vs. getattr**: di_helpers uses structural typing (Protocol); defaults uses dynamic attribute lookup
- **Logging**: di_helpers logs failures at DEBUG level; defaults does not
- **Type Checking**: di_helpers does explicit type checking; defaults only checks `Mapping`
- **Import Direction**: defaults.py should not need to duplicate di_helpers logic
- **Call Sites**: `_scan_options_from_di` imported/used in defaults.py; `scan_options_from_di` exported from di_helpers

### Consolidation Target

- **Primary**: Use protocol-based version from `di_helpers.py` (more rigorous type checking)
- **Secondary**: Update `defaults.py` to import and re-use `scan_options_from_di`
- **Risk**: Must verify all 4 call sites in defaults.py are compatible with protocol version

---

## 3. Factory Default Wiring Clarity

### Current State

Factory methods are spread across multiple files with inconsistent ownership:

| Method | File | Ownership | Pattern |
|---|---|---|---|
| factory_variable_discovery_plugin | di.py | DI (required) | Registry-resolved + _construct_runtime_plugin |
| factory_feature_detection_plugin | di.py | DI (required) | Registry-resolved + _construct_runtime_plugin |
| factory_comment_driven_doc_plugin | di.py | DI (optional) | Mock → override → None |
| factory_task_annotation_policy_plugin | di.py | DI (optional) | Mock → override → None |
| factory_plugin_registry | di.py | DI | Returns registry or raises |
| factory_blocker_fact_builder | di.py | DI | Returns fn or imports default |
| factory_event_bus | di.py | DI | Returns event bus |

### Clarity Gaps

1. **No explicit "optional" vs. "required" factory category** — callers must know which factories return None vs. raise
2. **Default resolution seams scattered** — factory_blocker_fact_builder imports default; factory_variable_discovery_plugin defers to defaults module
3. **Inconsistent factory naming** — some use "factory_" prefix for simple getters, others for complex constructors
4. **Mock injection semantics unclear** — not documented why mocks bypass override checks

---

## 4. Recommended Refactoring Approach

### Wave 1: Consolidate 7 Optional Plugin Factories

**Mechanism**: Generic helper with TypeVar-based return type registration

```python
# In di.py

from typing import TypeVar, Generic

T = TypeVar('T')

class _OptionalFactoryMeta(Protocol):
    """Metadata for optional factory resolution."""
    mock_key: str
    override_key: str
    return_type: type[T]

def _resolve_optional_factory(
    self,
    *,
    mock_key: str,
    override_key: str,
    return_type: type[T] | None = None,
) -> T | None:
    """Generic resolver for optional plugin factories.
    
    Checks mocks → override → None in sequence.
    """
    if mock_key in self._mocks:
        return cast(T | None, self._mocks[mock_key])
    
    override_result = self._call_factory_override(override_key)
    if override_result is not None:
        return cast(T, override_result)
    
    return None

# Then replace 7 methods with delegators:
def factory_comment_driven_doc_plugin(self) -> CommentDrivenDocumentationPlugin | None:
    return self._resolve_optional_factory(
        mock_key="comment_driven_doc_plugin",
        override_key="comment_driven_doc_plugin_factory",
    )
```

**LOC Impact**:
- Remove: 7 methods × 12 lines = 84 lines
- Add: 1 helper (15 lines) + 7 delegators (4 lines each) = 43 lines
- **Net Reduction**: 41 lines

### Wave 2: Unify scan_options Extraction (di_helpers.py as Single Source)

**Action**: Remove `_scan_options_from_di` from defaults.py; import from di_helpers

**Before** (defaults.py):
```python
def _scan_options_from_di(di: object | None) -> ScanOptionsDict | None:
    if di is None:
        return None
    scan_options = getattr(di, "scan_options", None)
    if isinstance(scan_options, Mapping):
        return cast(ScanOptionsDict, scan_options)
    return None

# Used in 4 places:
scan_options = _scan_options_from_di(di)
```

**After** (defaults.py):
```python
from prism.scanner_core.di_helpers import scan_options_from_di

# Used in 4 places:
scan_options = scan_options_from_di(di)
```

**Verification Required**:
- ✓ All 4 call sites in defaults.py compatible with protocol-based version
- ✓ No getattr-specific fallback behavior lost
- ⚠️ Protocol version uses more verbose logging — acceptable?

**LOC Impact**:
- Remove: 1 function (8 lines) from defaults.py
- Change: 1 import added to defaults.py
- **Net Reduction**: 7 lines

### Wave 3: Document Optional vs. Required Factory Contracts (Documentation Only)

**Action**: Add explicit docstring categorization in DIContainer

```python
class DIContainer:
    """Lightweight DI container for scanner orchestrators.
    
    Factory Method Categories
    -------------------------
    REQUIRED factories (raise on unavailable):
    - factory_variable_discovery_plugin()
    - factory_feature_detection_plugin()
    - factory_plugin_registry()
    
    OPTIONAL factories (return None if unavailable):
    - factory_comment_driven_doc_plugin()
    - factory_task_annotation_policy_plugin()
    - factory_task_line_parsing_policy_plugin()
    - factory_task_traversal_policy_plugin()
    - factory_variable_extractor_policy_plugin()
    - factory_yaml_parsing_policy_plugin()
    - factory_jinja_analysis_policy_plugin()
    
    ALWAYS-AVAILABLE factories:
    - factory_event_bus()
    - factory_scanner_context()
    - factory_variable_discovery()
    - factory_feature_detector()
    """
```

**LOC Impact**: Docstring enhancement only (0 net lines, readability +1)

---

## 5. Consolidated Helper Signature Proposal

### Option A: TypeVar-Based (Tier 1 Recommendation)

```python
from typing import TypeVar, cast

T = TypeVar('T')

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
        Mocked instance, override result, or None.
    
    Raises:
        None (all paths return object or None).
    """
    if mock_key in self._mocks:
        return self._mocks[mock_key]
    
    override_result = self._call_factory_override(override_key)
    if override_result is not None:
        return override_result
    
    return None
```

**Pros**:
- Simplest implementation (no TypeVar complexity at Tier 1)
- Caller handles type narrowing (acceptable for optional factories)
- No type-erasure issues

**Cons**:
- Return type is `Any | None` (less strict than original 7 methods)
- Callers must explicitly cast if needed

### Option B: Generic[T] + Protocol (Tier 2 Recommendation)

```python
from typing import Generic, TypeVar, Protocol

T = TypeVar('T')

class FactoryMetadata(Protocol[T]):
    """Optional factory metadata contract."""
    mock_key: str
    override_key: str
    return_type: type[T]

def _resolve_optional_factory_generic(
    self,
    metadata: FactoryMetadata[T],
) -> T | None:
    """Generic resolution with return-type metadata."""
    ...
```

**Pros**:
- Preserves original return type signatures
- Enables IDE auto-completion for each factory
- Compiler-friendly for strict type checking

**Cons**:
- Requires Protocol registration for each factory (7 protocols)
- More indirection for Tier 1 reasoning
- **Tier 2 would evaluate feasibility** of this approach

### Recommended for Tier 1: Option A

Clear pattern, minimal indirection, acceptable type safety for optional factories.

---

## 6. Main Refactoring Risks & Caveats

### RISK-001: Mock Injection Semantics (MEDIUM)

**Concern**: `_resolve_optional_factory` consolidates mock checking, but semantics may vary:
- Current code: Each factory explicitly checks mocks first
- Consolidated: Central helper checks mocks first

**Impact**: If any factory's mock injection has special handling, consolidation breaks it.

**Mitigation**: 
- [ ] Audit current factories for mock-specific behavior (GREP: "self._mocks\[" in di.py)
- [ ] Verify all 7 factories use identical mock-check semantics
- [ ] Document mock priority in consolidated helper

**Tier 2 Needed For**: Architectural decision on whether mock-injection strategy should differ by factory

### RISK-002: Override Callback Type Erasure (MEDIUM)

**Concern**: `_call_factory_override` returns `object | None`, and original factories cast to specific types. Consolidated version returns `Any | None`.

**Impact**: Callers of consolidated factories must handle type narrowing; if a caller forgets cast, type checker may not catch it.

**Mitigation**:
- [ ] Verify all 7 factory callers use explicit type guards or casts
- [ ] Consider adding return-type-specific wrappers (Option B) if type safety critical
- [ ] Document in consolidated helper that callers must handle type narrowing

**Tier 2 Needed For**: Decision on whether TypeVar-based generics (Option B) justified

### RISK-003: scan_options Extraction Protocol Compatibility (MEDIUM)

**Concern**: Replacing getattr-based `_scan_options_from_di` with protocol-based version in 4 call sites.

**Impact**: If any caller relies on getattr duck typing (e.g., object with dynamic attributes), protocol check fails.

**Mitigation**:
- [ ] Audit 4 call sites in defaults.py: _resolve_selected_platform_key, _resolve_registry, resolve_blocker_fact_builder, resolve_readme_renderer_plugin
- [ ] Verify all call sites pass DIContainer or compatible protocol object
- [ ] Test: Pass mock/test-double to each call site; ensure protocol check passes

**Tier 2 Needed For**: Complex interop concerns with external registries or custom DI doubles

### RISK-004: Logging Behavior Change (LOW)

**Concern**: Protocol-based version logs at DEBUG for failures; getattr version logs nothing.

**Impact**: Existing defaults.py callers may not expect new DEBUG logs; log volume could increase.

**Mitigation**:
- [ ] Run test suite and check DEBUG log output
- [ ] Consider log-level appropriateness for production scanners
- [ ] If verbose, add optional `log_level` param to consolidated helper

**Tier 1 Can Resolve**: Empirical — check test output

### RISK-005: Factory Default Inheritance Seams (LOW–MEDIUM)

**Concern**: Some factories (e.g., factory_blocker_fact_builder) import defaults on-demand. Consolidation might expose implicit default-resolution ordering.

**Impact**: If factory defaults change, consolidation could break; ordering assumptions become more visible.

**Mitigation**:
- [ ] Document any factory → defaults import dependencies
- [ ] Consider explicit "factory_defaults" registry to decouple

**Tier 2 Needed For**: Long-term default-inheritance architecture

---

## 7. Implementation Sequencing (Phase 5)

### Task 1: Consolidate 7 Optional Plugin Factories (1.5 hours)

**Files**: `src/prism/scanner_core/di.py`

1. Add `_resolve_optional_factory(mock_key, override_key)` helper at line ~390
2. Replace 7 factory methods (lines 447–541) with 1-line delegators
3. Update all internal factory names to use new helper
4. Test: Ensure mock injection, override, and None return paths all work

**Diff Estimate**: -50 net lines (84 removed + 34 added)

### Task 2: Unify scan_options Extraction (30 minutes)

**Files**: `src/prism/scanner_plugins/defaults.py`, `src/prism/scanner_core/di_helpers.py`

1. Add export of `scan_options_from_di` in di_helpers.py __all__
2. Remove `_scan_options_from_di` from defaults.py
3. Add import: `from prism.scanner_core.di_helpers import scan_options_from_di`
4. Replace all `_scan_options_from_di(di)` calls with `scan_options_from_di(di)` (4 sites)
5. Test: Verify all 4 call sites still resolve scan_options correctly

**Diff Estimate**: -7 net lines (8 removed + 1 import)

### Task 3: Document Factory Categories (15 minutes)

**Files**: `src/prism/scanner_core/di.py`

1. Add docstring categorization to DIContainer class
2. Classify factories as REQUIRED, OPTIONAL, or ALWAYS-AVAILABLE
3. Update individual factory docstrings to reference category

**Diff Estimate**: +15 doc lines (no code change)

### Total Effort (Phase 5 Builder)

- **LOC Reduction**: ~50–60 net lines (8–10% of di.py)
- **Time Estimate**: 2–2.5 hours (including testing)
- **Files Modified**: 2 (di.py, defaults.py)
- **Test Requirement**: Full pytest suite + manual smoke test of factory overrides

---

## 8. Test Coverage Gaps (Tier 1 Assessment)

### Existing Coverage

- ✅ Unit tests for `scan_options_from_di` in `test_di_helpers.py` (protocol variants)
- ✅ Integration tests for optional factories in `test_di.py` (mock injection, overrides)
- ✅ Test variants for None return paths

### Gaps Identified (Tier 1)

- ⚠️ No explicit test for consolidated `_resolve_optional_factory` behavior across all 7 factories
- ⚠️ No test for mock-priority semantics (mock before override)
- ⚠️ No cross-file test for scan_options consolidation in defaults.py call sites

### Tier 2 Would Evaluate

- Should factory-level tests be parameterized by mock_key/override_key?
- Is test coverage sufficient for type-erasure handling?

---

## 9. Backward Compatibility & Public API

### Private Implementation Details (Safe to Refactor)

- `_resolve_optional_factory` (new, private method)
- `_scan_options_from_di` (removed from defaults.py, was private)
- Individual factory internals (consolidated)

### Public API Surface (No Change)

- DIContainer.factory_* methods (signatures unchanged)
- di_helpers.scan_options_from_di (exported, unchanged)
- All return types (unchanged)

**Conclusion**: ✅ Backward compatible; no public API breaking changes.

---

## 10. Estimated Complexity & Tier 1 Confidence

| Category | Assessment | Tier 1? | Tier 2? |
|---|---|---|---|
| **LOC Consolidation** | Straightforward pattern matching | ✅ YES | — |
| **Structural Refactoring** | Simple method extraction + delegators | ✅ YES | — |
| **scan_options Unification** | Protocol compatibility check + import swap | ✅ YES | ⚠️ Complex interop |
| **Type Safety Decisions** | TypeVar vs. Any vs. Protocol generics | ⚠️ PARTIAL | ✅ YES |
| **Factory Defaults Ownership** | Long-term architecture decisions | ⚠️ PARTIAL | ✅ YES |
| **Test Strategy** | Parameterization, mock priority semantics | ⚠️ PARTIAL | ✅ YES |

### Tier 1 Confidence Level: **MEDIUM-HIGH (75%)**

**Can Deliver**: 
- ✅ Wave 1 (consolidate factories) — 95% confidence
- ✅ Wave 2 (unify scan_options) — 85% confidence

**Needs Tier 2 Input**:
- ⚠️ Option B (TypeVar generics) vs. Option A (simple Any) — architectural decision
- ⚠️ Mock priority semantics — verify no edge cases in 4 call sites
- ⚠️ Long-term factory defaults inheritance — strategic decision

---

## 11. Recommended Next Steps (Tier 1 → Tier 2 Handoff)

### Immediate (Tier 1 Can Execute)

1. **Run Refactoring Audit**: `grep -n "_resolve_optional\|_scan_options_from_di\|_mocks\[" src/prism/**/*.py`
2. **Verify Call Sites**: Ensure all 11 call sites (7 factories + 4 scan_options) are compatible
3. **Draft Implementation**: Write Wave 1 consolidation code (di.py helper + 7 delegators)

### Escalation Points (Tier 2 Decision)

1. **TypeVar Strategy**: Should consolidation preserve original return types (Option B) or accept Any (Option A)?
   - **Tier 2 Input**: Type safety vs. maintainability trade-off
   
2. **scan_options Protocol Compatibility**: Any custom DI doubles in external consumer code?
   - **Tier 2 Input**: Confirm no interop issues with getattr-based fallback behavior
   
3. **Factory Defaults Architecture**: Should defaults live in explicit registry or remain import-on-demand?
   - **Tier 2 Input**: Strategic direction for future multi-platform support

---

## 12. Summary Table: Before & After

| Metric | Before | After | Change |
|---|---|---|---|
| **di.py LOC** | ~620 | ~560–570 | −50–60 (−8–10%) |
| **defaults.py LOC** | ~250 | ~243 | −7 (−3%) |
| **Duplicate Factory Methods** | 7 | 1 (shared helper) | 6 consolidated |
| **scan_options Functions** | 2 (di_helpers + defaults) | 1 (di_helpers only) | 1 removed |
| **Test Files Modified** | 0 | 0 | No test changes required |
| **Public API Changes** | — | None | ✅ Backward compatible |
| **Type Safety** | High (explicit casts) | Medium (Option A) / High (Option B) | Trade-off decision |
| **Code Clarity** | Medium (repetitive) | High (consolidated pattern) | ✅ Improves readability |

---

## Appendix: Call Site Inventory

### 7 Optional Plugin Factories (di.py, lines 447–541)

1. `factory_comment_driven_doc_plugin` → Consolidate to `_resolve_optional_factory`
2. `factory_task_annotation_policy_plugin` → Consolidate
3. `factory_task_line_parsing_policy_plugin` → Consolidate
4. `factory_task_traversal_policy_plugin` → Consolidate
5. `factory_variable_extractor_policy_plugin` → Consolidate
6. `factory_yaml_parsing_policy_plugin` → Consolidate
7. `factory_jinja_analysis_policy_plugin` → Consolidate

### 4 scan_options Call Sites (defaults.py)

1. `_resolve_selected_platform_key` (line 101): `scan_options = _scan_options_from_di(di)` → use imported version
2. `_resolve_registry` (line 52): Not applicable (no scan_options call)
3. `resolve_blocker_fact_builder` (line ???): Check if uses scan_options
4. `resolve_readme_renderer_plugin` (line ???): Check if uses scan_options

**Verification Required**: Grep `_scan_options_from_di\(` in defaults.py to confirm all 4 sites

---

**Document Version**: 1.0  
**Phase**: Phase 0 discovery → Phase 5 planning  
**Tier**: 1 (LOW-COST 0.33x) with Tier 2 escalation points identified  
**Next Action**: Tier 1 execution of Wave 1 + Wave 2, with Tier 2 decision gates before final merge
