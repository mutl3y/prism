# Q3 Initiatives 4-6: Phase 5 Builder Dispatch (Tier 0 Scout Planning)

**Status**: 🚀 READY TO DISPATCH  
**Date**: 2026-05-09  
**Phase**: 5 (Builder Execution Mapping)  
**Tier**: 0 (FREE, 0.33x baseline cost)  
**Timeline**: 2-3 hours (scout mapping) + 8-12 hours (builder execution)

---

## Executive Summary

Three Q3 initiatives entering Phase 5 builders simultaneously:
- **Q3 Initiative 4**: Immutability & Caching Optimization
- **Q3 Initiative 5**: Layer Boundary Enforcement  
- **Q3 Initiative 6**: Type Safety & Ownership Consolidation

**Tier 0 Scout Tasks** (Parallel):
1. **Scout-Init4-CacheOpt**: Map caching refactor work (deterministic keys, LRU, custom objects)
2. **Scout-Init5-LayerBoundary**: Map layer boundary seams (plugin architecture, DI boundary)
3. **Scout-Init6-TypeSafety**: Map type safety improvements (@overload verification, protocols)

**Success Criteria**:
- Each scout delivers detailed implementation plan
- All 3 scouts complete within 2 hours
- Implementation readiness gate: Builder teams can start within 30 min of scout completion

---

## Initiative 4: Immutability & Caching Optimization

### Current State (From Phase 0-1 Audit)
- Cache keys sometimes non-deterministic (identity-based collisions)
- Memory unbounded (no LRU eviction policy)
- Custom object caching unsupported
- 30+ findings identified for Phase 5

### Phase 5 Scout Task: Scout-Init4-CacheOpt

**Owner**: Tier 0 Scout (GPT-4o, FREE)  
**Duration**: 45-60 minutes  
**Deliverable**: `phase-5-init4-builder-plan.yaml`

**Scope**:
1. Analyze `src/prism/scanner_cache.py` for:
   - Current cache key generation logic
   - Identity-based vs content-based hashing
   - LRU eviction strategies (missing or present?)
   - Custom object support (protocols or inheritance?)

2. Map implementation phases:
   - **Phase 5a**: Deterministic cache key generation (1-2 days)
   - **Phase 5b**: Custom object `__cache_key__()` protocol (1 day)
   - **Phase 5c**: LRU eviction implementation (2-3 days)
   - **Phase 5d**: Metrics collection & monitoring (1 day)

3. Identify builder team composition:
   - **Builder 1**: Cache-safety specialist
   - **Builder 2**: Performance engineer
   - **Builder 3**: Test infrastructure

4. Deliver plan with:
   - Exact file list to modify
   - Code snippets showing before/after patterns
   - Test strategy
   - Risk assessment
   - Estimated effort per phase

**Success Criteria**:
- ✅ Builder plan is immediately actionable
- ✅ No architectural ambiguity remaining
- ✅ Builder team can start without questions

---

## Initiative 5: Layer Boundary Enforcement

### Current State (From Phase 0-1 Audit)
- Plugin architecture seams unclear (direct imports across layers)
- DI container coupling to specific resolver implementations
- 40+ layer violation findings for Phase 5

### Phase 5 Scout Task: Scout-Init5-LayerBoundary

**Owner**: Tier 0 Scout (GPT-4o, FREE)  
**Duration**: 45-60 minutes  
**Deliverable**: `phase-5-init5-builder-plan.yaml`

**Scope**:
1. Analyze layer boundaries:
   - `scanner_core` (execution orchestration)
   - `scanner_plugins` (plugin kernel)
   - `scanner_extract` (extraction adapters)
   - `scanner_io` (I/O & output)

2. Map architecture seams:
   - Plugin protocol definitions
   - DI resolution boundaries
   - Import restriction rules
   - Interface facades (what should be public vs private?)

3. Identify implementation phases:
   - **Phase 5a**: Plugin protocol extraction (2-3 days)
   - **Phase 5b**: DI boundary enforcement (2-3 days)
   - **Phase 5c**: Layer import audit & fixes (2-3 days)
   - **Phase 5d**: Type-level boundary enforcement (1-2 days)

4. Builder team needs:
   - **Builder 1**: Architecture specialist
   - **Builder 2**: Plugin system expert
   - **Builder 3**: Type safety engineer

5. Deliver plan with:
   - Boundary diagrams (text-based)
   - Import rules to enforce
   - Protocol definitions
   - Refactoring sequences
   - Test harnesses

**Success Criteria**:
- ✅ Layer boundaries crystal clear
- ✅ Import restrictions automated (test coverage)
- ✅ Plugin protocols fully specified

---

## Initiative 6: Type Safety & Ownership Consolidation

### Current State (From Phase 0-1 Audit)
- 22 @overload signatures claimed but unverified
- Ownership consolidation incomplete (marker-prefix, policies)
- 35+ type safety findings for Phase 5

### Phase 5 Scout Task: Scout-Init6-TypeSafety

**Owner**: Tier 0 Scout (GPT-4o, FREE)  
**Duration**: 45-60 minutes  
**Deliverable**: `phase-5-init6-builder-plan.yaml`

