# Implementation Sequence — Locked 7-Wave Plan

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-1-grader (finalization)  
**Date**: May 9, 2026  
**Status**: ✅ **LOCKED FOR PHASE 2**

---

## Executive Summary

7-wave implementation sequence with clear dependencies, sizing estimates, and validation gates. Total effort: 8 person-days. No circular dependencies. Ready for parallel work in waves 2-4.

---

## Wave Dependency Graph

```
Wave 0 (Preparation)
  │
  ├─→ Wave 1 (FallbackPolicyRegistry)
  │     │
  │     ├─→ Wave 2 (PolicyManager)
  │     │     │
  │     │     ├─→ Wave 3 (Caching Layer)
  │     │     │     │
  │     │     │     └─→ Wave 4 (DIContainer Integration)
  │     │     │           │
  │     │     │           └─→ Wave 5 (Integration Tests)
  │     │     │                 │
  │     │     │                 └─→ Wave 6 (Performance Validation)
  │     │     │
  │     │     └─→ Wave 5 (can start after Wave 2)
  │     │
  │     └─→ Wave 5 (can start after Wave 1)
```

**Dependency Summary**:
- Wave 0: No dependencies (preparatory)
- Wave 1: Depends on Wave 0
- Wave 2: Depends on Wave 0, 1 (DI + registry ready)
- Wave 3: Depends on Wave 2 (PolicyManager methods used)
- Wave 4: Depends on Wave 2, 3 (manager + cache in DI)
- Wave 5: Depends on Wave 1, 2, 3, 4 (all components ready)
- Wave 6: Depends on Wave 5 (tests passing)

**Parallelizable**: Waves 2 & 3 can start after Wave 1; Wave 5 can start after Wave 2.

---

## Wave 0: Preparation (0.5 days)

### Objective
Create directory structure and type definitions. No implementation.

### Tasks

#### Task 0.1: Create Module Structure
- Create `src/prism/scanner_plugins/fallback_registry.py` (empty with docstring)
- Create `src/prism/scanner_plugins/policy_manager.py` (empty with docstring)
- Create `src/prism/scanner_plugins/bootstrap.py` (initialization bootstrap)
- Create `src/prism/scanner_config/policy_loader.py` (config consolidation)
- Create test files:
  - `tests/scanner_plugins/test_fallback_registry.py`
  - `tests/scanner_plugins/test_policy_manager.py`
  - `tests/scanner_config/test_policy_loader.py`
  - `tests/integration/test_policy_consolidation.py`

**Validation Gate 0.1**:
```bash
python -c "import src.prism.scanner_plugins.fallback_registry; print('✓ Imports OK')"
```

#### Task 0.2: Copy Type Definitions
- Extract protocol definitions from `contracts_request.py`
- Copy to `policy_manager.py` module docstring (for reference)
- Verify no circular imports

**Validation Gate 0.2**:
```bash
python -c "from src.prism.scanner_plugins.policy_manager import *; print('✓ Types importable')"
```

**Effort**: 0.5 days  
**Owner**: Backend (1 developer)  
**Status**: Ready to start

---

## Wave 1: FallbackPolicyRegistry (1 day)

### Objective
Implement centralized registry for 6 fallback policy singletons.

### Tasks

#### Task 1.1: Implement FallbackPolicyRegistry Class
**File**: `src/prism/scanner_plugins/fallback_registry.py`

**Scope**:
- `__init__()`: Initialize registry dict + RLock
- `register_fallback(policy_kind, plugin)`: Register singleton
- `get_fallback(policy_kind)`: Retrieve policy
- `get_all_fallbacks()`: Snapshot of all policies
- `has_fallback(policy_kind)`: Check existence
- `unregister_fallback(policy_kind)`: Testing cleanup

**Lines of Code**: 80-120  
**Tests**: 8-10 test cases

**Validation Gate 1.1**:
```bash
pytest tests/scanner_plugins/test_fallback_registry.py -v
# Expected: 8-10 tests pass, 0 failures
```

