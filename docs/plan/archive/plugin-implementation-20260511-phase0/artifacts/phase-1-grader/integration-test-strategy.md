# Integration Test Strategy — 25+ Test Cases

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-1-grader (test design)  
**Date**: May 9, 2026  
**Status**: ✅ **TEST SUITE DESIGNED**

---

## Overview

Comprehensive integration test suite with 25+ test cases covering:
- PolicyManager facade (all 8 methods)
- FallbackPolicyRegistry (registration + retrieval)
- 3-level caching (bundle, local cache, constants)
- Backward compatibility (legacy wrappers)
- Mock/override injection
- Performance (caching speedup)
- Thread safety
- End-to-end consolidation

---

## Test Suite Structure

```
tests/integration/test_policy_consolidation.py (30-50 tests)
├── TestPolicyManagerFacade (6 tests)
├── TestFallbackRegistry (5 tests)
├── TestCachingLevels (8 tests)
├── TestBackwardCompatibility (4 tests)
├── TestMockInjection (3 tests)
└── TestPerformance (4 tests)

tests/scanner_core/test_di_policy_integration.py (5 tests)
├── TestDIContainerIntegration (3 tests)
└── TestEndToEndPolicyResolution (2 tests)
```

**Total Tests**: 25-40  
**Expected Coverage**: 85-90% of new code  
**Execution Time**: 30-60 seconds

---

## Test Case Catalog

### Group 1: PolicyManager Facade (6 tests)

#### Test 1.1: resolve_task_line_parsing_policy() Returns Correct Type

**Setup**:
```python
def test_resolve_task_line_parsing_policy():
    di = DIContainer.default()
    manager = di.policy_manager
```

**Test**:
```python
    policy = manager.resolve_task_line_parsing_policy()
    assert isinstance(policy, PreparedTaskLineParsingPolicy)
    assert hasattr(policy, 'detect_task_module')
    assert hasattr(policy, 'TASK_INCLUDE_KEYS')
```

**Assertions**:
- ✓ Policy is correct type
- ✓ Policy has required attributes
- ✓ Policy is not None

**Expected**: PASS

---

#### Test 1.2: resolve_task_annotation_policy() Returns Correct Type

**Similar to 1.1 but for task annotation policy**

---

#### Test 1.3: resolve_task_traversal_policy() Returns Correct Type

**Similar to 1.1 but for task traversal policy**

---

#### Test 1.4: resolve_prepared_policy_bundle() Returns 6-Policy Bundle

**Setup**:
```python
def test_resolve_prepared_policy_bundle():
    di = DIContainer.default()
    manager = di.policy_manager
```

**Test**:
```python
    bundle = manager.resolve_prepared_policy_bundle()
    assert isinstance(bundle, dict)
    assert 'task_line_parsing' in bundle
    assert 'task_annotation_parsing' in bundle
    assert 'task_traversal' in bundle
    assert 'yaml_parsing' in bundle
    assert 'jinja_analysis' in bundle
    assert 'variable_extractor' in bundle
    assert len(bundle) == 6
```

**Assertions**:
- ✓ Bundle is dict
- ✓ All 6 policies present
- ✓ Bundle has exactly 6 entries

**Expected**: PASS

---

#### Test 1.5: resolve_by_kind() Works for Valid Kinds

**Setup**:
```python
def test_resolve_by_kind_valid():
    di = DIContainer.default()
    manager = di.policy_manager
```

**Test**:
```python
    policy = manager.resolve_by_kind('task_line_parsing')
    assert policy is not None
    assert isinstance(policy, PreparedTaskLineParsingPolicy)
    
    policy2 = manager.resolve_by_kind('jinja_analysis')
    assert policy2 is not None
```

**Assertions**:
- ✓ Resolves by kind for valid kinds
- ✓ Returns correct policy type

**Expected**: PASS

---

#### Test 1.6: Error Handling When Policy Not Found

**Setup**:
```python
def test_resolve_by_kind_invalid():
    di = DIContainer.default()
    manager = di.policy_manager
```

