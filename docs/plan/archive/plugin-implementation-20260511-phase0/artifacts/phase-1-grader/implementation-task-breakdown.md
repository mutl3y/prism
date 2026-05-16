# Implementation Task Breakdown — 20 Detailed Tasks

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-1-grader (task decomposition)  
**Date**: May 9, 2026  
**Status**: ✅ **READY FOR PHASE 2 ASSIGNMENT**

---

## Overview

20 implementation tasks broken down from 7 waves. Each task specifies:
- Inputs (files to read)
- Outputs (files to create/modify)
- Success criteria
- Test strategy
- Estimated effort
- Owner/assignee

---

## Wave 0: Preparation (3 tasks)

### Task 0.1: Create Module Directory Structure

**Summary**: Create all new Python modules (empty stubs with docstrings)

**Inputs**:
- Current filesystem structure
- Module naming conventions from project

**Outputs**:
- `src/prism/scanner_plugins/fallback_registry.py` (module docstring only)
- `src/prism/scanner_plugins/policy_manager.py` (module docstring only)
- `src/prism/scanner_plugins/bootstrap.py` (module docstring only)
- `src/prism/scanner_config/policy_loader.py` (module docstring only)
- `tests/scanner_plugins/test_fallback_registry.py` (test file stub)
- `tests/scanner_plugins/test_policy_manager.py` (test file stub)
- `tests/scanner_config/test_policy_loader.py` (test file stub)
- `tests/integration/test_policy_consolidation.py` (test file stub)

**Success Criteria**:
- ✓ All 8 files created
- ✓ All files are syntactically valid Python
- ✓ All files are importable without errors
- ✓ No circular import issues

**Test Strategy**:
```bash
python -c "import src.prism.scanner_plugins.fallback_registry; \
           import src.prism.scanner_plugins.policy_manager; \
           print('✓ All modules importable')"
```

**Effort**: 0.2 days  
**Owner**: Backend Developer

---

### Task 0.2: Extract & Document Protocol Definitions

**Summary**: Copy protocol definitions from contracts_request.py to policy_manager.py docstrings for reference

**Inputs**:
- `src/prism/scanner_data/contracts_request.py` (read protocols)
- Existing protocol definitions (6 Prepared* protocols)

**Outputs**:
- `src/prism/scanner_plugins/policy_manager.py` (module docstring with protocol specs)
- Documentation of all 8 PolicyManager methods (method signatures + docstrings)

**Success Criteria**:
- ✓ All 6 protocols documented
- ✓ All 8 PolicyManager method signatures specified
- ✓ No circular imports created
- ✓ Docstrings follow project style guide

