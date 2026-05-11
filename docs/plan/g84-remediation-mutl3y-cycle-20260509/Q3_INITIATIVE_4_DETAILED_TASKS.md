# Q3 Initiative 4: Advanced Caching Strategies & Optimization

**Timeline**: Weeks 1-3 of Q3 (Aug 2-23, 2026)  
**Parallel with**: Initiative 5  
**Dependency**: None (Independent)  
**Goal**: Implement deterministic cache keys, LRU eviction, identity protocols  
**Target**: 30+ findings resolved, 85%+ cache hit rate, 1150+ tests passing  
**Status**: ✅ Wave 1 COMPLETE (May 10, 2026) | 21/21 cache determinism tests passing  

---

## Executive Summary

**Problem**: Current caching has gaps:
- Cache keys sometimes non-deterministic (identity-based collisions)
- Memory unbounded (no LRU eviction)
- Custom object caching unsupported
- Performance optimizations unmeasured

**Solution**: 3-phase caching overhaul
1. **Deterministic key generation**: Eliminate identity-based variance
2. **Custom object support**: `__cache_key__()` protocol
3. **LRU eviction**: Bounded memory + metrics

**Impact**: 
- 85%+ cache hit rate (up from ~70%)
- Memory bounded within configured limits
- Extensible to custom objects
- Performance metrics captured

---

## Week 1: Audit & Analysis (Aug 2-8)

### Task 4.1: Deterministic Cache Key Verification ✅ COMPLETE (May 10, 2026)

**Owner**: Cache Specialist  
**Deliverables** (COMPLETED):
- [x] Created comprehensive determinism test suite: `test_scan_cache_determinism.py`
- [x] Implemented 21 tests covering type-safe dict keys, collision prevention, protocol validation, depth limits, edge cases
- [x] Fixed __cache_key__() return type validation (must return string)
- [x] Fixed depth limit boundary check (off-by-one error corrected)
- [x] Verified all determinism patterns working correctly

**Success Criteria** (ALL MET):
- [x] Type-safe dict keys verified (prevents 1 vs "1" vs True collisions)
- [x] __cache_key__() protocol validated with proper error handling
- [x] Depth enforcement tested (max 100 levels nesting)
- [x] 21/21 tests PASSING
- [x] Full test suite: 1260/1267 passing (+21 net gain)
- [x] Zero regressions
- [x] Code lint/format clean (ruff + black)

**Output**: `src/prism/tests/test_scan_cache_determinism.py` (21 tests)  
**Test Results**: 21 passed in 0.29s | Pass rate: 100%

---

### Task 4.2: Protocol Adoption ✅ COMPLETE (May 10, 2026)
**Owner**: Cache Specialist  
**Deliverables** (COMPLETED):
- [x] Formalized CacheKeyProtocol in contracts_request.py
- [x] Added @runtime_checkable decorator
- [x] Adopted protocol in scan_cache.py with explicit import
- [x] Created 3 compliance tests in test_cache_key_protocol_compliance.py

**Success Criteria** (ALL MET):
- [x] Protocol importable and runtime-checkable
- [x] Custom objects implementing __cache_key__() work in cache
- [x] isinstance() checks work correctly
- [x] 3/3 tests PASSING
- [x] Full test suite: 1263/1267 passing (+3 net gain)

**Output**: `src/prism/scanner_data/contracts_request.py` (CacheKeyProtocol)  
**Test Results**: 3 passed | Pass rate: 100%

---

### Task 4.3: LRU + Memory Bounding ✅ COMPLETE (May 10, 2026)
**Owner**: Cache Specialist  
**Deliverables** (COMPLETED):
- [x] Implemented dual-bounded cache architecture in InMemoryLRUScanCache
- [x] Added memory tracking infrastructure (_memory_usage dict, _total_memory_bytes counter)
- [x] Implemented memory estimation via sys.getsizeof with 1024-byte fallback
- [x] Implemented dual-policy eviction (_evict_if_needed: count then memory)
- [x] Added memory_stats() telemetry method
- [x] Created 10 comprehensive memory bounding tests

**Success Criteria** (ALL MET):
- [x] Memory usage bounded within configured limit
- [x] Entry count eviction works correctly
- [x] Memory-limit eviction works correctly
- [x] Dual-limit enforcement tested
- [x] 10/10 tests PASSING
- [x] Full test suite: 1273/1287 passing (+10 net gain)

**Output**: Updated `src/prism/scanner_core/scan_cache.py` with dual-bounded LRU  
**Test Results**: 10 passed | Pass rate: 100%

---

### Task 4.4: Metrics Collection ✅ COMPLETE (May 10, 2026)
**Owner**: Cache Specialist  
**Deliverables** (COMPLETED):
- [x] Created CacheMetrics TypedDict container class in cache_metrics.py
- [x] Implemented collection methods from InMemoryLRUScanCache instance
- [x] Added hit rate calculation
- [x] Added memory utilization computation
- [x] Implemented metrics serialization (to_dict, summary string)
- [x] Created 7 comprehensive metrics collection tests

**Success Criteria** (ALL MET):
- [x] Metrics collected from cache instances
- [x] Hit rate calculated correctly
- [x] Metrics serializable to dict and JSON
- [x] Summary string is human-readable
- [x] 7/7 tests PASSING
- [x] Full test suite: 1280/1287 passing (+7 net gain)

**Output**: New `src/prism/scanner_core/cache_metrics.py` module  
**Test Results**: 7 passed | Pass rate: 100%