**Scope**:
1. Type safety audit:
   - Verify all 22 @overload signatures (mypy validation)
   - Identify missing protocol implementations
   - Check TypedDict usage compliance
   - Audit generic type constraints

2. Ownership consolidation:
   - Marker-prefix ownership (who authorizes? who consumes?)
   - Policy ownership (prepared_policy_bundle authority)
   - Error ownership (who catches? who raises?)
   - Configuration ownership (who owns defaults?)

3. Implementation phases:
   - **Phase 5a**: @overload verification & fixes (1-2 days)
   - **Phase 5b**: Protocol implementation completion (2-3 days)
   - **Phase 5c**: TypedDict conformance audit (1-2 days)
   - **Phase 5d**: Ownership consolidation (2-3 days)

4. Builder team:
   - **Builder 1**: Type safety specialist
   - **Builder 2**: Protocol architect
   - **Builder 3**: Ownership auditor

5. Deliver plan with:
   - @overload verification checklist (22 items)
   - Protocol implementation matrix
   - TypedDict compliance report
   - Ownership transfer plan
   - Type coverage metrics

**Success Criteria**:
- ✅ All 22 @overload signatures verified
- ✅ Ownership consolidation roadmap clear
- ✅ Type safety tooling ready

---

## Parallel Scout Dispatch

**Dispatch Strategy**: All 3 scouts launched simultaneously (zero coordination overhead)

```
2026-05-09 15:00 UTC
├─ Scout-Init4-CacheOpt: Phase 5 builder plan
├─ Scout-Init5-LayerBoundary: Phase 5 builder plan
└─ Scout-Init6-TypeSafety: Phase 5 builder plan
    │
    └─ [60 minutes]
       └─ 2026-05-09 16:00 UTC: All scouts report → Builder planning begins
```

**Join Point**: After all 3 scouts complete, builder teams are formed

---

## Post-Scout Handoff: Builder Team Formation

**After Scout Reports Received**:

### Initiative 4 Builder Team: Phase 5a (1 day)
- **Team**: 3 builders (cache-safety, performance, test)
- **Work**: Deterministic cache key generation
- **Files**: `scanner_cache.py`, `test_cache_determinism.py`
- **Output**: 200+ lines new code, 15+ new tests
- **Tier**: 2 (BALANCED, 1x) if complex refactoring

### Initiative 5 Builder Team: Phase 5a (2-3 days)
- **Team**: 3 builders (architecture, plugin, types)
- **Work**: Plugin protocol extraction + DI boundary
- **Files**: `scanner_plugins/protocol.py`, `scanner_core/di.py`, imports audit
- **Output**: Protocol definitions, import restrictions, test harnesses
- **Tier**: 2 (BALANCED, 1x) for architecture

### Initiative 6 Builder Team: Phase 5a (1-2 days)
- **Team**: 3 builders (type safety, protocol, ownership)
- **Work**: @overload verification + ownership consolidation
- **Files**: All files with @overload, marker_prefix enforcement, policy consolidation
- **Output**: 22 verified @overload, ownership audit report, type coverage metrics
- **Tier**: 1→2 (START Tier 1, escalate if complexity spike)

---

## Cost Estimate

| Initiative | Phase | Scout Cost | Builder Cost | Total |
|-----------|-------|-----------|-------------|-------|
| **Init 4** | 5a-5d | $0.003 | $0.012 | $0.015 |
| **Init 5** | 5a-5d | $0.003 | $0.018 | $0.021 |
| **Init 6** | 5a-5d | $0.003 | $0.010 | $0.013 |
| **TOTAL** | - | **$0.009** | **$0.040** | **$0.049** |

**Baseline**: ~$0.050 for Phase 5 scout + builder execution (all Tier 0-2)

---

## Timeline

**Scout Phase** (Today):
- 15:00 UTC: Dispatch 3 scouts (parallel)
- 16:00 UTC: All scouts report
- 16:15 UTC: Builder teams formed
- 16:30 UTC: Builders start Phase 5a work

**Builder Phase** (5-7 days):
- Day 1-3: Phase 5a (deterministic keys, protocols, type fixes)
- Day 2-4: Phase 5b (LRU, boundary enforcement, protocol impl)
- Day 4-6: Phase 5c (Layer audit, ownership consolidation, TypedDict audit)
- Day 7: Testing & validation

**Completion**: 2026-05-16 (EST)

---

## Go/No-Go Criteria

**Go** (Scout reports actionable):
- ✅ Clear implementation phases defined
- ✅ File list specific
- ✅ Before/after code patterns shown
- ✅ Builder team can start without questions

**No-Go** (Scout hits blockers):
- ❌ Architecture ambiguity remains
- ❌ Missing context (need Tier 1 investigation)
- ❌ Dependency on pending work

---

## Next Steps

1. **Dispatch 3 scouts NOW** (all Tier 0)
2. **Scout completion** (60 min) → Builder plan ready
3. **Form builder teams** (30 min) → Begin Phase 5a work
4. **Monitor progress** (daily) → Report daily at 18:00 UTC