**Test Strategy**:
```python
# Verify protocols are importable from policy_manager module
from src.prism.scanner_plugins.policy_manager import (
    PreparedTaskLineParsingPolicy,
    PreparedTaskAnnotationPolicy,
    # ... etc
)
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

---

### Task 0.3: Verify & Lock Interface Contract

**Summary**: Lock the 8-method PolicyManager interface as frozen contract

**Inputs**:
- Policy boundary scout findings (8 methods specified)
- Consolidation opportunities analysis (6 legacy resolvers → 1 facade)

**Outputs**:
- `src/prism/scanner_plugins/policy_manager.py` (interface specification frozen)
- Documentation: "This interface is LOCKED for backward compatibility"

**Success Criteria**:
- ✓ 8 methods specified with signatures
- ✓ All method docstrings complete
- ✓ Interface documented as immutable
- ✓ Sign-off in code (# INTERFACE LOCKED - g84 Phase 1)

**Effort**: 0.1 days  
**Owner**: Backend Developer

**Wave 0 Total**: 0.6 days

---

## Wave 1: FallbackPolicyRegistry (3 tasks)

### Task 1.1: Implement FallbackPolicyRegistry Class

**Summary**: Core registry class for 6 singleton fallback policies

**Inputs**:
- Protocol definitions (from Wave 0, Task 0.2)
- Thread-safety requirements (coordinator found potential race)
- Existing fallback pattern (from current code)

**Outputs**:
- `src/prism/scanner_plugins/fallback_registry.py` (FallbackPolicyRegistry class)
  - `__init__()`
  - `register_fallback(policy_kind, plugin)`
  - `get_fallback(policy_kind)`
  - `get_all_fallbacks()`
  - `has_fallback(policy_kind)`
  - `unregister_fallback(policy_kind)` (testing cleanup)

**Lines of Code**: 80-120

**Success Criteria**:
- ✓ Class definition complete
- ✓ All 6 methods implemented
- ✓ Thread-safe via RLock
- ✓ Type hints complete (mypy clean)
- ✓ Docstrings for all methods
- ✓ No external dependencies (only stdlib)

**Test Strategy**:
- Test registration and retrieval
- Test duplicate registration error
- Test None registration error
- Test get_all_fallbacks() returns snapshot (not reference)
- Test thread safety with concurrent access
- Test unregister cleanup

```bash
pytest tests/scanner_plugins/test_fallback_registry.py -v
# Expected: 10 tests pass, 0 failures, 0 warnings
```

**Effort**: 0.4 days  
**Owner**: Backend Developer

---

### Task 1.2: Implement Bootstrap Initialization

**Summary**: Bootstrap function to initialize registry with 6 default policies

**Inputs**:
- FallbackPolicyRegistry class (from Task 1.1)
- 6 default policy implementations (existing in codebase)
- Module import paths for default policies

**Outputs**:
- `src/prism/scanner_plugins/bootstrap.py`
  - `initialize_fallback_registry()` function
  - Imports of 6 default implementations
  - Registration of all 6 policies by kind

**Lines of Code**: 40-60

**Success Criteria**:
- ✓ Bootstrap function returns FallbackPolicyRegistry instance
- ✓ All 6 default policies registered by correct kind
- ✓ Callable without arguments (uses defaults)
- ✓ Type hints complete
- ✓ Docstring documents initialization order
- ✓ Clear error messages if registration fails

**Test Strategy**:
- Test bootstrap creates registry
- Test all 6 policies registered
- Test registry returned is functional
- Test idempotency (calling twice returns different instances)

```bash
python -c "from src.prism.scanner_plugins.bootstrap import initialize_fallback_registry; \
           r = initialize_fallback_registry(); \
           assert r.has_fallback('task_line_parsing'); \
           assert len(r.get_all_fallbacks()) == 6; \
           print('✓ Bootstrap OK')"
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

---

### Task 1.3: Integrate Registry into DIContainer

**Summary**: Add FallbackPolicyRegistry field to DIContainer; initialize in bootstrap

**Inputs**:
- DIContainer class definition (`src/prism/scanner_core/di.py`)
- FallbackPolicyRegistry class (from Task 1.1)
- Bootstrap function (from Task 1.2)

**Outputs**:
- `src/prism/scanner_core/di.py` (updated)
  - New field: `fallback_policy_registry: FallbackPolicyRegistry`
  - Updated `__init__()` to accept registry
  - Updated `DIContainer.default()` to initialize registry via bootstrap
  - Getter method (if needed): `get_fallback_policy_registry()`

**Lines of Code**: 20-40 (additions)

**Success Criteria**:
- ✓ DIContainer has fallback_policy_registry field
- ✓ DIContainer.default() initializes via bootstrap
- ✓ Registry accessible via di.fallback_policy_registry
- ✓ Type hints correct
- ✓ No circular imports
- ✓ Existing DIContainer tests still pass

**Test Strategy**:
- Test DIContainer.default() has registry
- Test registry is same instance as fallback_policy_registry
- Test registry is populated with 6 policies
- Test registry persists across multiple accesses