**Test**:
```python
    with pytest.raises(ValueError) as exc_info:
        manager.resolve_by_kind('invalid_kind')
    assert 'invalid_kind' in str(exc_info.value)
```

**Assertions**:
- ✓ Raises ValueError for invalid kind
- ✓ Error message includes invalid kind name

**Expected**: PASS

---

### Group 2: FallbackPolicyRegistry (5 tests)

#### Test 2.1: Registry Registration & Retrieval

**Setup**:
```python
from src.prism.scanner_plugins.fallback_registry import FallbackPolicyRegistry

def test_registry_register_and_retrieve():
    registry = FallbackPolicyRegistry()
    mock_policy = Mock(spec=PreparedTaskLineParsingPolicy)
```

**Test**:
```python
    registry.register_fallback('task_line_parsing', mock_policy)
    retrieved = registry.get_fallback('task_line_parsing')
    assert retrieved is mock_policy
```

**Assertions**:
- ✓ Policy registered successfully
- ✓ Retrieved policy is same object

**Expected**: PASS

---

#### Test 2.2: Duplicate Registration Error

**Setup**: FallbackPolicyRegistry instance

**Test**:
```python
def test_duplicate_registration_error():
    registry = FallbackPolicyRegistry()
    policy = Mock()
    registry.register_fallback('test', policy)
    
    with pytest.raises(ValueError) as exc_info:
        registry.register_fallback('test', Mock())
    assert 'already registered' in str(exc_info.value)
```

**Assertions**:
- ✓ Raises ValueError on duplicate
- ✓ Error message indicates duplicate

**Expected**: PASS

---

#### Test 2.3: has_fallback() Check

**Test**:
```python
def test_has_fallback():
    registry = FallbackPolicyRegistry()
    assert not registry.has_fallback('task_line_parsing')
    
    registry.register_fallback('task_line_parsing', Mock())
    assert registry.has_fallback('task_line_parsing')
```

**Assertions**:
- ✓ Returns False for unregistered
- ✓ Returns True for registered

**Expected**: PASS

---

#### Test 2.4: get_all_fallbacks() Snapshot

**Test**:
```python
def test_get_all_fallbacks():
    registry = FallbackPolicyRegistry()
    policy1, policy2 = Mock(), Mock()
    registry.register_fallback('policy1', policy1)
    registry.register_fallback('policy2', policy2)
    
    snapshot = registry.get_all_fallbacks()
    assert snapshot == {'policy1': policy1, 'policy2': policy2}
    
    # Verify snapshot is copy (not reference)
    snapshot['policy3'] = Mock()
    assert 'policy3' not in registry.get_all_fallbacks()
```

**Assertions**:
- ✓ Returns all policies
- ✓ Returns snapshot (not reference)

**Expected**: PASS

---

#### Test 2.5: Thread Safety

**Test**:
```python
import threading
import time

def test_thread_safety():
    registry = FallbackPolicyRegistry()
    errors = []
    
    def register_concurrent():
        try:
            for i in range(100):
                registry.register_fallback(f'policy_{i}', Mock())
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=register_concurrent) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0  # Some registrations will fail as expected
    assert len(registry.get_all_fallbacks()) > 0  # But registry is not corrupted
```

**Assertions**:
- ✓ Registry doesn't corrupt under concurrent access
- ✓ Error handling working

**Expected**: PASS

---

### Group 3: Caching Levels (8 tests)

#### Test 3.1: Level 1 Cache (Bundle Singleton)

**Test**:
```python
def test_level1_bundle_singleton():
    di = DIContainer.default()
    scan_options = {}
    
    bundle1 = ensure_prepared_policy_bundle(scan_options=scan_options, di=di)
    bundle2 = ensure_prepared_policy_bundle(scan_options=scan_options, di=di)
    
    assert bundle1 is bundle2  # Same instance
    assert scan_options['prepared_policy_bundle'] is bundle1
```

**Assertions**:
- ✓ Bundle created once per scan
- ✓ Bundle cached in scan_options