**Estimated Effort**: 0.4 days

---

#### Task 1.2: Implement initialize_fallback_registry() Bootstrap
**File**: `src/prism/scanner_plugins/bootstrap.py`

**Scope**:
- Import 6 default policy implementations
- Create FallbackPolicyRegistry instance
- Register 6 policies by kind ("task_line_parsing", etc.)
- Return initialized registry

**Lines of Code**: 40-60  
**Tests**: 3-4 test cases

**Dependencies**:
- Task 1.1 complete (registry class exists)
- Default policy implementations exist (from prior work)

**Validation Gate 1.2**:
```bash
python -c "from src.prism.scanner_plugins.bootstrap import initialize_fallback_registry; r = initialize_fallback_registry(); assert r.has_fallback('task_line_parsing'); print('✓')"
```

**Estimated Effort**: 0.3 days

---

#### Task 1.3: Integrate FallbackPolicyRegistry into DIContainer
**File**: `src/prism/scanner_core/di.py`

**Scope**:
- Add `fallback_policy_registry: FallbackPolicyRegistry` field to DIContainer
- Update `DIContainer.default()` to initialize registry via bootstrap
- Add getter methods if needed

**Lines of Code**: 20-40  
**Tests**: 2-3 test cases

**Validation Gate 1.3**:
```bash
python -c "from src.prism.scanner_core.di import DIContainer; di = DIContainer.default(); assert hasattr(di, 'fallback_policy_registry'); print('✓')"
```

**Estimated Effort**: 0.3 days

**Wave 1 Total**: 1.0 days

---

## Wave 2: PolicyManager Facade (1.5 days)

### Objective
Implement unified PolicyManager with 8 public methods.

### Tasks

#### Task 2.1: Implement PolicyManager Class (Core)
**File**: `src/prism/scanner_plugins/policy_manager.py`

**Scope**:
- `__init__(fallback_registry, plugin_registry, di, cache=None)`
- 6 resolver methods:
  - `resolve_task_line_parsing_policy()`
  - `resolve_task_annotation_policy()`
  - `resolve_task_traversal_policy()`
  - `resolve_yaml_parsing_policy()`
  - `resolve_jinja_analysis_policy()`
  - `resolve_variable_extractor_policy()`
- 2 utility methods:
  - `resolve_prepared_policy_bundle()` (atomic initialization)
  - `resolve_by_kind(kind)` (generic extensibility)

**Lines of Code**: 200-300  
**Tests**: 15-20 test cases

**Implementation Strategy**:
```python
def resolve_task_line_parsing_policy(self):
    """Resolve with priority: DI factory → registry → fallback"""
    # 1. Check DI factory (highest priority)
    if hasattr(self.di, 'factory_task_line_parsing_policy_plugin'):
        return self.di.factory_task_line_parsing_policy_plugin()
    # 2. Check plugin registry
    if self.plugin_registry.has_plugin('task_line_parsing'):
        return self.plugin_registry.get_plugin('task_line_parsing')
    # 3. Fallback (lowest priority)
    if self.fallback_registry.has_fallback('task_line_parsing'):
        return self.fallback_registry.get_fallback('task_line_parsing')
    # 4. Raise if no policy found
    raise ValueError("No task_line_parsing policy available")
```

**Validation Gate 2.1**:
```bash
pytest tests/scanner_plugins/test_policy_manager.py::TestPolicyResolution -v
# Expected: 15-20 tests pass
```

**Estimated Effort**: 0.8 days

---

#### Task 2.2: Add Mock/Override Injection for Testing
**File**: `src/prism/scanner_plugins/policy_manager.py` (extensions)

**Scope**:
- Add `@contextmanager override_policy(kind, policy)` for testing
- Add `@contextmanager mock_registry(policies)` for fixture injection
- Verify mock injection doesn't affect other tests (thread isolation)

**Lines of Code**: 50-80  
**Tests**: 5-8 test cases