```bash
python -c "from src.prism.scanner_core.di import DIContainer; \
           di = DIContainer.default(); \
           assert hasattr(di, 'fallback_policy_registry'); \
           assert di.fallback_policy_registry.has_fallback('task_line_parsing'); \
           print('✓ DI Integration OK')"
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

**Wave 1 Total**: 1.0 days

---

## Wave 2: PolicyManager Facade (3 tasks)

### Task 2.1: Implement PolicyManager Core Class

**Summary**: Main facade class with 8 public methods for unified policy resolution

**Inputs**:
- FallbackPolicyRegistry (from Wave 1)
- PluginRegistry (existing)
- DIContainer (from Wave 1)
- Protocol definitions (from Wave 0)

**Outputs**:
- `src/prism/scanner_plugins/policy_manager.py`
  - PolicyManager class (200-300 lines)
  - `__init__(fallback_registry, plugin_registry, di, cache=None)`
  - 6 resolver methods (one per policy type)
  - `resolve_prepared_policy_bundle()` (atomic init)
  - `resolve_by_kind(kind)` (generic extensibility)
  - Private `_resolve_policy_impl()` helper
  - Resolution priority: DI factory → PluginRegistry → FallbackRegistry

**Lines of Code**: 200-300

**Success Criteria**:
- ✓ All 8 public methods implemented
- ✓ Resolution priority correct (DI → Plugin → Fallback)
- ✓ All methods return correct protocol type
- ✓ Error handling: ValueError if no policy found
- ✓ Type hints complete (mypy clean)
- ✓ Docstrings with examples
- ✓ Resolution logic matches scout design

**Test Strategy**:
- Test each of 6 resolver methods returns correct type
- Test resolution priority (DI override works)
- Test resolution priority (PluginRegistry override works)
- Test resolution priority (Fallback used when needed)
- Test error when no policy found
- Test `resolve_prepared_policy_bundle()` returns 6-policy bundle
- Test `resolve_by_kind()` with valid and invalid kinds
- Mock override injection (separate task)

```bash
pytest tests/scanner_plugins/test_policy_manager.py::TestPolicyResolution -v
# Expected: 15-20 tests pass, 0 failures
```

**Effort**: 0.8 days  
**Owner**: Backend Developer

---

### Task 2.2: Implement Mock/Override Injection for Testing

**Summary**: Add test fixtures for overriding policies in unit tests

**Inputs**:
- PolicyManager class (from Task 2.1)
- Testing best practices (python unittest.mock patterns)
- Existing test fixtures in project

**Outputs**:
- `src/prism/scanner_plugins/policy_manager.py` (additions)
  - `@contextmanager override_policy(manager, kind, policy)`
  - `@contextmanager mock_registry(fallbacks)` context manager
  - Documentation of how to use in tests
  - Example test using override
- `tests/scanner_plugins/test_policy_manager.py` (additions)
  - Tests of override mechanism
  - Tests of mock registry
  - Tests of fixture isolation

**Lines of Code**: 50-80

**Success Criteria**:
- ✓ Override context manager works
- ✓ Mock registry context manager works
- ✓ Overridden policy takes precedence over fallback
- ✓ Override doesn't leak to other tests (isolation)
- ✓ Cleanup happens on context exit
- ✓ Thread-safe (if running parallel tests)
- ✓ Documentation and examples clear

**Test Strategy**:
- Test override takes effect within context
- Test override doesn't affect default after context
- Test multiple overrides in same context
- Test nested contexts work correctly
- Test parallel test isolation (no cross-test leakage)

```bash
pytest tests/scanner_plugins/test_policy_manager.py::TestMockInjection -v
# Expected: 8 tests pass, all isolated, 0 failures
```

**Effort**: 0.4 days  
**Owner**: Backend Developer

---

### Task 2.3: Integrate PolicyManager into DIContainer

**Summary**: Add PolicyManager field to DIContainer; initialize in default()

**Inputs**:
- PolicyManager class (from Task 2.1)
- DIContainer class definition (from Wave 1)
- FallbackPolicyRegistry instance (from Wave 1)
- PluginRegistry (existing)

**Outputs**:
- `src/prism/scanner_core/di.py` (updated)
  - New field: `policy_manager: PolicyManager`
  - Updated `__init__()` to accept policy_manager
  - Updated `DIContainer.default()` to instantiate PolicyManager with:
    - `fallback_registry=di.fallback_policy_registry`
    - `plugin_registry=di.plugin_registry`
    - `di=di` (self-reference)
    - `cache=None` (added in Wave 3)
  - Getter method (if needed): `get_policy_manager()`

**Lines of Code**: 30-50 (additions)

**Success Criteria**:
- ✓ DIContainer has policy_manager field
- ✓ PolicyManager initialized in DIContainer.default()
- ✓ PolicyManager has correct references (registry, plugin_registry, di)
- ✓ Type hints correct
- ✓ No circular imports
- ✓ Existing DIContainer tests still pass
- ✓ DIContainer can be instantiated with custom PolicyManager (for testing)

**Test Strategy**:
- Test DIContainer.default() has policy_manager
- Test policy_manager has correct references
- Test calling di.policy_manager.resolve_*() works
- Test PolicyManager methods return correct types
- Test existing DIContainer tests still pass (no regression)

```bash
python -c "from src.prism.scanner_core.di import DIContainer; \
           di = DIContainer.default(); \
           p = di.policy_manager; \
           policy = p.resolve_task_line_parsing_policy(); \
           print('✓ DI → PolicyManager → Policy OK')"
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