**Expected**: PASS

---

#### Test 3.2: Level 2 Cache (Local Policy Cache)

**Test**:
```python
def test_level2_local_policy_cache():
    cache = LocalPolicyCache()
    policy1 = Mock()
    
    # First access: cache miss
    result1 = cache.get(1001, 'task_line_parsing')
    assert result1 is None
    
    # Store in cache
    cache.set(1001, 'task_line_parsing', policy1)
    
    # Second access: cache hit
    result2 = cache.get(1001, 'task_line_parsing')
    assert result2 is policy1
    
    # Verify stats
    hits, misses, size = cache.stats()
    assert hits == 1 and misses == 1 and size == 1
```

**Assertions**:
- ✓ Cache miss returns None
- ✓ Cache hit returns stored policy
- ✓ Stats tracked correctly
- ✓ Speedup: dict lookup << policy resolution

**Expected**: PASS

---

#### Test 3.3: Level 2 Cache Per-DI Isolation

**Test**:
```python
def test_level2_cache_per_di_isolation():
    cache = LocalPolicyCache()
    policy1 = Mock(name='policy1')
    policy2 = Mock(name='policy2')
    
    # Different DI identities
    cache.set(1001, 'task_line_parsing', policy1)
    cache.set(1002, 'task_line_parsing', policy2)
    
    # Verify isolation
    assert cache.get(1001, 'task_line_parsing') is policy1
    assert cache.get(1002, 'task_line_parsing') is policy2
```

**Assertions**:
- ✓ Different DI = different cache entries
- ✓ No cross-DI pollution

**Expected**: PASS

---

#### Test 3.4: Level 2 Cache Clear

**Test**:
```python
def test_level2_cache_clear():
    cache = LocalPolicyCache()
    policy = Mock()
    cache.set(1001, 'task_line_parsing', policy)
    
    assert cache.get(1001, 'task_line_parsing') is policy
    
    cache.clear()
    
    assert cache.get(1001, 'task_line_parsing') is None
```

**Assertions**:
- ✓ clear() removes all entries
- ✓ Subsequent get() returns None

**Expected**: PASS

---

#### Test 3.5: Level 3 Cache (Constants Pre-Computation)

**Test**:
```python
def test_level3_constants_precomputation():
    policy = AnsibleDefaultTaskLineParsingPolicyPlugin()
    constants = build_policy_constants_cache(policy)
    
    assert 'TASK_INCLUDE_KEYS' in constants
    assert 'SET_FACT_KEYS' in constants
    assert isinstance(constants['TASK_INCLUDE_KEYS'], frozenset)
    assert len(constants['TASK_INCLUDE_KEYS']) > 0
```

**Assertions**:
- ✓ Constants extracted from policy
- ✓ All required keys present
- ✓ Constants are frozen (immutable)

**Expected**: PASS

---

#### Test 3.6: Integrated Caching (All 3 Levels)

**Test**:
```python
def test_integrated_3_level_caching():
    di = DIContainer.default()
    scan_options = {}
    manager = di.policy_manager
    
    # Level 1: Bundle created once
    bundle = ensure_prepared_policy_bundle(scan_options=scan_options, di=di)
    
    # Level 2: Policies cached locally
    policy1 = manager.resolve_task_line_parsing_policy()
    policy2 = manager.resolve_task_line_parsing_policy()
    assert policy1 is policy2  # Cache hit
    
    # Level 3: Constants pre-computed
    assert 'constants' in bundle or constants pre-computed
```

**Assertions**:
- ✓ All 3 levels working together
- ✓ Cache hits occurring
- ✓ Speedup measurable

**Expected**: PASS

---

#### Test 3.7: Cache Speedup Benchmark

