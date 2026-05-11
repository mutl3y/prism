---
date: 2026-05-11
purpose: Consolidate 22 plan directories into actionable structure
estimated_effort: 2-3 hours
status: completed
date_reviewed: 2026-05-11
---

# docs/plan Housekeeping Proposal

## Execution Status (As Of 2026-05-11)

- Phase 1 archive move: complete
- Phase 3 future-initiative archive move: complete
- Phase 4 architecture-review archive move: complete
- Consolidated surfaces created: [mutl3y-lessons-g74-g84-consolidated.md](mutl3y-lessons-g74-g84-consolidated.md) and [FUTURE_INITIATIVES.md](FUTURE_INITIATIVES.md)

This file is retained as the proposal and execution record for the 2026-05-11 housekeeping wave.

## Current State: 22 Plan Directories (Fragmented)

Historical snapshot at proposal time (pre-execution).

```
docs/plan/
├── archive/                                      # Already archived
├── .mutl3y-lessons/                             # Mutl3y workflow lessons
├── mutl3y-review-20260505-g74/                  # OLD: g74 cycle (superseded)
├── mutl3y-review-20260505-g75/                  # OLD: g75 cycle (superseded)
├── mutl3y-review-20260507-g76/                  # OLD: g76 cycle (superseded)
├── mutl3y-review-20260507-g77/                  # OLD: g77 cycle (superseded)
├── mutl3y-review-20260507-g78/                  # OLD: g78 cycle (superseded)
├── mutl3y-review-20260507-g79/                  # OLD: g79 cycle (superseded)
├── mutl3y-review-20260507-godmode/              # OLD: God Mode cycle (superseded)
├── mutl3y-review-20260508-g82-test/             # OLD: g82 test cycle (superseded)
├── mutl3y-review-wave2-hotpath-20260507/        # OLD: Wave 2 hotpath (superseded)
├── mutl3y-cluster-autopilot-20260507/           # OLD: Cluster autopilot test (superseded)
├── mutl3y-structure-validation-20260506-2342/   # OLD: Structure validation (superseded)
├── g84-10-model-gilfoyle-comparison-20260508/   # OLD: g84 discovery phase (superseded by g84 complete cycle)
├── di-container-refactoring-wave-20260508/      # OLD: DI container work (merged into g84)
├── g82-tier-enforcement-test-20260508/          # OLD: Tier enforcement test
├── architecture-extensibility-review-20260421/  # OLD: Extensibility review (findings integrated)
├── q2-initiative-2-policymanager-20260526/      # FUTURE: Q2 work (not started)
├── q3-initiative-4-cache-optimization/          # FUTURE: Q3 work (not started)
├── q3-initiative-4-phase0-20260509/             # FUTURE: Q3 Phase 0 (not started)
├── q3-initiative-6-phase-5-scout/               # FUTURE: Q3 Phase 5 (not started)
├── g84-remediation-mutl3y-cycle-20260509/       # ✅ CURRENT: g84 complete cycle (DONE)
└── post-g84-arch-refactor-20260511/             # ✅ ACTIVE: Error envelope work (IN PROGRESS)
```

**Problem**: 13 obsolete plan directories (g74-g82 cycles, old discovery phases) + 4 future stubs

---

## Housekeeping Strategy: Archive + Consolidate

### Phase 1: Archive Old Mutl3y Cycles (Move to archive/)

**Candidates for archiving** (13 directories):
- `mutl3y-review-20260505-g74/`
- `mutl3y-review-20260505-g75/`
- `mutl3y-review-20260507-g76/`
- `mutl3y-review-20260507-g77/`
- `mutl3y-review-20260507-g78/`
- `mutl3y-review-20260507-g79/`
- `mutl3y-review-20260507-godmode/`
- `mutl3y-review-20260508-g82-test/`
- `mutl3y-review-wave2-hotpath-20260507/`
- `mutl3y-cluster-autopilot-20260507/`
- `mutl3y-structure-validation-20260506-2342/`
- `g84-10-model-gilfoyle-comparison-20260508/`
- `di-container-refactoring-wave-20260508/`