**Wave 2 Total**: 1.5 days

---

## Wave 3: Caching Layer (3 tasks)

### Task 3.1: Implement LocalPolicyCache

**Summary**: Level 2 cache for policy resolution (dict or LRU-based)

**Inputs**:
- Caching scout findings (Level 2 cache design)
- Performance targets (1000x+ speedup in hotloops)
- Hotspot analysis (6 identified hotspots)

**Outputs**:
- `src/prism/scanner_core/di_helpers.py` (additions or new section)
  - LocalPolicyCache class (60-100 lines)
  - `get(di_identity, policy_kind)` → policy | None
  - `set(di_identity, policy_kind, policy)` → None
  - `clear()` → None (for testing/between-scans cleanup)
  - `stats()` → (hits, misses, size) (for benchmarking)
  - `_build_key(di_identity, policy_kind)` helper

**Lines of Code**: 60-100

**Success Criteria**:
- ✓ Cache implemented as dict or LRU
- ✓ get() returns cached policy or None
- ✓ set() stores policy in cache
- ✓ clear() removes all entries
- ✓ stats() returns accurate hit/miss counters
- ✓ Thread-safe (GIL protects dict mutations)
- ✓ Type hints complete
- ✓ Docstrings document cache lifetime (per-scan)

**Test Strategy**:
- Test get() on empty cache returns None
- Test set() then get() returns same object
- Test hit/miss counting
- Test clear() empties cache
- Test cache key uniqueness (same policy, different DI → different cache entries)
- Test concurrent access (thread-safe)
- Benchmark cache overhead (should be <1μs per operation)

```bash
pytest tests/scanner_core/test_policy_cache.py::TestLocalCache -v
# Expected: 10-12 tests pass, 0 failures, cache speedup documented
```

**Effort**: 0.4 days  
**Owner**: Backend Developer

---

### Task 3.2: Integrate Cache into PolicyManager Resolution

**Summary**: Update PolicyManager resolver methods to use LocalPolicyCache

**Inputs**:
- PolicyManager class (from Wave 2)
- LocalPolicyCache class (from Task 3.1)
- Resolution priority: DI → Plugin → Fallback → Cache

**Outputs**:
- `src/prism/scanner_plugins/policy_manager.py` (updated)
  - Update `__init__()` to accept cache parameter
  - Update 6 resolver methods to check cache before resolving
  - Store resolved policies in cache
  - Private `_resolve_policy_impl()` (no cache, actual resolution)
  - Documentation of cache behavior

**Lines of Code**: 40-60 (additions/modifications)

**Success Criteria**:
- ✓ Resolver methods check cache first
- ✓ Cache miss triggers resolution
- ✓ Resolved policy stored in cache
- ✓ Cache key includes DI identity
- ✓ Type hints correct
- ✓ Resolution logic unchanged (backward compatible)
- ✓ Cache can be disabled (cache=None) for testing

**Test Strategy**:
- Test cache hit on second call
- Test cache miss on first call
- Test cache per-DI isolation (different DI → different cache)
- Test resolution count (should be 1 if cached)
- Test override still works (overridden policy bypasses cache)
- Performance test (verify speedup vs. no-cache baseline)