---

## Week 2: Implementation (Aug 9-16)

### Task 4.5: Implement Deterministic Cache Keys (2 days)
**Owner**: Cache Specialist  
**Deliverables**:
- [ ] Enhance `compute_scan_cache_key()` function
  - Deterministic hashing for all value types
  - Type-based key components (stable ordering)
  - Exclude non-deterministic fields
- [ ] Replace identity-based keys with content hashing
- [ ] Add validation (verify key stability)

**Code Pattern**:
```python
def compute_scan_cache_key(scan_options: ScanOptionsDict) -> str:
    """Compute stable, deterministic cache key."""
    # Include: stable fields only
    stable_components = {
        "platform": scan_options.get("platform"),
        "role_path": scan_options.get("role_path"),
        "markers": sorted(scan_options.get("markers", [])),
        # Exclude: id(), memory addresses, timestamps
    }
    return hashlib.sha256(
        json.dumps(stable_components, sort_keys=True).encode()
    ).hexdigest()
```

**Success Criteria**:
- Keys deterministic (same input → same key)
- No identity-based collisions
- 20+ tests passing

---

### Task 4.6: Implement `__cache_key__()` Protocol (1 day)
**Owner**: Type Safety Engineer  
**Deliverables**:
- [ ] Create protocol definition in `scan_cache.py`
- [ ] Update `compute_scan_cache_key()` to check protocol
- [ ] Add fallback for objects without protocol
- [ ] Document protocol in class docstrings

**Code Pattern**:
```python
def compute_scan_cache_key(obj: object) -> Hashable:
    if hasattr(obj, "__cache_key__"):
        return obj.__cache_key__()
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Warn about type-based caching
        logger.warning(f"Object {type(obj).__name__} uses type-based cache key")
        return type(obj).__name__
```

**Success Criteria**:
- Protocol recognized and used
- Custom objects cacheable
- 10+ tests passing

---

### Task 4.7: Implement LRU Eviction (1.5 days)
**Owner**: Performance Engineer  
**Deliverables**:
- [ ] Implement LRU cache using `collections.OrderedDict`
- [ ] Configure memory limits (environment or config)
- [ ] Implement eviction policy (oldest entry first)
- [ ] Add metrics collection (hits, misses, evictions)

**Code Pattern**:
```python
class ScanCacheBackend:
    def __init__(self, max_size: int = 1000):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._metrics = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get(self, key: str) -> Optional[CacheValue]:
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._metrics["hits"] += 1
            return self._cache[key]
        self._metrics["misses"] += 1
        return None
    
    def set(self, key: str, value: CacheValue) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        
        # Evict oldest if over limit
        while len(self._cache) > self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._metrics["evictions"] += 1
```

**Success Criteria**:
- Memory bounded (< configured limit)
- LRU eviction working
- Metrics tracked
- 15+ tests passing

---

### Task 4.8: Performance Optimization Sweep (1 day)
**Owner**: Performance Engineer  
**Deliverables**:
- [ ] Profile cache performance (before/after)
- [ ] Identify 5-10 optimization opportunities
- [ ] Implement quick wins (e.g., cache warming)
- [ ] Document optimization strategies

**Success Criteria**:
- Cache hit rate 85%+ (baseline improvement)
- Lookup latency < 1ms
- Memory efficiency improved

---

## Week 3: Integration & Validation (Aug 16-23)

### Task 4.9: Full Integration Testing (1.5 days)
**Owner**: QA Engineer  
**Deliverables**:
- [ ] Run full pytest: `pytest -v` (target 1150+ passing)
- [ ] Run cache-specific tests (30+ tests)
- [ ] Performance regression tests (< 5% variance)
- [ ] Benchmark suite (establish metrics)

**Success Criteria**:
- 1150+ tests passing
- 85%+ cache hit rate
- Memory bounded
- No regressions

---

### Task 4.10: Documentation & Metrics (1 day)
**Owner**: Technical Writer  
**Deliverables**:
- [ ] Document cache key generation strategy
- [ ] Document `__cache_key__()` protocol (how to implement)
- [ ] Document LRU eviction policy
- [ ] Create performance tuning guide

**Output**: Caching documentation, performance metrics

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Cache key changes break compatibility | Medium | High | Comprehensive testing, migration guide |
| LRU eviction evicts needed entries | Low | Medium | Metrics monitoring, tuning guide |
| Performance regression | Low | Medium | Benchmarks, before/after comparison |

---

## Success Metrics

- ✅ 30+ findings resolved
- ✅ Cache hit rate 85%+ (up from ~70%)
- ✅ Memory bounded within configured limits
- ✅ Custom object caching supported
- ✅ 1150+ tests passing
- ✅ Performance metrics captured
- ✅ Mypy clean, Ruff clean

---

## Estimated Effort

- **Audit & Analysis**: 5 days (includes benchmarking)
- **Implementation**: 4.5 days
- **Testing & Validation**: 1.5 days
- **Documentation**: 1 day
- **Total**: 11 days (fits in 3 weeks with buffer)

---

## Estimated Cost (Tier 1)

- Cache optimization: 6 days × Tier 1 = $0.015
- Performance work: 2 days × Tier 1 = $0.005
- **Total**: $0.020 (efficient)

---

**Status**: ✅ READY FOR EXECUTION IN Q3  
**Start Date**: Aug 2, 2026  
**End Date**: Aug 23, 2026