**Rationale**: All superseded by `g84-remediation-mutl3y-cycle-20260509/` (the complete consolidated cycle)

**Action**:
```bash
cd /raid5/source/test/prism/docs/plan
mkdir -p archive/mutl3y-cycles-g74-g84
mv mutl3y-review-20260505-g74/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-20260505-g75/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-20260507-g76/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-20260507-g77/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-20260507-g78/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-20260507-g79/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-20260507-godmode/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-20260508-g82-test/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-review-wave2-hotpath-20260507/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-cluster-autopilot-20260507/ archive/mutl3y-cycles-g74-g84/
mv mutl3y-structure-validation-20260506-2342/ archive/mutl3y-cycles-g74-g84/
mv g84-10-model-gilfoyle-comparison-20260508/ archive/mutl3y-cycles-g74-g84/
mv di-container-refactoring-wave-20260508/ archive/mutl3y-cycles-g74-g84/
```

---

### Phase 2: Create Consolidated Learning Summary

**Purpose**: Extract key lessons from 13 archived cycles into single reference document

**Tasks**:
1. Read findings from each archived cycle
2. Extract reusable patterns (tier enforcement, delegation discipline, route failures)
3. Consolidate into `docs/plan/mutl3y-lessons-g74-g84-consolidated.md`

**Structure**:
```markdown
# Mutl3y Lessons Learned: Cycles g74-g84

## Tier Enforcement Patterns
(from g82, g74-g79)

## Delegation Discipline
(from g78, g79, godmode)

## Route Failure Recovery
(from g82, g84)

## Scout-First Discovery
(from g84 post-cycle analysis)

## Model Usage Ledger Insights
(from g82, g84 ledgers)
```

---

### Phase 3: Consolidate Q2/Q3 Future Work Stubs

Note: The status labels in this section are proposal-time values captured on 2026-05-11. Current initiative status lives in [FUTURE_INITIATIVES.md](FUTURE_INITIATIVES.md).

**Current State**:
- `q2-initiative-2-policymanager-20260526/` (not started)
- `q3-initiative-4-cache-optimization/` (not started)
- `q3-initiative-4-phase0-20260509/` (not started)
- `q3-initiative-6-phase-5-scout/` (not started)

**Problem**: Separate directories for future work creates discovery burden

**Action**: Create `docs/plan/FUTURE_INITIATIVES.md` roadmap

```markdown
# Future Initiatives Roadmap

## Q2 2026

### Initiative 2: PolicyManager Consolidation
**Status**: Not started (deferred from g84)  
**Scope**: Consolidate PolicyManager + DIContainer policy resolution overlap  
**Effort**: 2-3 days  
**Plan**: docs/plan/q2-initiative-2-policymanager-20260526/

## Q3 2026

### Initiative 4: Cache Optimization
**Status**: Not started  
**Scope**: Optimize scan cache for high-volume collection scans  
**Effort**: 1 week  
**Plans**:
- docs/plan/q3-initiative-4-cache-optimization/
- docs/plan/q3-initiative-4-phase0-20260509/

### Initiative 6: Type Safety Improvements
**Status**: Not started (gem-reviewer recommendation)  
**Scope**: Reduce `Any` usage, strengthen Protocol contracts  
**Effort**: 1-2 weeks  
**Plan**: docs/plan/q3-initiative-6-phase-5-scout/
```

Then move directories to archive:
```bash
mkdir -p archive/future-initiatives
mv q2-initiative-2-policymanager-20260526/ archive/future-initiatives/
mv q3-initiative-4-cache-optimization/ archive/future-initiatives/
mv q3-initiative-4-phase0-20260509/ archive/future-initiatives/
mv q3-initiative-6-phase-5-scout/ archive/future-initiatives/
```

---

### Phase 4: Archive Old Architecture Reviews