**Validation Gate 2.2**:
```bash
pytest tests/scanner_plugins/test_policy_manager.py::TestMockInjection -v
# Expected: 5-8 tests pass (isolated)
```

**Estimated Effort**: 0.4 days

---

#### Task 2.3: Update DIContainer to Include PolicyManager
**File**: `src/prism/scanner_core/di.py`

**Scope**:
- Add `policy_manager: PolicyManager` field to DIContainer
- Update `DIContainer.default()` to instantiate PolicyManager with:
  - `fallback_registry` (from Wave 1)
  - `plugin_registry` (existing)
  - `di` (self-reference for factory lookup)
- Add lazy initialization if needed

**Lines of Code**: 30-50  
**Tests**: 2-3 test cases

**Validation Gate 2.3**:
```bash
python -c "from src.prism.scanner_core.di import DIContainer; di = DIContainer.default(); p = di.policy_manager.resolve_task_line_parsing_policy(); print('✓')"
```

**Estimated Effort**: 0.3 days

**Wave 2 Total**: 1.5 days

---

## Wave 3: Caching Layer (1 day)

### Objective
Implement 3-level caching to achieve 1000x+ speedup in hotloops.

### Tasks

#### Task 3.1: Implement LocalPolicyCache (Level 2)
**File**: `src/prism/scanner_core/di_helpers.py` (or new)

**Scope**:
- `LocalPolicyCache` class with LRU or simple dict
- Cache key: `(di_identity, policy_kind)` → policy object
- Methods:
  - `get(di_identity, policy_kind)` → policy | None
  - `set(di_identity, policy_kind, policy)` → None
  - `clear()` → None (for testing)
  - `stats()` → (hits, misses, size) (for benchmarking)

**Lines of Code**: 60-100  
**Tests**: 8-12 test cases

**Validation Gate 3.1**:
```bash
pytest tests/scanner_core/test_policy_cache.py::TestLocalCache -v
# Expected: 8-12 tests pass; cache hit rate >95%
```

**Estimated Effort**: 0.4 days

---

#### Task 3.2: Integrate Cache into PolicyManager
**File**: `src/prism/scanner_plugins/policy_manager.py` (update)

**Scope**:
- Update `resolve_*()` methods to use LocalPolicyCache
- Check cache before fallback/registry lookup
- Populate cache on miss
- Document cache lifetime (per-scan)

**Lines of Code**: 40-60 (additions)  
**Tests**: 5-8 test cases (cache integration)

**Implementation Pattern**:
```python
def resolve_task_line_parsing_policy(self):
    # Level 2 cache check
    if self.cache:
        cached = self.cache.get(id(self.di), 'task_line_parsing')
        if cached is not None:
            return cached
    
    # Resolve via fallback/registry
    policy = self._resolve_policy_impl('task_line_parsing')
    
    # Store in cache
    if self.cache:
        self.cache.set(id(self.di), 'task_line_parsing', policy)
    
    return policy
```

**Validation Gate 3.2**:
```bash
pytest tests/integration/test_policy_caching.py::TestCacheIntegration -v
# Expected: 5-8 tests pass; verified cache hits
```

**Estimated Effort**: 0.3 days

---

#### Task 3.3: Pre-Compute Collection Constants (Level 3)
**File**: `src/prism/scanner_core/di_helpers.py` (additions)

**Scope**:
- Extract TASK_INCLUDE_KEYS → frozen set at bundle creation
- Pre-resolve INCLUDE_VARS_KEYS, SET_FACT_KEYS, etc.
- Store in PreparedPolicyBundle as immutable
- Update callers to use pre-resolved values (no re-resolution)

**Lines of Code**: 30-50  
**Tests**: 3-5 test cases

**Validation Gate 3.3**:
```bash
python -c "from src.prism.scanner_core.di_helpers import build_constants_cache; c = build_constants_cache(...); assert type(c['TASK_INCLUDE_KEYS']) == frozenset; print('✓')"
```