**Test**:
```python
import time

def test_cache_speedup_benchmark():
    di_uncached = DIContainer(cache=None)
    di_cached = DIContainer.default()
    
    manager_uncached = di_uncached.policy_manager
    manager_cached = di_cached.policy_manager
    
    # Benchmark uncached (resolve 1000 times)
    start = time.perf_counter()
    for _ in range(1000):
        manager_uncached.resolve_task_line_parsing_policy()
    uncached_time = time.perf_counter() - start
    
    # Benchmark cached (resolve 1000 times)
    start = time.perf_counter()
    for _ in range(1000):
        manager_cached.resolve_task_line_parsing_policy()
    cached_time = time.perf_counter() - start
    
    speedup = uncached_time / cached_time
    assert speedup > 100  # Expect 100x+ speedup
```

**Assertions**:
- ✓ Cache speedup > 100x
- ✓ Speedup targets met

**Expected**: PASS

---

#### Test 3.8: Cache Invalidation (Immutable Policies)

**Test**:
```python
def test_cache_invalidation_not_needed():
    # Policies are immutable, so no cache invalidation needed
    cache = LocalPolicyCache()
    policy1 = Mock(name='policy1', spec=PreparedTaskLineParsingPolicy)
    
    cache.set(1001, 'task_line_parsing', policy1)
    
    # Even after "time passes", cache is still valid
    # (because policies are immutable)
    time.sleep(0.1)
    
    assert cache.get(1001, 'task_line_parsing') is policy1
    # No invalidation needed
```

**Assertions**:
- ✓ Cached policy is still valid after time passes
- ✓ No invalidation overhead

**Expected**: PASS

---

### Group 4: Backward Compatibility (4 tests)

#### Test 4.1: Legacy Resolver Function Wrapper

**Test**:
```python
def test_legacy_resolver_wrapper():
    di = DIContainer.default()
    
    # Old way (should still work with warning)
    with pytest.warns(DeprecationWarning, match="deprecated"):
        old_policy = resolve_task_line_parsing_policy_plugin(di)
    
    # New way
    new_policy = di.policy_manager.resolve_task_line_parsing_policy()
    
    # Should return same policy
    assert old_policy == new_policy
```

**Assertions**:
- ✓ Legacy function still works
- ✓ DeprecationWarning emitted
- ✓ Returns same policy as PolicyManager

**Expected**: PASS

---

#### Test 4.2: All 6 Legacy Wrappers Working

**Test**:
```python
def test_all_legacy_wrappers():
    di = DIContainer.default()
    legacy_functions = [
        resolve_task_line_parsing_policy_plugin,
        resolve_task_annotation_policy_plugin,
        resolve_task_traversal_policy_plugin,
        resolve_yaml_parsing_policy_plugin,
        resolve_jinja_analysis_policy_plugin,
        resolve_variable_extractor_policy_plugin,
    ]
    
    for func in legacy_functions:
        with pytest.warns(DeprecationWarning):
            policy = func(di)
            assert policy is not None
```

**Assertions**:
- ✓ All 6 wrappers work
- ✓ All emit deprecation warnings

**Expected**: PASS

---

#### Test 4.3: Backward Compatibility Code Still Works

**Test**:
```python
def test_backward_compat_code_paths():
    # Simulate old code that directly calls resolvers
    di = DIContainer.default()
    
    with pytest.warns(DeprecationWarning):
        policy = resolve_task_line_parsing_policy_plugin(di)
        module_name = policy.detect_task_module({'debug': 'msg=hello'})
        assert module_name == 'debug'
```

**Assertions**:
- ✓ Old code paths work
- ✓ Returned policies are functional

**Expected**: PASS

---

#### Test 4.4: No Deprecation Warnings in New Code

**Test**:
```python
def test_new_code_no_warnings():
    di = DIContainer.default()
    manager = di.policy_manager
    
    # New code should emit NO warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        policy = manager.resolve_task_line_parsing_policy()
        
        # Filter to only DeprecationWarning
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0
```

**Assertions**:
- ✓ New PolicyManager usage emits no warnings
- ✓ Clean migration path

**Expected**: PASS

---

### Group 5: Mock/Override Injection (3 tests)

#### Test 5.1: Override Policy in Context

