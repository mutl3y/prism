# Q2 Initiative 1 — Phase 0 Execution Tracker

**Date**: May 10, 2026  
**Phase**: 0 (Discovery & Setup)  
**Status**: 🚀 LAUNCHING NOW  

---

## Tier Strategy

| Phase | Task | Tier | Reason | Cost |
| --- | --- | --- | --- | --- |
| 0 | Scope review + DI Container audit | **Tier 0 (FREE)** | Discovery/design work | $0.001 |
| 1 | Interface design + extraction planning | **Tier 0 (FREE)** | Design work | $0.001 |
| 2-Phase A | PluginResolver extraction + tests | **Tier 2 (BALANCED 1x)** | Architectural refactoring, god-object decomposition | $0.030 |
| 2-Phase B | ServiceLocator extraction + tests | **Tier 2 (BALANCED 1x)** | Complex factory patterns, composition | $0.020 |
| 2-Phase C | Integration & testing | **Tier 0 (FREE)** | Validation, test runs | $0.001 |
| **Total** | 17 findings resolved | — | 2-week timeline | **$0.053** |

**Budget Impact**: $0.053 of $0.080 reserve (33% utilization)  
**Escalation Justification**:
- Tasks 2-A & 2-B involve architecture-sensitive DI refactoring (god-object decomposition)
- Tier 2 required for complex factory pattern analysis and correct extraction boundaries
- Tier 0 insufficient for system-wide DI reasoning

---

## Phase 0 Dispatch: DI Container Discovery

### Team Composition
1. **Scout-ArchitectureReview** (Tier 0, lead discovery)
   - Review DIContainer (1000+ lines)
   - Identify 17 factory/plugin methods
   - Map dependencies and call sites
   
2. **Scout-CodebasePatterns** (Tier 0, parallel)
   - Audit factory patterns in DIContainer
   - Identify extraction boundaries
   - Document coupling points

3. **Scout-CallSiteMapping** (Tier 0, parallel)
   - Find all call sites to DIContainer methods
   - Map scanner_core, scanner_extract, scanner_plugins usage
   - Identify refactoring blast radius

### Deliverables (by May 12)
- [ ] `di-container-audit.md` (17 methods classified, dependencies mapped)
- [ ] `extraction-boundaries.yaml` (method → class allocation)
- [ ] `call-site-analysis.md` (refactoring impact assessment)

### Success Criteria
- All 17 methods identified and classified
- Data flow between methods documented
- Extraction boundaries clear and non-overlapping
- Call site analysis complete (zero surprises)

---

## Next Phases (Tier 2, May 13+)

### Phase 1: Design (Tier 2)
- Task 1.2: PluginResolver interface design
- Task 1.3: ServiceLocator interface design

### Phase 2: Implementation (Tier 2)  
- Task 2.1: Extract PluginResolver (300+ lines)
- Task 2.2: Extract ServiceLocator (300+ lines)
- Task 2.3: Slim DIContainer + facade
- Task 2.4: Full integration & testing

### Gate Criteria
- 1150+ tests passing (no regressions)
- 0 new mypy errors
- DIContainer < 300 lines (from 1000+)

---

**Status**: Ready to dispatch Phase 0 scouts on Tier 0 (FREE tier)