**Estimated Effort**: 0.3 days

**Wave 3 Total**: 1.0 days

---

## Wave 4: DIContainer & Integration (1 day)

### Objective
Integrate PolicyManager + caching into DIContainer; verify no regressions.

### Tasks

#### Task 4.1: Update DIContainer Initialization
**File**: `src/prism/scanner_core/di.py`

**Scope**:
- Initialize LocalPolicyCache in DIContainer.default()
- Pass cache to PolicyManager constructor
- Verify cache is cleared between scans (if needed)
- Add cache stats endpoint for monitoring

**Lines of Code**: 20-40  
**Tests**: 3-5 test cases

**Validation Gate 4.1**:
```bash
pytest tests/scanner_core/test_di_integration.py::TestDICache -v
# Expected: 3-5 tests pass; no lingering cache state
```

**Estimated Effort**: 0.3 days

---

#### Task 4.2: Create Backward Compatibility Wrappers
**File**: `src/prism/scanner_plugins/defaults.py` (update)

**Scope**:
- Update 6 legacy resolver functions to delegate to PolicyManager
- Add DeprecationWarning to each function
- Ensure old code still works without modification

**Implementation Pattern**:
```python
def resolve_task_line_parsing_policy_plugin(di):
    """DEPRECATED: Use di.policy_manager.resolve_task_line_parsing_policy()"""
    warnings.warn(
        "resolve_task_line_parsing_policy_plugin() is deprecated; "
        "use di.policy_manager.resolve_task_line_parsing_policy() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    if hasattr(di, 'policy_manager'):
        return di.policy_manager.resolve_task_line_parsing_policy()
    # Fallback for code without DI (rare)
    return _resolve_legacy_impl(di)
```

**Lines of Code**: 30-50 (total, for 6 functions)  
**Tests**: 6-8 test cases (one per wrapper)

**Validation Gate 4.2**:
```bash
pytest tests/scanner_plugins/test_backward_compat.py -v
# Expected: 6-8 tests pass; deprecation warnings verified
```

**Estimated Effort**: 0.4 days

---

#### Task 4.3: Run Full Test Suite (No Regressions)
**File**: pytest full suite

**Scope**:
- Run full unit test suite
- Run integration tests
- Verify no regressions from Wave 0-4 changes
- Document any warnings or failures

**Tests**: 200+ unit tests + integration suite

**Validation Gate 4.3**:
```bash
pytest tests/ -v --tb=short -x
# Expected: All tests pass; 0 failures; acceptable warnings only
```

**Estimated Effort**: 0.3 days (includes debugging if needed)

**Wave 4 Total**: 1.0 days

---

## Wave 5: Integration & Migration (1.5 days)

### Objective
Migrate existing code to PolicyManager; verify seamless integration.

### Tasks

#### Task 5.1: Migrate High-Priority Consumers
**Files**: 
- `src/prism/scanner_extract/task_line_parsing.py`
- `src/prism/scanner_extract/task_extract_adapters.py`
- `src/prism/scanner_core/task_annotation_parsing.py`

**Scope**:
- Replace `resolve_task_line_parsing_policy()` with `di.policy_manager.resolve_task_line_parsing_policy()`
- Replace `resolve_task_annotation_policy()` with `di.policy_manager.resolve_task_annotation_policy()`
- Replace direct resolver calls with facade calls
- Test each module after migration

**Lines Changed**: 80-120  
**Tests**: 15-20 test cases (module-level)

**Validation Gate 5.1**:
```bash
pytest tests/scanner_extract/ tests/scanner_core/ -v -k "task_parsing or annotation"
# Expected: All 15-20 tests pass; no deprecation warnings
```

**Estimated Effort**: 0.6 days

---

#### Task 5.2: Migrate Secondary Consumers
**Files**:
- `src/prism/scanner_extract/task_traversal.py`
- `src/prism/scanner_core/task_catalog.py`
- `src/prism/scanner_extract/variable_extractor.py`
- `src/prism/scanner_core/variable_discovery.py`

