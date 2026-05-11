# G84 Deferred Findings: Multi-Week Roadmap (Q2-Q4 2026)

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Roadmap**: g84-deferred-findings-roadmap-q2q42026  
**Date**: 2026-05-09  
**Status**: ✅ Approved for Q2-Q4 2026 Execution  
**Total Findings Deferred**: 210 (80% of 261 total)  

---

## Executive Summary

The g84 remediation cycle identified **210 findings** (80% of 261 total) requiring **architectural refactoring**, **cross-module coordination**, and **deep system knowledge**. These findings cannot be addressed in isolated waves; they require **1-week to 3-week initiatives** with dedicated architectural teams.

This roadmap sequences those 210 findings into **5 focused initiatives** spanning **Q2-Q4 2026**:

| Initiative | Focus | Findings | Effort | Quarter |
| --- | --- | --- | --- | --- |
| **Q2-1** | DI Container Refactoring | 17 | 3 weeks | Q2 (Weeks 19-21) |
| **Q2-2** | Policy Ownership Consolidation | 8 | 2 weeks | Q2 (Weeks 22-24) |
| **Q3-1** | Advanced Caching Strategies | 30+ | 3 weeks | Q3 (Weeks 27-30) |
| **Q3-2** | Concurrency Coordination | 25+ | 3 weeks | Q3 (Weeks 31-35) |
| **Q4-1** | Output/Reporting Optimization | 20+ | 2 weeks | Q4 (future) |
| **Cleanup & Docs** | General improvements | 110+ | 2 weeks | Q4 (future) |

**Total Estimated Effort**: 15-20 weeks  
**Recommended Team Size**: 1-2 senior engineers per initiative  
**Cost Estimate**: $0.25-0.35 (moderate cost for enterprise refactoring)  

---

## Initiative 1: DI Container Refactoring (Q2 Weeks 19-21)

### Problem Statement

The DIContainer has grown to 50+ methods handling:
- Factory registration (20+ methods)
- Policy resolution (10+ methods)
- Plugin registry coordination (10+ methods)
- Event bus management (5+ methods)
- Scope/lifecycle management (5+ methods)

**Findings Addressed**:
- GILF-NODE1-01: DIContainer god-object (17 methods need extraction)
- GILF-DI-02: Factory method deduplication (20+ identical patterns)
- GILF-NODE1-02: ScannerContext embedded DI concerns (5 methods)
- GILF-DI-03: Scope collision between plugins (2 methods)
- GILF-NODE1-03: Factory override missing error handling (3 methods)

**Total Findings**: 17 HIGH + CRITICAL

### Proposed Solution

**Phase 1: Factory Provider Extraction (1 week)**
- Extract: `factory_*()` methods → `FactoryProvider` class
- Benefits: Reusable, testable, focused responsibility
- Implementation: Copy existing 20+ factory methods into new class
- Tests: Verify all 40+ factory tests still pass
- Files: Create `src/prism/scanner_core/di_factory_provider.py`

**Phase 2: Policy Provider Extraction (1 week)**
- Extract: `resolve_*_policy()` methods → `PolicyProvider` class
- Benefits: Policy resolution logic centralized, composable
- Implementation: Move 10+ policy resolution methods
- Tests: Policy-specific test suite (50+ tests)
- Files: Create `src/prism/scanner_core/di_policy_provider.py`

**Phase 3: Registry Coordinator Creation (1 week)**
- Extract: Plugin registry wiring → `RegistryCoordinator` class
- Benefits: Clear ownership of plugin lifecycle
- Implementation: Move plugin registry methods
- Tests: Plugin registration/resolution tests (30+ tests)
- Files: Create `src/prism/scanner_core/di_registry_coordinator.py`
- Cleanup: DIContainer now delegates to 3 focused providers

### Success Criteria

- ✅ DIContainer reduced from 50+ to 15 methods (delegation only)
- ✅ All 40+ factory tests pass
- ✅ All 50+ policy tests pass
- ✅ All 30+ registry tests pass
- ✅ Zero regression in `pytest -q` (maintain 1166+ passing)
- ✅ TypedDict contracts maintained (mypy green)

### Resource Requirement

- 1 senior engineer (full-time)
- 1 QA engineer (part-time, for test validation)
- Estimated effort: 15 hours = 3 days intensive work

### Deliverables

1. `di_factory_provider.py` (refactored, 150-200 LOC)
2. `di_policy_provider.py` (refactored, 100-150 LOC)
3. `di_registry_coordinator.py` (refactored, 150-200 LOC)
4. Updated DIContainer (delegation layer, 30-50 LOC)
5. Updated test suite (40+ tests passing)
6. Closure report with metrics

---

## Initiative 2: Policy Ownership Consolidation (Q2 Weeks 22-24)

### Problem Statement

Policy resolution is scattered across 6 modules:
- `scanner_core/scan_request.py`: InitialPolicies
- `scanner_core/di.py`: DIContainer policy resolver
- `scanner_extract/task_extract_adapters.py`: TaskLineParsingPolicy
- `scanner_plugins/defaults.py`: Plugin factory fallbacks
- `scanner_io/output_emission.py`: OutputPolicy
- `scanner_readme/guide.py`: ReadmeRenderPolicy