```bash
pytest tests/integration/test_policy_caching.py::TestCacheIntegration -v
# Expected: 8 tests pass, cache hits >95%, speedup documented
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

---

### Task 3.3: Pre-Compute Collection Constants (Level 3 Cache)

**Summary**: Extract immutable collection constants at bundle creation (no runtime re-resolution)

**Inputs**:
- Caching scout findings (Level 3 constants pre-resolution)
- Collection constants (TASK_INCLUDE_KEYS, SET_FACT_KEYS, etc.)
- PreparedPolicyBundle structure

**Outputs**:
- `src/prism/scanner_core/di_helpers.py` (additions)
  - `build_policy_constants_cache(policy)` function
  - Extract TASK_INCLUDE_KEYS → frozen set
  - Extract INCLUDE_VARS_KEYS → frozen set
  - Extract SET_FACT_KEYS → frozen set
  - Extract TASK_BLOCK_KEYS → frozen set
  - Extract TASK_META_KEYS → frozen set
  - Return dict[str, frozenset] of constants
- Update PreparedPolicyBundle to include pre-resolved constants
- Update callers to use pre-resolved values instead of re-resolving

**Lines of Code**: 30-50

**Success Criteria**:
- ✓ Constants extracted at bundle creation time (once per scan)
- ✓ All constants frozen (immutable)
- ✓ Constants accessible via bundle['constants'] or similar
- ✓ Callers use pre-resolved constants (no runtime re-resolution)
- ✓ Type hints correct
- ✓ No performance regression (should be neutral or faster)

**Test Strategy**:
- Test constants extracted from policy
- Test constants are frozen sets (immutable)
- Test constant values match original policy
- Test bundle can be created with constants
- Test callers can access pre-resolved constants
- Benchmark pre-resolution cost (should be <1ms per bundle)

```bash
pytest tests/scanner_core/test_policy_constants.py -v
# Expected: 5-8 tests pass, 0 failures, no regression
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

**Wave 3 Total**: 1.0 days

---

## Wave 4: DIContainer & Integration (3 tasks)

### Task 4.1: Update DIContainer to Include PolicyManager + Cache

**Summary**: Initialize LocalPolicyCache in DIContainer; pass to PolicyManager

**Inputs**:
- DIContainer class (from Wave 1, Task 1.3)
- LocalPolicyCache class (from Wave 3)
- PolicyManager class (from Wave 2)

**Outputs**:
- `src/prism/scanner_core/di.py` (updated)
  - New field: `policy_cache: LocalPolicyCache | None`
  - Updated `DIContainer.default()` to initialize cache
  - Updated `DIContainer.default()` to pass cache to PolicyManager
  - Optional: cache stats endpoint for monitoring

**Lines of Code**: 20-40

**Success Criteria**:
- ✓ DIContainer has policy_cache field
- ✓ Cache initialized in DIContainer.default()
- ✓ Cache passed to PolicyManager.__init__()
- ✓ Cache is None in testing (if cache=None param used)
- ✓ No lingering cache state between scans
- ✓ Type hints correct
- ✓ Stats endpoint functional (if added)

**Test Strategy**:
- Test DIContainer.default() has cache
- Test cache passed to PolicyManager
- Test cache is functional (hits occur)
- Test cache doesn't leak between scans (isolation)
- Test with cache=None works (for testing)
- Benchmark: verify speedup from caching

