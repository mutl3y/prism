# Q2 Initiative 1: Phase 0 Kickoff — DI Container Decomposition

**Date**: May 9, 2026  
**Status**: ✅ READY FOR EXECUTION  
**Baseline**: 1166/1171 tests passing (99.2%), 0 regressions  
**Goal**: Kick off Task 1.1 (DI Container Analysis)  

---

## Phase 0: Discovery & Setup

### Current Baseline
```
Tests: 1166/1171 passing (99.2%)
Coverage: Baseline established
Lint: ruff + black clean
Type: 0 new mypy errors
```

### Q2 Initiative 1 Overview
**17 CRITICAL/HIGH findings** → Extract PluginResolver + ServiceLocator from DIContainer

**Problem**: DIContainer is 1000+ line god-object mixing:
- DI container logic
- Plugin resolver responsibilities  
- Service locator patterns
- Factory method orchestration

**Solution**: 3-class decomposition
1. **DIContainer** (slimmed to ~250 lines): Core DI binding logic
2. **PluginResolver** (new ~200 lines): Plugin registry + resolution
3. **ServiceLocator** (new ~150 lines): Service factory coordination

**Success Criteria**:
- DIContainer < 300 lines
- PluginResolver extracted (cleanly separated)
- ServiceLocator created (composable)
- 1150+ tests still passing
- Mypy clean (0 new errors)

---

## Task 1.1: DI Container Analysis (Week 1, Day 1-2)

### Scope
Audit current `src/prism/scanner_core/di.py` to:
1. Identify 15-20 god-object methods
2. Classify each method (DI, Plugin, Service, Factory)
3. Map data flow between methods
4. Identify extraction boundaries
5. Document current coupling

### Deliverables (by May 14)
- [ ] `di-container-audit.md` (findings)
- [ ] `di-container-architecture.yaml` (data flow diagram)
- [ ] `extraction-boundary-map.yaml` (which methods → which class)

### Owner
**Scout-DIArchitecture** (named scout)

### Checklist
- [ ] Audit complete (15-20 methods classified)
- [ ] Data flow documented
- [ ] Extraction boundaries clear
- [ ] Report ready for Task 1.2 handoff

---

## Execution Plan (Week 1-2)

### Week 1: Analysis & Design
- **Task 1.1** (Day 1-2): DI Container Analysis ← **START HERE**
- **Task 1.2** (Day 3-4): Extraction Boundary Design
- **Task 1.3** (Day 5): Service Locator Contract

### Week 2: Implementation
- **Task 1.4** (Day 1-2): Implement PluginResolver
- **Task 2.1** (Day 3): Refactor DIContainer
- **Task 2.2** (Day 4): Implement ServiceLocator
- **Task 2.3** (Day 5): Integration Testing

---

## Named Workers (Q2 Initiative 1)

### Scout Phase
- **Scout-DIArchitecture**: Audit and analysis (Task 1.1-1.3)

### Builder Phase
- **Builder-PluginResolver**: Implement PluginResolver
- **Builder-DISlim**: Refactor DIContainer
- **Builder-ServiceLocator**: Implement ServiceLocator
- **Builder-Integration**: Tie together + tests

---

## Validation Gates

**End of Task 1.1** (May 14):
- [ ] Audit document complete
- [ ] 15+ method classifications documented
- [ ] Extraction boundaries clear

**End of Week 1** (May 17):
- [ ] 3 scout artifacts ready
- [ ] Design approved
- [ ] Ready for builder phase

**End of Initiative 1** (May 26):
- [ ] 1150+ tests passing
- [ ] DIContainer < 300 lines
- [ ] PluginResolver + ServiceLocator extracted
- [ ] 0 mypy errors (new)

---

## Next Action (Now)

**DISPATCH**: Scout-DIArchitecture to begin Task 1.1 (DI Container Analysis)

Scout should:
1. Read `src/prism/scanner_core/di.py` (current ~1000 lines)
2. Identify 15-20 methods
3. Classify each (DI, Plugin, Service, Factory)
4. Document in `di-container-audit.md`
5. Return by May 14, EOD

---

**Status**: ✅ PHASE 0 READY — AWAITING SCOUT DISPATCH

**Estimated Completion**: May 14, 2026 (EOD)  
**Next Phase**: Design & Boundaries (Task 1.2, May 15)