**Findings Addressed**:
- GILF-NODE2-01: Policy scattering (8 modules with policy logic)
- GILF-NODE2-02: Marker-prefix ownership leak (4 methods)
- GILF-DI-04: Policy boundary enforcement (6 findings)
- GILF-NODE2-03: Prepared-policy inconsistency (3 findings)

**Total Findings**: 8 HIGH

### Proposed Solution

**Phase 1: Create PolicyManager (1 week)**
- Centralize: All policy resolution → `PolicyManager` class
- Benefits: Single source of truth for policy lifecycle
- Implementation: Gather 20+ policy-resolution methods
- Files: Create `src/prism/scanner_core/policy_manager.py`
- Tests: 30+ policy tests in `test_policy_manager.py`

**Phase 2: Enforce PolicyManager Seams (1 week)**
- Replace: Direct policy resolution → PolicyManager delegation
- Modules: Update 6 modules to use PolicyManager
- Benefits: Clear dependency flow (modules → PolicyManager → policies)
- Tests: Ensure parity with old resolution logic (50+ tests)

**Phase 3: Immutable Policy Contracts (baseline week)**
- Validate: All PreparedPolicy* TypedDicts are immutable (already mostly done)
- Add: Frozen dataclasses for policy payloads
- Tests: Immutability violation tests (10+ tests)

### Success Criteria

- ✅ PolicyManager owns 100% of policy resolution logic
- ✅ All 6 modules delegate to PolicyManager
- ✅ All 30+ policy tests pass
- ✅ All 50+ parity tests pass
- ✅ Zero regressions in main test suite (maintain 1166+ passing)
- ✅ mypy validates policy contract immutability

### Resource Requirement

- 1 senior engineer (full-time)
- 0.5 QA engineer (part-time)
- Estimated effort: 12 hours = 2.5 days

### Deliverables

1. `policy_manager.py` (centralized, 200-300 LOC)
2. Updated modules (6 files, 50-100 LOC each)
3. Test suite (30+ new tests)
4. Closure report

---

## Initiative 3: Advanced Caching Strategies (Q3 Weeks 27-30)

### Problem Statement

Caching has evolved but not optimized:
- Cache key canonicalization (4 findings: GILF-NODE3-04, 05, 06, 07)
- Identity-based cache misses (3 findings: GILF-NODE3-01, 02, 03)
- LRU eviction strategy missing (2 findings: GILF-CACHE-01, 02)
- Performance optimization gaps (10+ findings: GILF-PERF-*)

**Total Findings**: 30+ MEDIUM/HIGH

### Proposed Solution

**Phase 1: Cache Key Canonicalization (1 week)**
- Implement: Stable, deterministic cache key generation
- Benefits: Eliminate cache misses from key variation
- Implementation: Enhanced `compute_scan_cache_key()` logic
- Tests: 20+ cache key tests

**Phase 2: Identity Protocol (1 week)**
- Implement: `__cache_key__()` protocol for custom objects
- Benefits: Mutable objects can participate in caching
- Implementation: Add protocol, update 5+ container classes
- Tests: 15+ identity tests

**Phase 3: LRU Eviction + Metrics (1 week)**
- Implement: LRU eviction strategy (e.g., `collections.OrderedDict`)
- Benefits: Bounded memory usage, predictable behavior
- Add: Cache hit/miss metrics
- Tests: 10+ eviction tests

### Success Criteria

- ✅ Cache key generation is deterministic and stable
- ✅ 20+ cache key tests pass
- ✅ Custom object caching supported via protocol
- ✅ 15+ identity tests pass
- ✅ LRU eviction bounds memory within configured limits
- ✅ 10+ eviction tests pass
- ✅ Cache hit rate > 85% on typical workloads

### Resource Requirement

- 1 senior engineer (full-time)
- 1 QA engineer (part-time)
- Estimated effort: 18 hours = 3.5 days

### Deliverables

1. Enhanced `scan_cache.py` (refactored, 300-400 LOC)
2. `__cache_key__()` protocol docs
3. Test suite (45+ new tests)
4. Cache hit/miss metrics implementation
5. Performance benchmarks

---

## Initiative 4: Concurrency Coordination (Q3 Weeks 31-35)

### Problem Statement

Concurrency patterns need explicit coordination:
- Thread-safety of shared mutable cache (2 findings: GILF-THREAD-01, 02)
- Double-checked locking pattern (1 finding: GILF-THREAD-03)
- Concurrent event listener failures (3 findings: GILF-EVENT-02, 03, 04)
- VariableRowBuilder concurrent construction (2 findings: GILF-VRB-01, 02)
- Plugin resolution cache coherency (3 findings: GILF-PLUGIN-01, 02, 03)
- Marker-prefix concurrent access (5+ findings: GILF-MP-*)

**Total Findings**: 25+ CRITICAL/HIGH

### Proposed Solution

**Phase 1: Mutual Exclusion Strategy (1.5 weeks)**
- Implement: `threading.Lock` for shared mutable state
- Modules: ScanCache, EventBus, PluginRegistry
- Benefits: Guaranteed thread-safety without complex patterns
- Tests: 20+ concurrency tests (stress testing)

