# Q2 Initiative 2 — PolicyManager Consolidation

**Kickoff Date**: May 26, 2026  
**Duration**: 2 weeks (May 26 - Jun 9)  
**Scope**: Consolidate policy ownership from 4 policy-holder modules into single PolicyManager  
**Dependencies**: Q2 Initiative 1 ✅ COMPLETE  

---

## Findings Overview (8 HIGH findings)

| ID | Finding | Severity | Category | Status |
| ---|---------|----------|----------|--------|
| F-01 | Policy resolution scattered across 4 modules | HIGH | Ownership | Not Started |
| F-02 | No centralized policy orchestration point | HIGH | Design | Not Started |
| F-03 | Policy caching inconsistent across modules | HIGH | Coordination | Not Started |
| F-04 | DI container still involved in policy access | HIGH | Coupling | Not Started |
| F-05 | Policy validation duplicated in multiple places | HIGH | Duplication | Not Started |
| F-06 | No explicit policy lifecycle management | HIGH | Reliability | Not Started |
| F-07 | Mock/override policy injection unclear | HIGH | Testability | Not Started |
| F-08 | Policy change propagation non-deterministic | HIGH | Performance | Not Started |

---

## Phase Breakdown

### Phase 0: Discovery & Analysis (May 26-27)

**Scouts**:
- Scout-PolicyAudit: Analyze 4 policy-holder modules (extract_defaults, variable_pipeline, task_vocabulary, feature_detector)
- Scout-PolicyBoundary: Design consolidation boundaries and PolicyManager interface
- Scout-PolicyProtocol: Define policy resolution protocol and caching strategy

**Deliverables**: 6 design artifacts, blocking issues identified

### Phase 1: Design Specification (May 28-29)

**Scouts**:
- Scout-PolicyCoordination: Map policy access patterns across scanner_core
- Scout-PolicyCaching: Design cache invalidation and coordination

**Deliverables**: Cache coordination spec, integration test strategy

### Phase 2: Implementation (May 30 - Jun 2)

**Wave 1 (May 30-31)**: Extract PolicyManager class
- Builder-PolicyExtraction: Extract policy resolution from 4 modules

**Wave 2 (Jun 1-2)**: Implement policy factories
- Builder-PolicyFactories: Implement 8+ policy factory methods
- Builder-PolicyCaching: Implement cache coordination

### Phase 3: Integration & Validation (Jun 3-6)

**Validation**:
- Builder-PolicyIntegration: Integration tests for all policy access patterns
- Gatekeeper: Run full test suite, verify 0 regressions

### Phase 4: Closure (Jun 7-9)

**Review & Sign-Off**:
- Code review of PolicyManager
- Documentation finalization
- Artifact archival

---

## Prerequisites for Success

✅ **Q2 Initiative 1 Complete**: DIContainer now focused on DI only
✅ **PluginResolver Available**: For policy resolution queries
✅ **ServiceLocator Available**: For policy caching + invalidation
✅ **Test Baseline**: 1166 tests passing, integration testing infrastructure ready

---

## Expected Outcomes

- **PolicyManager class**: 200-300 lines, 8+ factory methods
- **Test coverage**: 95%+, 25+ integration tests
- **Findings resolved**: 8/8 HIGH findings
- **Backward compatibility**: 100% verified
- **Code quality**: Ruff clean, mypy clean, lint passing

---

## Recommended Approach

1. **Start with Scout phase**: Complete all 4 scout tasks in parallel
2. **Design-first**: Finalize PolicyManager interface before any implementation
3. **Parallel waves**: Execute Wave 1 & 2 builders in parallel (disjoint scopes)
4. **Integration-heavy**: 25+ tests covering all policy access patterns
5. **Gate validation**: 8 gates (same as Initiative 1)

---

## Cost Optimization Strategy

**Tier Strategy** (from mutl3y-tier-strategy.md):
- Phase 0-1 Scouts: **Tier 0 (FREE)** — GPT-4o/4.1
- Phase 2 Builders: **Tier 0 (FREE)** → **Tier 2 (1x)** if DI coupling issues
- Phase 3 Integration: **Tier 0 (FREE)**
- Gilfoyle Review: **Tier 2 (1x)** only if findings incomplete

**Expected Cost**: ~0.08x baseline (85%+ savings)

---

## Parallel with Q2 Initiative 3

**Q2 Initiative 3** (Marker-Prefix Boundary Enforcement) can begin Week 2 planning (Jun 2-3) in parallel with Initiative 2 Wave 2-3 execution.

---

## Success Criteria

| Criterion | Measure | Target |
|-----------|---------|--------|
| Findings Resolved | F-01 through F-08 | 8/8 (100%) |
| Code Coverage | New PolicyManager | 95%+ |
| Tests Passing | Total suite | 1166+ |
| New Failures | From consolidation | 0 |
| Backward Compat | Old code continues | 100% |
| Integration Tests | New coverage | 25+ |
| Type Safety | Mypy errors (new) | 0 |
| Lint Status | Ruff/Black | Clean |

---

## Timeline & Milestones

- **May 26 (Day 1)**: Scout phase kickoff
- **May 28 (Day 3)**: Scout phase complete, design finalized
- **May 30 (Day 5)**: Wave 1 builders start
- **Jun 1 (Day 7)**: Wave 2 builders start
- **Jun 3 (Day 9)**: Integration testing begins
- **Jun 7 (Day 13)**: All testing complete, gates pass
- **Jun 9 (Day 15)**: Closure certificate complete

---

## Ready to Proceed

✅ Initiative 1 complete  
✅ Execution trace updated  
✅ Test baseline verified (1166 passing)  
✅ Next phase planned and documented  

**Status**: READY FOR INITIATIVE 2 KICKOFF ON MAY 26

---

**Prepared By**: Mutl3y-Foreman  
**Date**: May 9, 2026, 19:35 UTC  
**Plan ID**: q2-initiative-2-policymanager-20260526