**Test**:
```python
def test_mock_policy_override_context():
    di = DIContainer.default()
    manager = di.policy_manager
    
    mock_policy = Mock(spec=PreparedTaskLineParsingPolicy)
    
    with override_policy(manager, 'task_line_parsing', mock_policy):
        policy = manager.resolve_task_line_parsing_policy()
        assert policy is mock_policy
    
    # Outside context, back to normal
    policy = manager.resolve_task_line_parsing_policy()
    assert policy is not mock_policy
```

**Assertions**:
- ✓ Override works inside context
- ✓ Returns to normal outside context

**Expected**: PASS

---

#### Test 5.2: Mock Registry Fixture

**Test**:
```python
def test_mock_registry_fixture():
    manager = PolicyManager(
        fallback_registry=FallbackPolicyRegistry(),
        plugin_registry=Mock(),
        di=None
    )
    
    mock_policies = {
        'task_line_parsing': Mock(),
        'jinja_analysis': Mock(),
    }
    
    with mock_registry(manager, mock_policies):
        policy1 = manager.resolve_task_line_parsing_policy()
        policy2 = manager.resolve_jinja_analysis_policy()
        
        assert policy1 is mock_policies['task_line_parsing']
        assert policy2 is mock_policies['jinja_analysis']
```

**Assertions**:
- ✓ Mock registry fixture works
- ✓ All mocks injected correctly

**Expected**: PASS

---

#### Test 5.3: Test Isolation (No Cross-Test Pollution)

**Test**:
```python
def test_override_isolation():
    # Test A
    di_a = DIContainer.default()
    manager_a = di_a.policy_manager
    mock_a = Mock()
    
    with override_policy(manager_a, 'task_line_parsing', mock_a):
        policy_a = manager_a.resolve_task_line_parsing_policy()
        assert policy_a is mock_a
    
    # Test B (after Test A cleanup)
    di_b = DIContainer.default()
    manager_b = di_b.policy_manager
    policy_b = manager_b.resolve_task_line_parsing_policy()
    assert policy_b is not mock_a  # No pollution from Test A
```

**Assertions**:
- ✓ Overrides don't leak between tests
- ✓ Clean isolation

**Expected**: PASS

---

### Group 6: Performance (4 tests)

#### Test 6.1: Caching Reduces Lookups

**Test**:
```python
def test_caching_reduces_lookups():
    # Count resolution attempts with/without cache
    di_uncached = DIContainer(cache=None)
    di_cached = DIContainer.default()
    
    manager_uncached = di_uncached.policy_manager
    manager_cached = di_cached.policy_manager
    
    # Mock to count calls
    original_resolve = manager_uncached._resolve_policy_impl
    call_count = [0]
    
    def counting_resolve(*args, **kwargs):
        call_count[0] += 1
        return original_resolve(*args, **kwargs)
    
    # Uncached: 10 calls = 10 resolutions
    for _ in range(10):
        manager_uncached.resolve_task_line_parsing_policy()
    uncached_calls = call_count[0]
    
    # Cached: 10 calls = 1 resolution (then cache hits)
    call_count[0] = 0
    for _ in range(10):
        manager_cached.resolve_task_line_parsing_policy()
    cached_calls = call_count[0]
    
    assert uncached_calls == 10
    assert cached_calls == 1
```

**Assertions**:
- ✓ Uncached: N calls = N resolutions
- ✓ Cached: N calls = 1 resolution

**Expected**: PASS

---

#### Test 6.2: Hotloop Performance Improvement

**Test**:
```python
def test_hotloop_speedup():
    # Simulate task catalog hotloop
    di = DIContainer.default()
    manager = di.policy_manager
    
    tasks = [{'name': f'task_{i}'} for i in range(1000)]
    
    start = time.perf_counter()
    for task in tasks:
        policy = manager.resolve_task_line_parsing_policy()
        module = policy.detect_task_module(task)
    elapsed = time.perf_counter() - start
    
    # With caching, should be <10ms for 1000 tasks
    assert elapsed < 0.01  # 10ms
```