**Scope**:
- Replace resolver calls with PolicyManager facade
- Update imports
- Verify no behavioral changes

**Lines Changed**: 60-100  
**Tests**: 10-15 test cases (module-level)

**Validation Gate 5.2**:
```bash
pytest tests/scanner_extract/test_task_traversal.py tests/scanner_core/test_task_catalog.py -v
# Expected: All 10-15 tests pass
```

**Estimated Effort**: 0.5 days

---

#### Task 5.3: Migrate Configuration Loaders
**Files**:
- `src/prism/scanner_config/extract_defaults.py`
- `src/prism/scanner_config/policy_loaders.py` (if exists)

**Scope**:
- Consolidate 4 separate config loaders into ConfigPolicyLoader
- Integrate with PolicyManager
- Verify YAML config loading unchanged

**Lines Changed**: 40-80  
**Tests**: 5-8 test cases

**Validation Gate 5.3**:
```bash
pytest tests/scanner_config/test_policy_loaders.py -v
# Expected: All 5-8 tests pass
```

**Estimated Effort**: 0.4 days

**Wave 5 Total**: 1.5 days

---

## Wave 6: Performance Validation (0.5 days)

### Objective
Benchmark improvements; validate 28% speedup projection.

### Tasks

#### Task 6.1: Run Performance Benchmarks
**Files**: `tests/benchmarks/test_policy_performance.py`

**Scope**:
- Benchmark task catalog loop with/without cache
- Benchmark hotspots identified by Scout 4
- Compare before/after (Wave 0 baseline vs. Wave 5 + caching)
- Document speedup ratios

**Benchmarks**:
1. Task line parsing hotloop: target 1000x+
2. Task annotation extraction: target 100x+
3. Variable discovery: target 50x+
4. Overall scan time: target 28%

**Validation Gate 6.1**:
```bash
python tests/benchmarks/test_policy_performance.py --compare
# Expected: Speedup ratios meet targets; document results
```

**Estimated Effort**: 0.3 days

---

#### Task 6.2: Create Performance Report
**Files**: `docs/plan/g84-remediation-mutl3y-cycle-20260509/artifacts/phase-1-grader/performance-validation.md`

**Scope**:
- Report actual speedup numbers vs. projections
- Explain any variance (acceptable: ±10%)
- Identify any remaining hotspots
- Recommendation: proceed to Phase 3 (integration + closure)

**Estimated Effort**: 0.2 days

**Wave 6 Total**: 0.5 days

---

## Summary: 7-Wave Effort Breakdown

| Wave | Task | Days | Owner | Dependencies |
| --- | --- | --- | --- | --- |
| 0 | Preparation | 0.5 | Backend | None |
| 1 | FallbackPolicyRegistry | 1.0 | Backend | Wave 0 |
| 2 | PolicyManager Facade | 1.5 | Backend | Wave 0, 1 |
| 3 | Caching Layer | 1.0 | Backend | Wave 2 |
| 4 | DIContainer Integration | 1.0 | Backend | Wave 1, 2, 3 |
| 5 | Migration & Integration | 1.5 | Backend | Wave 2, 4 |
| 6 | Performance Validation | 0.5 | Backend | Wave 5 |
| **Total** | | **6.5 days** | **1 backend dev** | |

**Parallel Opportunities**:
- Waves 2 & 3 can start in parallel after Wave 1
- Wave 5 can start after Wave 2
- Total critical path: 5-6 days (if parallelized)

---

## Validation Gates Summary