**Candidates**:
- `architecture-extensibility-review-20260421/` (findings already integrated into g84)
- `g82-tier-enforcement-test-20260508/` (tier enforcement now in memory notes)

**Action**:
```bash
mkdir -p archive/architecture-reviews
mv architecture-extensibility-review-20260421/ archive/architecture-reviews/
mv g82-tier-enforcement-test-20260508/ archive/architecture-reviews/
```

---

## Target State (After Housekeeping)

```
docs/plan/
├── archive/
│   ├── mutl3y-cycles-g74-g84/                   # 13 old cycles
│   ├── future-initiatives/                      # 4 Q2/Q3 stubs
│   └── architecture-reviews/                    # 2 old reviews
├── .mutl3y-lessons/                             # Workflow lessons (keep)
├── g84-remediation-mutl3y-cycle-20260509/       # ✅ COMPLETE: g84 full cycle
├── post-g84-arch-refactor-20260511/             # ✅ ACTIVE: Error envelope work
├── mutl3y-lessons-g74-g84-consolidated.md       # NEW: Consolidated lessons
└── FUTURE_INITIATIVES.md                        # NEW: Roadmap for Q2/Q3 work
```

**Reduction**: 22 directories → 4 active + 1 archive folder

---

## Execution Commands

```bash
cd /raid5/source/test/prism/docs/plan

# Phase 1: Archive old Mutl3y cycles
mkdir -p archive/mutl3y-cycles-g74-g84
for dir in mutl3y-review-20260505-g74 mutl3y-review-20260505-g75 \
           mutl3y-review-20260507-g76 mutl3y-review-20260507-g77 \
           mutl3y-review-20260507-g78 mutl3y-review-20260507-g79 \
           mutl3y-review-20260507-godmode mutl3y-review-20260508-g82-test \
           mutl3y-review-wave2-hotpath-20260507 mutl3y-cluster-autopilot-20260507 \
           mutl3y-structure-validation-20260506-2342 \
           g84-10-model-gilfoyle-comparison-20260508 \
           di-container-refactoring-wave-20260508; do
  mv "$dir" archive/mutl3y-cycles-g74-g84/
done

# Phase 3: Archive future initiative stubs
mkdir -p archive/future-initiatives
for dir in q2-initiative-2-policymanager-20260526 \
           q3-initiative-4-cache-optimization \
           q3-initiative-4-phase0-20260509 \
           q3-initiative-6-phase-5-scout; do
  mv "$dir" archive/future-initiatives/
done

# Phase 4: Archive old architecture reviews
mkdir -p archive/architecture-reviews
mv architecture-extensibility-review-20260421 archive/architecture-reviews/
mv g82-tier-enforcement-test-20260508 archive/architecture-reviews/
```

---

## Benefits

1. **Clarity**: 4 active directories instead of 22
2. **Discovery**: Easy to find current work (g84 complete, error envelope active)
3. **Learning**: Consolidated lessons document instead of scattered findings
4. **Roadmap**: Single FUTURE_INITIATIVES.md for Q2/Q3 planning
5. **Archive Integrity**: Old cycles preserved but out of daily view

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Losing old cycle findings | Keep archive/, create consolidated summary |
| Breaking references in AGENTS.md | Update AGENTS.md "Notable Findings" with archive paths |
| Future work stubs inaccessible | Create FUTURE_INITIATIVES.md roadmap with archive links |

---

## Next Steps

1. ✅ Execute archiving commands (Phase 1, 3, 4)
2. Create `mutl3y-lessons-g74-g84-consolidated.md` (Phase 2)
3. Create `FUTURE_INITIATIVES.md` roadmap (Phase 3)
4. Update `AGENTS.md` with archive references
5. Update post-g84 plan with clean directory structure

**Estimated Effort**: 2-3 hours (mostly automated with bash commands)

---

**Prepared By**: Tier 2 Foreman  
**Purpose**: Housekeeping for docs/plan directory structure  
**Status**: Ready for execution