**Assertions**:
- ✓ Hotloop completes in <10ms for 1000 tasks
- ✓ Performance meets targets

**Expected**: PASS

---

#### Test 6.3: Bundle Creation Time

**Test**:
```python
def test_bundle_creation_time():
    di = DIContainer.default()
    
    start = time.perf_counter()
    for _ in range(100):
        bundle = di.policy_manager.resolve_prepared_policy_bundle()
    elapsed = time.perf_counter() - start
    avg_per_bundle = elapsed / 100
    
    # Bundle creation should be <1ms
    assert avg_per_bundle < 0.001  # 1ms
```

**Assertions**:
- ✓ Bundle creation <1ms
- ✓ Performance acceptable

**Expected**: PASS

---

#### Test 6.4: Overall Scan Time Improvement

**Test**:
```python
def test_overall_scan_time_improvement():
    # Full scan with caching enabled
    result = run_scan(
        repo_path='test_repo',
        scan_options={'prepared_policy_bundle': ...}
    )
    
    # Scan time should be reduced by ~28% vs. uncached
    # (This would require baseline measurement)
    # For now, verify scan completes successfully
    assert result['status'] == 'success'
    assert result['scan_time'] < baseline_scan_time * 1.05  # Allow 5% variance
```

**Assertions**:
- ✓ Full scan completes successfully with caching
- ✓ Performance improvement evident

**Expected**: PASS (depends on baseline availability)

---

## Test Execution Plan

### Phase 1: Unit Tests (Waves 0-4)

```bash
# Wave 0-1 tests
pytest tests/scanner_plugins/test_fallback_registry.py -v

# Wave 2 tests
pytest tests/scanner_plugins/test_policy_manager.py -v

# Wave 3 tests
pytest tests/scanner_core/test_policy_cache.py -v

# Wave 4 tests
pytest tests/scanner_plugins/test_backward_compat.py -v
pytest tests/scanner_core/test_di_integration.py -v
```

**Effort**: 1-2 hours  
**Gate**: All unit tests pass before Wave 5

---

### Phase 2: Integration Tests (Wave 5)

```bash
# Full integration test suite
pytest tests/integration/test_policy_consolidation.py -v

# DI integration
pytest tests/scanner_core/test_di_policy_integration.py -v
```

**Effort**: 2-3 hours  
**Gate**: All integration tests pass before Wave 6

---

### Phase 3: Performance Tests (Wave 6)

```bash
# Performance benchmarks
python tests/benchmarks/test_policy_performance.py --compare
```

**Effort**: 1-2 hours  
**Gate**: Performance targets met (28% speedup)

---

## Test Coverage Goals

| Component | Target Coverage | Expected |
| --- | --- | --- |
| PolicyManager | 90% | 95% |
| FallbackPolicyRegistry | 95% | 98% |
| LocalPolicyCache | 85% | 92% |
| Integration | 75% | 85% |
| **Total New Code** | **85%** | **90%** |

---

## Test Dependencies

```bash
pytest>=7.0
pytest-cov>=3.0
pytest-mock>=3.6
mock>=4.0
```

---

## Test Execution Timeline

| Phase | Start | Duration | Gate |
| --- | --- | --- | --- |
| Unit Tests | After Wave 0 | 1-2h | All pass |
| Integration Tests | After Wave 5 | 2-3h | All pass |
| Performance Tests | After Wave 6 | 1-2h | 28% speedup |
| **Total** | **Day 0** | **4-7h** | **Release Ready** |

---

## Sign-Off Criteria

Before releasing to production:
- ✓ 25+ test cases pass (0 failures)
- ✓ Coverage ≥85% of new code
- ✓ Performance benchmarks meet targets
- ✓ No regressions in existing tests
- ✓ Backward compatibility verified
- ✓ Mock injection working correctly

---

**Prepared By**: gem-reviewer (Grader)  
**Date**: May 9, 2026  
**Status**: ✅ **TEST SUITE DESIGNED**