| Gate | Command | Expected Result | Wave |
| --- | --- | --- | --- |
| 0.1 | `python -c "import src.prism.scanner_plugins.fallback_registry"` | ✓ Imports OK | 0 |
| 0.2 | `python -c "from src.prism.scanner_plugins.policy_manager import *"` | ✓ Types importable | 0 |
| 1.1 | `pytest tests/scanner_plugins/test_fallback_registry.py -v` | All 8-10 tests pass | 1 |
| 1.2 | `python -c "from src.prism.scanner_plugins.bootstrap import initialize_fallback_registry; r = initialize_fallback_registry(); assert r.has_fallback('task_line_parsing')"` | ✓ Bootstrap successful | 1 |
| 1.3 | `python -c "from src.prism.scanner_core.di import DIContainer; di = DIContainer.default(); assert hasattr(di, 'fallback_policy_registry')"` | ✓ DI integration OK | 1 |
| 2.1 | `pytest tests/scanner_plugins/test_policy_manager.py::TestPolicyResolution -v` | All 15-20 tests pass | 2 |
| 2.2 | `pytest tests/scanner_plugins/test_policy_manager.py::TestMockInjection -v` | All 5-8 tests pass (isolated) | 2 |
| 2.3 | `python -c "from src.prism.scanner_core.di import DIContainer; di = DIContainer.default(); p = di.policy_manager.resolve_task_line_parsing_policy()"` | ✓ PolicyManager ready | 2 |
| 3.1 | `pytest tests/scanner_core/test_policy_cache.py::TestLocalCache -v` | All 8-12 tests pass | 3 |
| 3.2 | `pytest tests/integration/test_policy_caching.py::TestCacheIntegration -v` | All 5-8 tests pass; cache hits verified | 3 |
| 3.3 | `python -c "from src.prism.scanner_core.di_helpers import build_constants_cache; c = build_constants_cache(...); assert type(c['TASK_INCLUDE_KEYS']) == frozenset"` | ✓ Constants cached | 3 |
| 4.1 | `pytest tests/scanner_core/test_di_integration.py::TestDICache -v` | All 3-5 tests pass; no lingering cache | 4 |
| 4.2 | `pytest tests/scanner_plugins/test_backward_compat.py -v` | All 6-8 tests pass; deprecation warnings OK | 4 |
| 4.3 | `pytest tests/ -v --tb=short` | All tests pass; 0 failures | 4 |
| 5.1 | `pytest tests/scanner_extract/ tests/scanner_core/ -v -k "task_parsing or annotation"` | All 15-20 tests pass; no deprecation warnings | 5 |
| 5.2 | `pytest tests/scanner_extract/test_task_traversal.py tests/scanner_core/test_task_catalog.py -v` | All 10-15 tests pass | 5 |
| 5.3 | `pytest tests/scanner_config/test_policy_loaders.py -v` | All 5-8 tests pass | 5 |
| 6.1 | `python tests/benchmarks/test_policy_performance.py --compare` | Speedup ratios documented | 6 |

---

## Release Ready Criteria

Before proceeding to Phase 3:
- ✅ All 18 validation gates passed
- ✅ All unit tests passing (0 failures)
- ✅ All integration tests passing
- ✅ Performance benchmarks confirm 28% speedup
- ✅ Backward compatibility verified (old code works with warnings)
- ✅ No regressions detected
- ✅ Documentation updated

---

## Risks & Mitigations

| Risk | Severity | Mitigation | Owner |
| --- | --- | --- | --- |
| Regression in task parsing | HIGH | Full unit test suite before Wave 4.3 | Backend |
| Performance less than 28% | MEDIUM | Benchmark early (Wave 6); adjust caching if needed | Backend |
| Thread safety issue | MEDIUM | GIL-based protection; immutable policies design | Backend |
| Deprecation warnings too noisy | LOW | Adjust warning level in Phase 3 if needed | Backend |

---

## Status

🟢 **SEQUENCE LOCKED** — Ready for Phase 2 Implementation

- Wave breakdown complete
- Dependencies verified
- Validation gates defined
- Effort estimated
- Owner assigned

**Next Step**: Begin Wave 0 preparation immediately

---

**Prepared By**: gem-reviewer (Grader)  
**Date**: May 9, 2026  
**Status**: ✅ LOCKED FOR PHASE 2
