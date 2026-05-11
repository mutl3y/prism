---
title: "Future Initiatives Roadmap"
date_created: "2026-05-11"
date_reviewed: "2026-05-11"
status: "active"
---

# Future Initiatives Roadmap

This document consolidates Q2 and Q3 initiatives that were deferred during post-g84 architecture refactoring. Each initiative represents a multi-week workstream with clear scope, dependencies, and implementation readiness.

## Rebaseline Summary

- Q2 Initiative 2 is narrowed to residual PolicyManager debt and deprecation cleanup.
- Q3 Initiative 4 remains the strongest next implementation candidate.
- Q3 Initiative 4 Phase 0 remains a reference artifact until revalidation is needed.
- Q3 Initiative 6 needs a fresh slice before any implementation work.
- Q3 Initiative 7 stays on the active execution path through [plugin-implementation-20260511](plugin-implementation-20260511).

---

## Q2 Initiative 2: PolicyManager Consolidation (Review Queue)

**Plan Folder**: [q2-initiative-2-policymanager-20260526/](future-initiatives/q2-initiative-2-policymanager-20260526/)
**Duration**: 2 weeks
**Dependencies**: Q2 Initiative 1 ✅ COMPLETE
**Status**: Backlog candidate under active review (not in current execution wave)

### Objective
Consolidate policy resolution from 4 scattered policy-holder modules into a single, centralized `PolicyManager` with explicit lifecycle management.

### Current State (Findings)
- **8 HIGH findings** around policy scattering, DI coupling, inconsistent caching, duplicated validation
- Policy resolution spread across: extract_defaults, variable_pipeline, task_vocabulary, feature_detector
- No centralized orchestration point
- DI container still involved in policy access (architectural debt)

### Key Artifacts
- [INITIATIVE_2_KICKOFF_PLAN.md](future-initiatives/q2-initiative-2-policymanager-20260526/INITIATIVE_2_KICKOFF_PLAN.md) — Phase breakdown + findings list
- Phase 0 scope: Scout 4 modules, analyze policy patterns, map dependencies

### Success Criteria
- ✅ Single PolicyManager owns all policy resolution
- ✅ Policy caching centralized + metrics captured
- ✅ DI container no longer involved in policy access
- ✅ Explicit policy lifecycle (load → validate → serve → retire)
- ✅ Mock/override policy injection working in tests
- ✅ All 8 findings resolved

---

## Q3 Initiative 4: Cache Optimization & Memory Bounding (Review Queue)

**Plan Folder**: [q3-initiative-4-cache-optimization/](future-initiatives/q3-initiative-4-cache-optimization/)
**Duration**: 6-8 days
**Dependencies**: None
**Status**: Backlog candidate under active review (not in current execution wave)

### Objective
Harden scan cache with memory bounding, performance metrics, and edge-case coverage.

### Current State
- **Deterministic cache keys** ✅ Working (SHA256, sorted JSON)
- **Custom object protocol** ✅ Done (`__cache_key__()`) but underdocumented
- **LRU eviction** ✅ Basic implementation
- **Memory bounding** ⚠️ Missing
- **Performance metrics** ⚠️ Partial (hit rate, eviction count needed)
- **Object size estimation** ⚠️ Missing

### Key Artifacts
- [phase-5-builder-plan.yaml](future-initiatives/q3-initiative-4-cache-optimization/phase-5-builder-plan.yaml) — Phased sub-tasks with clear test patterns

### Sub-Phases
1. **Phase 5a**: Deterministic cache keys verification (1-2 days)
2. **Phase 5b**: Memory bounding by bytes (2-3 days)
3. **Phase 5c**: Performance metrics & dashboard (1-2 days)
4. **Phase 5d**: Edge-case coverage & regression tests (1 day)

### Success Criteria
- ✅ Cache size bounded by configurable max bytes
- ✅ LRU eviction respects byte limit
- ✅ Hit rate / miss rate / eviction count metrics tracked
- ✅ Size estimation for: dicts, lists, strings, TypedDicts
- ✅ All 4 sub-phases deployed independently
- ✅ Full pytest suite passing (1306+ baseline)

---

## Q3 Initiative 6: Type Safety & Static Analysis (Review Queue)

**Plan Folder**: [q3-initiative-6-phase-5-scout/](future-initiatives/q3-initiative-6-phase-5-scout/)
**Duration**: 3-5 weeks
**Dependencies**: None
**Status**: Backlog candidate under active review (not in current execution wave)

### Objective
Improve TypedDict coverage, mypy compliance, and static analysis across scanner layers.

### Key Focus Areas
- TypedDict extensions for platform-specific error envelopes (partial — Phase 2 complete)
- Mypy strict mode enablement (per-module opt-in)
- Static analysis tooling (ruff, black, mypy) integration
- Type-safe plugin protocols