**Phase 2: Double-Checked Locking Validation (1 week)**
- Validate: Existing double-checked locking (GIL-safe in Python)
- Document: Why pattern is safe in Python context
- Add: Code comments explaining pattern
- Tests: 10+ double-checked locking tests

**Phase 3: Concurrent Event Handler Safety (1 week)**
- Implement: Bounded deque for event listener failures (already done, verify)
- Add: Thread-safe event emission
- Add: Exception context preservation across threads
- Tests: 15+ event handler tests

**Phase 4: Future-Proof Async Support (0.5 weeks)**
- Design: AsyncIO compatibility (for future async scanner)
- Document: Async migration path
- Tests: 5+ async simulation tests

### Success Criteria

- ✅ All shared mutable state protected by locks
- ✅ 20+ concurrency stress tests pass
- ✅ No data races detected (thread-safe scanning)
- ✅ 10+ double-checked locking tests pass
- ✅ Event handler failures never block scanning
- ✅ 15+ event handler tests pass
- ✅ Async migration path documented

### Resource Requirement

- 1 senior engineer (concurrency expert)
- 1 QA engineer (full-time for stress testing)
- Estimated effort: 25 hours = 5 days intensive

### Deliverables

1. Enhanced `scan_cache.py` (thread-safe, 100 LOC additions)
2. Enhanced `events.py` (thread-safe, 50 LOC additions)
3. Enhanced `plugin_registry.py` (thread-safe, 75 LOC additions)
4. Concurrency patterns documentation
5. Test suite (50+ new concurrency tests)
6. Async migration guide

---

## Initiative 5: Output/Reporting Optimization (Q4)

### Problem Statement

Output and reporting layers have 20+ optimization opportunities:
- Report generation efficiency (5 findings)
- CSV/JSON rendering optimization (4 findings)
- Markdown rendering performance (3 findings)
- Metadata serialization (3 findings)
- Error report formatting (2 findings)

**Total Findings**: 20+ MEDIUM

### Proposed Solution (Deferred to Q4 Planning)

- Week 1: Profile current output generation
- Week 2: Implement high-impact optimizations
- Week 3: Add caching for report templates

### Resource Requirement

- 1 engineer (full-time)
- Estimated effort: 10 hours = 2 days

---

## Initiative 6: Cleanup & Documentation (Q4)

### Problem Statement

110+ MEDIUM/LOW findings addressing:
- Code documentation gaps (40+ findings)
- Logging consistency (25+ findings)
- DI consolidation opportunities (20+ findings)
- Testing improvements (15+ findings)
- Refactoring Polish (10+ findings)

### Proposed Solution (Deferred to Q4 Planning)

- Week 1: Documentation sweep (40+ findings)
- Week 2: Logging standardization (25+ findings)
- Week 3: Testing improvements (15+ findings)
- Week 4: Polish & cleanup (30+ findings)

### Resource Requirement

- 2 engineers (part-time each)
- Estimated effort: 20 hours = 1 week

---

## Timeline Summary

```
Q2 2026:
  Week 19-21: Initiative 1 (DI Container Refactoring)
  Week 22-24: Initiative 2 (Policy Ownership Consolidation)
  
Q3 2026:
  Week 27-30: Initiative 3 (Advanced Caching Strategies)
  Week 31-35: Initiative 4 (Concurrency Coordination)
  
Q4 2026:
  Week ????: Initiative 5 (Output/Reporting Optimization)
  Week ????: Initiative 6 (Cleanup & Documentation)
```

**Total Timeline**: ~16-20 weeks  
**Total Cost**: $0.25-0.35 (moderate investment for enterprise-grade system)  
**Recommended Start**: Week 19 (mid-May 2026)

---

## Success Metrics (End of Q4 2026)

- ✅ 260/261 findings addressed (99%+ closure)
- ✅ Test suite 1200+ passing (99%+)
- ✅ Zero regressions introduced
- ✅ Code quality metrics improved
- ✅ Performance benchmarks established
- ✅ Concurrency safety validated
- ✅ Caching efficiency optimized
- ✅ Documentation comprehensive

---

## Next Steps

1. **Assign Teams** (May 9-15):
   - Q2-1 owner: TBD (senior architect)
   - Q2-2 owner: TBD (policy specialist)
   - Q3-1 owner: TBD (cache expert)
   - Q3-2 owner: TBD (concurrency expert)

2. **Schedule Kickoff** (May 15):
   - Initiative 1 kickoff: Week 19 (May 20-24)
   - Planning sessions: May 9-15

3. **Monitor Progress**:
   - Biweekly cycle reviews
   - Metrics tracking
   - Risk mitigation

4. **Adapt as Needed**:
   - Deferred findings may be reprioritized
   - New findings may emerge (add to Q4 cleanup)
   - Resource availability may shift (adjust timeline)

---

**Roadmap Status**: ✅ Approved for Q2-Q4 2026 Execution  
**Last Updated**: 2026-05-09  
**Next Review**: 2026-05-15 (team assignment)