```bash
pytest tests/scanner_core/test_di_integration.py::TestDICache -v
# Expected: 5 tests pass, cache integration verified, no leakage
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

---

### Task 4.2: Create Backward Compatibility Wrappers

**Summary**: Update 6 legacy resolver functions to delegate to PolicyManager

**Inputs**:
- PolicyManager class (from Wave 2)
- DIContainer (from Wave 4, Task 4.1)
- 6 legacy resolver functions in `defaults.py`
- Backward compatibility requirements (6+ month soft deprecation)

**Outputs**:
- `src/prism/scanner_plugins/defaults.py` (updated, 6 functions)
  - `resolve_task_line_parsing_policy_plugin(di)` → delegates to PolicyManager
  - `resolve_task_annotation_policy_plugin(di)` → delegates to PolicyManager
  - `resolve_task_traversal_policy_plugin(di)` → delegates to PolicyManager
  - `resolve_yaml_parsing_policy_plugin(di)` → delegates to PolicyManager
  - `resolve_jinja_analysis_policy_plugin(di)` → delegates to PolicyManager
  - `resolve_variable_extractor_policy_plugin(di)` → delegates to PolicyManager
  - Each function emits DeprecationWarning with migration guidance
  - Fallback implementation (for code without DI) still works

**Lines of Code**: 30-50 (total for 6 functions)

**Success Criteria**:
- ✓ All 6 functions delegate to PolicyManager
- ✓ DeprecationWarning emitted each time
- ✓ Warning includes migration guidance
- ✓ Old code continues to work (backward compatible)
- ✓ Return types match original (no behavioral change)
- ✓ Fallback implementation present (for code without DI)
- ✓ Docstrings updated with deprecation notice

**Test Strategy**:
- Test each wrapper delegates to PolicyManager
- Test DeprecationWarning emitted
- Test returned policy matches PolicyManager result
- Test backward compatibility (old code still works)
- Test warning can be caught/suppressed in tests

```bash
pytest tests/scanner_plugins/test_backward_compat.py -v
# Expected: 8 tests pass, deprecation warnings verified
```

**Effort**: 0.4 days  
**Owner**: Backend Developer

---

### Task 4.3: Run Full Test Suite (Regression Check)

**Summary**: Execute entire test suite to verify no regressions from Waves 0-4

**Inputs**:
- All code changes from Waves 0-4
- Existing test suite
- CI/CD environment

**Outputs**:
- Test results report
- Coverage report
- Any warnings or failures documented
- Plan to fix any regressions

**Success Criteria**:
- ✓ All unit tests pass (0 failures)
- ✓ All integration tests pass (0 failures)
- ✓ No regressions from existing functionality
- ✓ Coverage maintained or improved
- ✓ Acceptable warnings only (deprecation warnings OK)
- ✓ Performance not degraded

**Test Strategy**:
```bash
pytest tests/ -v --tb=short -x --cov=src/prism --cov-report=html
# Expected: All tests pass; 0 failures; coverage stable
```

**Effort**: 0.3 days  
**Owner**: Backend Developer (+ debugging if needed)

**Wave 4 Total**: 1.0 days

---

## Wave 5: Migration & Integration (4 tasks)

### Task 5.1: Migrate High-Priority Consumers (Core Parsing)

**Summary**: Update task line parsing & annotation parsing modules to use PolicyManager

**Inputs**:
- PolicyManager (from Wave 2)
- 3 modules to migrate:
  - `src/prism/scanner_extract/task_line_parsing.py`
  - `src/prism/scanner_extract/task_extract_adapters.py`
  - `src/prism/scanner_core/task_annotation_parsing.py`
- Coordination scout call-site inventory

**Outputs**:
- Updated 3 modules (80-120 lines changed total)
  - Replace `resolve_task_line_parsing_policy()` calls with `di.policy_manager.resolve_task_line_parsing_policy()`
  - Replace `resolve_task_annotation_policy()` calls with `di.policy_manager.resolve_task_annotation_policy()`
  - Remove imports of old resolver functions
  - Update any caching or memoization patterns

**Success Criteria**:
- ✓ All calls migrated to PolicyManager
- ✓ Old resolver function calls removed
- ✓ No deprecation warnings in logs
- ✓ Functionality unchanged (same behavior)
- ✓ Tests updated to use new paths
- ✓ No new circular imports

**Test Strategy**:
- Run module tests: `pytest tests/scanner_extract/test_task_line_parsing.py`
- Run module tests: `pytest tests/scanner_extract/test_task_extract_adapters.py`
- Run module tests: `pytest tests/scanner_core/test_task_annotation_parsing.py`
- Verify no deprecation warnings in output
- Integration test to verify end-to-end parsing still works

```bash
pytest tests/scanner_extract/ tests/scanner_core/ -v -k "task_parsing or annotation" -W error::DeprecationWarning
# Expected: All 15-20 tests pass; 0 deprecation warnings
```

**Effort**: 0.6 days  
**Owner**: Backend Developer

---

### Task 5.2: Migrate Secondary Consumers (Traversal & Variables)

**Summary**: Update task traversal, task catalog, and variable discovery modules

**Inputs**:
- PolicyManager (from Wave 2)
- 4 modules to migrate:
  - `src/prism/scanner_extract/task_traversal.py`
  - `src/prism/scanner_core/task_catalog.py`
  - `src/prism/scanner_extract/variable_extractor.py`
  - `src/prism/scanner_core/variable_discovery.py`

**Outputs**:
- Updated 4 modules (60-100 lines changed total)
  - Replace resolver function calls with PolicyManager calls
  - Update imports
  - Remove old resolver function imports

**Success Criteria**:
- ✓ All resolver calls migrated
- ✓ No deprecation warnings
- ✓ Functionality unchanged
- ✓ Tests pass
- ✓ No circular imports

**Test Strategy**:
```bash
pytest tests/scanner_extract/test_task_traversal.py tests/scanner_core/test_task_catalog.py -v
# Expected: 10-15 tests pass; 0 deprecation warnings
```

**Effort**: 0.5 days  
**Owner**: Backend Developer

---

### Task 5.3: Migrate Configuration Loaders

**Summary**: Consolidate 4 separate policy loaders into unified ConfigPolicyLoader

**Inputs**:
- PolicyManager (from Wave 2)
- 2 modules with config loaders:
  - `src/prism/scanner_config/extract_defaults.py`
  - `src/prism/scanner_config/policy_loaders.py` (if exists)

**Outputs**:
- `src/prism/scanner_config/policy_loader.py` (new, consolidated)
  - ConfigPolicyLoader class
  - Load from YAML config
  - Integrate with PolicyManager
  - Override policies from config
- Updated 2 existing modules to delegate to ConfigPolicyLoader

**Lines of Code**: 40-80

**Success Criteria**:
- ✓ 4 loaders consolidated into 1
- ✓ YAML config loading preserved
- ✓ Policies overridable from config
- ✓ Backward compatible (old config still works)
- ✓ Tests pass
- ✓ No behavioral changes

**Test Strategy**:
```bash
pytest tests/scanner_config/test_policy_loader.py -v
# Expected: 5-8 tests pass; 0 failures
```

**Effort**: 0.4 days  
**Owner**: Backend Developer

---

### Task 5.4: Full Integration Test + Sanity Check

**Summary**: Run full test suite to verify all migrations complete and working

**Inputs**:
- All code changes from Waves 0-5
- Full test suite
- Real scan files (for smoke testing)

**Outputs**:
- Test results
- Integration test report
- Go/no-go decision for Wave 6

**Success Criteria**:
- ✓ All unit tests pass
- ✓ All integration tests pass
- ✓ No deprecation warnings in normal usage
- ✓ Smoke test: real scan completes successfully
- ✓ 0 regressions from previous work
- ✓ Ready for Wave 6 (performance validation)

**Test Strategy**:
```bash
pytest tests/ -v --tb=short
# Expected: All tests pass; ready for performance validation
```

**Effort**: 0.2 days  
**Owner**: Backend Developer

**Wave 5 Total**: 1.7 days

---

## Wave 6: Performance Validation (2 tasks)

### Task 6.1: Run Performance Benchmarks

**Summary**: Benchmark hotloops to verify 28% overall speedup projection

**Inputs**:
- Caching scout hotspot analysis (6 identified)
- Test data (real scan files or synthetic data)
- Baseline metrics (from Wave 0 or prior)

**Outputs**:
- Benchmark report: `tests/benchmarks/test_policy_performance.py` results
- Speedup ratios for each hotspot
- Overall scan time improvement
- Any anomalies or unexpected results

**Success Criteria**:
- ✓ Hotloop 1 (task catalog): 1000x+ speedup verified
- ✓ Hotloop 2 (annotation extraction): 100x+ speedup
- ✓ Hotloop 3 (variable discovery): 50x+ speedup
- ✓ Overall scan speedup: 20-30% (28% target)
- ✓ Memory overhead: <1KB per scan
- ✓ Benchmarks reproducible

**Test Strategy**:
```bash
python tests/benchmarks/test_policy_performance.py --compare --baseline=wave0
# Expected: Speedup targets met; results documented
```

**Effort**: 0.3 days  
**Owner**: Backend Developer

---

### Task 6.2: Create Performance Report

**Summary**: Document benchmark results and performance validation

**Inputs**:
- Benchmark results (from Task 6.1)
- Baseline metrics (from Phase 0 scouts)
- Caching strategy projections (from Phase 0 scouts)

**Outputs**:
- `docs/plan/g84-remediation-mutl3y-cycle-20260509/artifacts/phase-1-grader/performance-validation.md`
  - Executive summary
  - Benchmark results table
  - Speedup ratios per hotspot
  - Overall impact
  - Any variance explanations
  - Recommendation for Phase 3

**Success Criteria**:
- ✓ Results clearly documented
- ✓ Speedup targets met (within ±10%)
- ✓ Variance explained
- ✓ Recommendation clear (proceed to Phase 3)
- ✓ Report ready for stakeholders

**Effort**: 0.2 days  
**Owner**: Backend Developer

**Wave 6 Total**: 0.5 days

---

## Summary: 20 Task Effort Breakdown

| Wave | Task | Summary | Effort | Total |
| --- | --- | --- | --- | --- |
| 0.1 | Module Structure | Create directory structure | 0.2 | 0.6 |
| 0.2 | Protocol Definitions | Extract & document protocols | 0.3 | |
| 0.3 | Interface Lock | Freeze PolicyManager interface | 0.1 | |
| 1.1 | FallbackRegistry Class | Core registry implementation | 0.4 | 1.0 |
| 1.2 | Bootstrap | Bootstrap initialization | 0.3 | |
| 1.3 | DI Integration | Add to DIContainer | 0.3 | |
| 2.1 | PolicyManager Core | 8-method facade | 0.8 | 1.5 |
| 2.2 | Mock Injection | Test overrides | 0.4 | |
| 2.3 | DI Integration | PolicyManager in DIContainer | 0.3 | |
| 3.1 | LocalPolicyCache | Level 2 cache implementation | 0.4 | 1.0 |
| 3.2 | Cache Integration | Cache in PolicyManager | 0.3 | |
| 3.3 | Constants Cache | Level 3 constants pre-computation | 0.3 | |
| 4.1 | DI + Cache | DIContainer integration | 0.3 | 1.0 |
| 4.2 | Backward Compat | Legacy wrapper functions | 0.4 | |
| 4.3 | Regression Test | Full test suite | 0.3 | |
| 5.1 | Migration Phase 1 | Migrate core parsing modules | 0.6 | 1.7 |
| 5.2 | Migration Phase 2 | Migrate traversal/variable modules | 0.5 | |
| 5.3 | Config Migration | Consolidate loaders | 0.4 | |
| 5.4 | Integration Test | Full suite + sanity check | 0.2 | |
| 6.1 | Performance | Run benchmarks | 0.3 | 0.5 |
| 6.2 | Performance Report | Document results | 0.2 | |
| **TOTAL** | **20 tasks** | | | **6.8 days** |

---

## Effort Summary

**Total Effort**: 6.8 days (1 backend developer)  
**Parallel Opportunities**:
- Tasks 2.1 & 3.1 can start in parallel after Task 1.3
- Tasks 5.1, 5.2, 5.3 can run in parallel
- Task 6.1 starts after Wave 5 complete

**Critical Path**: 6 days (if optimally parallelized)

---

## Assignment & Tracking

Each task should be assigned to a developer with:
- Estimated effort in person-days
- Owner name
- Start date
- Completion date
- Sign-off required before proceeding to next wave

---

**Prepared By**: gem-reviewer (Grader)  
**Date**: May 9, 2026  
**Status**: ✅ **READY FOR PHASE 2 ASSIGNMENT**