### Success Criteria
- ✅ 100% of owned modules passing mypy typecheck
- ✅ TypedDict used consistently for all data contracts
- ✅ Plugin protocols fully typed (no `Any` in critical paths)
- ✅ Static analysis CI/CD gates enforced

---

## Q3 Initiative 7: Multi-Platform Scanner Expansion (In Progress)

**Status**: Unblocked and actively progressing via [plugin-implementation-20260511](plugin-implementation-20260511)

### Objective
Implement Kubernetes and Terraform scanner plugins using unified error envelope and plugin-registry architecture.

### Implementation Plan

#### Phase 1: Kubernetes Scanner (Weeks 1-2)
- Mock K8s plugin with basic manifest parsing
- K8s error adapter implementation
- 10+ error codes (API errors, auth, manifest parsing, etc.)
- Basic E2E test with sample manifests

#### Phase 2: Terraform Scanner (Weeks 3-4)
- Mock Terraform plugin with HCL parsing
- Terraform error adapter implementation
- 10+ error codes (plan parse, provider auth, state errors)
- Basic E2E test with sample Terraform files

#### Phase 3: Plugin Parity & Cross-Platform Testing (Week 5)
- Parity tests across Ansible/K8s/Terraform error handling
- Unified provenance testing (task_file/line_number across platforms)
- Cross-platform collection mode tests

### Success Criteria
- ✅ K8s plugin functional (mock + real manifests)
- ✅ Terraform plugin functional (mock + real plans)
- ✅ Error codes and categories complete for both
- ✅ Unified error provenance working
- ✅ Collection mode supports all 3 platforms
- ✅ Full pytest suite passing (1369+ baseline from Phase 3)
- ✅ CI/CD gates green (pytest, ruff, black, mypy)

---

## Implementation Readiness Checklist

### Q2 Initiative 2 (PolicyManager)
- ✅ Findings documented (8 HIGH)
- ✅ Phase 0 discovery plan ready
- ✅ Scout scope clear (4 modules)
- ✅ No architectural blockers
- **Ready for**: Phase 0 scout dispatch (Tier 0, 2-3 hours)

### Q3 Initiative 4 (Cache Optimization)
- ✅ Current implementation partially mature
- ✅ 4 sub-phases clearly scoped
- ✅ Test patterns established
- ✅ No architectural ambiguity
- **Ready for**: Phase 5 builder dispatch (Tier 1, 6-8 days)

### Q3 Initiative 6 (Type Safety)
- ✅ Mypy baseline captured (96 errors, 93 non-owned)
- ✅ TypedDict strategy defined
- ✅ Static analysis tooling in place
- **Ready for**: Phase 0 scout for coverage analysis

### Q3 Initiative 7 (Multi-Platform Expansion)
- ✅ Error envelope foundation complete (Phases 1-3)
- ✅ Ansible adapter implemented and tested
- ✅ K8s/Terraform adapter stubs in place
- ✅ Plugin registry ready
- **Ready for**: Phase 0 scout for mock plugin design

---

## Dependencies & Sequencing

```
Q2 Initiative 1 (COMPLETE)
    ↓
Q2 Initiative 2 (PolicyManager) — Ready to start

Q3 Initiative 4 (Cache) — Can start anytime (no deps)

Q3 Initiative 6 (Type Safety) — Can run in parallel

Error Envelope (Phases 1-3) ✅ COMPLETE
    ↓
Q3 Initiative 7 (Multi-Platform Expansion) — Unblocked now
```

---

## Next Steps

**Immediate (As of 2026-05-11)**:
1. Continue active execution in [plugin-implementation-20260511](plugin-implementation-20260511) for Initiative 7 deliverables.
2. Re-baseline Q2 Initiative 2 and Q3 Initiative 4 target dates against current team capacity.
3. Keep Initiative 6 as backlog until ownership and strict-mode scope are explicitly scheduled.

**Short-term (After current active wave closes)**:
1. Decide next start candidate between Initiative 2 (PolicyManager) and Initiative 4 (Cache optimization).
2. Promote one backlog initiative from archive to an active top-level plan directory.
3. Update this roadmap with committed date windows once the promoted plan is approved.

Current review snapshot: [future-initiatives/REVIEW_20260511.md](future-initiatives/REVIEW_20260511.md)

**Unblocked** (pending prioritization):
- Q3 Initiative 6: Type safety & static analysis improvements

---

## Live Initiative References

All future initiative planning docs now live at: `/docs/plan/future-initiatives/`

- Q2 Initiative 2: `q2-initiative-2-policymanager-20260526/INITIATIVE_2_KICKOFF_PLAN.md`
- Q3 Initiative 4: `q3-initiative-4-cache-optimization/phase-5-builder-plan.yaml`
- Q3 Initiative 6: `q3-initiative-6-phase-5-scout/` (scout reports)
