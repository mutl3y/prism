# G84 Findings Remediation: Mutl3y Execution Plan

**Objective**: Remediate all 261 g84 code review findings from scanner_core codebase  
**Timeline**: Single mutl3y cycle (Phase 1 → Phase 7)  
**Status**: ✅ READY TO EXECUTE  
**Plan Date**: 2026-05-09  

---

## Executive Summary

**261 Findings** discovered across scanner_core, grouped into **6 remediation waves**:

| Wave | Severity | Count | Domain | Approx. Effort |
|------|----------|-------|--------|---|
| **1** | CRITICAL | 33 | All domains | High (blocks everything) |
| **2** | HIGH | 59 | DI/Architecture | Medium-High |
| **3** | HIGH | 29 | Extraction/Parsing | Medium |
| **4** | HIGH | 1 | Output/Reporting | Low |
| **5** | HIGH+MEDIUM | 41 | Architecture/Cleanup | Medium |
| **6** | MEDIUM+LOW | 112 | General cleanup | Low-Medium |

**Sequential execution**: Wave 1 → Wave 2 → ... → Wave 6  
**Model selection**: Claude Haiku 4.5 (Tier 1, 0.33x) for mechanical fixes; escalate to Sonnet 4.5 for architectural

---

## Phase 1: Grading & Prioritization

**Status**: ✅ COMPLETE (findings already graded)

**Input**: g84-findings-consolidated.yaml (261 findings sorted by severity)

**Grading Results**:
- **CRITICAL (33)**: Must fix before any other work
- **HIGH (98)**: High impact, unblocks other issues
- **MEDIUM (99)**: Important but not blocking
- **LOW (31)**: Polish/cleanup

**Priority Enforcement**: Waves execute in order (CRITICAL → HIGH → MEDIUM → LOW)

---

## Phase 5: Implementation (Remediation Waves)

### Wave 1: CRITICAL Findings (33 issues)

**Duration**: ~4 hours  
**Builder Assignment**: Claude Sonnet 4.5 (1x) — CRITICAL severity requires reasoning  
**Model Justification**: g84 data shows 92% critical coverage for Sonnet vs 85% Haiku; CRITICAL findings need depth  

**Key Categories in Wave 1**:
- Type-safety violations (TypedDict casts, type erasure)
- Architecture god-objects (DI container, Scanner)
- Error handling gaps (bare exception catches)
- Circular dependencies

**Deliverables**:
- All 33 CRITICAL findings fixed
- Changes pushed to feature branch: `g84-wave1-critical-fixes`
- Full test suite passes

**Gate After Wave 1**: pytest + mypy green → proceed to Wave 2

---

### Wave 2: HIGH Findings - DI/Architecture (59 issues)

**Duration**: ~6 hours  
**Builder Assignment**: Claude Sonnet 4.5 (1x) — Architectural reasoning required  
**Model Justification**: DI refactoring needs deep analysis; 187 findings with 92% critical coverage  

**Key Categories**:
- DI container factory consolidation
- Ownership/responsibility cleanup
- Policy boundary fixes
- Type annotations

**Deliverables**:
- All 59 HIGH architecture findings fixed
- Changes pushed to feature branch: `g84-wave2-di-architecture`
- Zero mypy errors for affected modules

**Gate After Wave 2**: Full test suite + mypy → proceed to Wave 3

---

### Wave 3: HIGH Findings - Extraction/Parsing (29 issues)

**Duration**: ~3 hours  
**Builder Assignment**: Claude Haiku 4.5 (0.33x) — mostly mechanical fixes in extraction layer  
**Model Justification**: 198 findings, good for extraction pattern fixes; escalate if complex logic discovered  

**Key Categories**:
- Task line parsing accuracy
- Annotation handling
- Variable extraction normalization
- YAML/Jinja integration points

**Deliverables**:
- All 29 HIGH extraction findings fixed
- Changes pushed to feature branch: `g84-wave3-extraction`
- Extraction tests pass

**Gate After Wave 3**: Extraction-specific tests green → proceed to Wave 4

---

### Wave 4: HIGH Findings - Output/Reporting (1 issue)

**Duration**: ~30 min  
**Builder Assignment**: Claude Haiku 4.5 (0.33x) — single mechanical fix  

**Deliverables**:
- 1 HIGH output finding fixed
- Tests pass

**Gate After Wave 4**: → proceed to Wave 5

---

### Wave 5: MEDIUM Findings - Architecture (41 issues)

**Duration**: ~4 hours  
**Builder Assignment**: Claude Haiku 4.5 (0.33x) for mechanical; escalate 3-5 items to Sonnet 4.5  
**Model Justification**: Mix of cleanup + architectural decisions; use cost_priority="balanced" for complex items  

**Key Categories**:
- Event handling improvements
- Cache/performance fixes
- Code organization
- Documentation gaps

**Deliverables**:
- All 41 MEDIUM findings fixed
- Changes pushed to feature branch: `g84-wave5-medium-architecture`
- Architecture checklist complete

**Gate After Wave 5**: Architecture review + tests → proceed to Wave 6

---

### Wave 6: MEDIUM & LOW Findings - Cleanup (112 issues)

**Duration**: ~8 hours  
**Builder Assignment**: Claude Haiku 4.5 (0.33x) — mostly mechanical improvements  
**Model Justification**: 198 findings suitable for cleanup work; best ROI  

**Key Categories**:
- Logging/debugging improvements
- Comment cleanup
- Minor refactoring
- Edge case handling

**Deliverables**:
- All 112 MEDIUM+LOW findings fixed
- Changes pushed to feature branch: `g84-wave6-cleanup`
- Full test suite passes

**Gate After Wave 6**: All tests green → proceed to Phase 6

---

## Phase 6: Validation Gate

**Validation Checklist** (run in order):

```bash
# 1. Unit tests (all modules)
pytest -v --tb=short src/prism/tests/

# 2. Lint check
ruff check src/prism/

# 3. Code formatting
black --check src/prism/

# 4. Type checking
mypy src/prism > /tmp/mypy-final.out 2>&1

# 5. Edge case validation
pytest src/prism/tests/test_g84_remediation_verification.py -v
```

**Gate Criteria**:
- ✅ pytest: 100% pass (no new failures introduced)
- ✅ ruff: 0 violations
- ✅ black: formatting correct
- ✅ mypy: Zero regression from Wave 1 baseline

**If gate fails**: Rework failed wave, rerun gate

**If gate passes**: → Phase 7 Closure

---

## Phase 7: Closure & Proof

**Closure Checklist**:

✅ **All 261 findings remediated**:
- [ ] Verify all 261 issues closed/fixed in g84-findings-consolidated.yaml
- [ ] Grep for all GILF-* IDs in findings → verify each has fix commit

✅ **Code quality baseline established**:
- [ ] Pre-remediation mypy error count: [baseline]
- [ ] Post-remediation mypy error count: [final]
- [ ] Improvement: [%]

✅ **Test coverage verified**:
- [ ] All 261 findings have test cases for the fix
- [ ] 0 regression failures
- [ ] New tests pass

✅ **Documentation complete**:
- [ ] Summary document: "g84 Remediation Complete"
- [ ] Per-wave summaries showing before/after
- [ ] Known limitations (if any) documented

✅ **Learnings captured**:
- [ ] Which model (Haiku vs Sonnet) worked best for each wave
- [ ] Cost per finding remediated
- [ ] Lessons for future remediation cycles

---

## Model Selection Strategy (via model-router skill)

Each wave will call `query_model_router()` with:

```python
# Wave 1-2 (CRITICAL + HIGH Architecture)
routing = query_model_router(
    task_type="implementation",
    cost_priority="balanced",  # Reasoning required
    focus_area="architecture"
)
# Expected: Claude Sonnet 4.5 (1x, 187 findings, 92% critical)

# Wave 3-4 (HIGH Extraction + Wave 6 Cleanup)
routing = query_model_router(
    task_type="implementation",
    cost_priority="low",  # Mechanical fixes
    focus_area="extraction"
)
# Expected: Claude Haiku 4.5 (0.33x, 198 findings, 233/dollar)

# Wave 5 (Mixed)
routing = query_model_router(
    task_type="implementation",
    cost_priority="low"
)
# Expected: Haiku 4.5, escalate to Sonnet if needed
```

**Cost Estimate**:
- Waves 1-2: ~10 hrs × Sonnet (1x) = ~0.01-0.015
- Waves 3-6: ~15 hrs × Haiku (0.33x) = ~0.004-0.006
- **Total**: ~0.015-0.025 (cost-efficient for 261 findings fixed)

---

## Execution Timeline

| Phase | Duration | Owner | Status |
|-------|----------|-------|--------|
| Phase 0 | — | — | ✅ Skipped (findings pre-discovered) |
| Phase 1 | 0.5 hrs | Foreman | ✅ Complete |
| **Wave 1** | 4 hrs | Builder (Sonnet) | ⏳ Ready |
| **Wave 2** | 6 hrs | Builder (Sonnet) | ⏳ Ready |
| **Wave 3** | 3 hrs | Builder (Haiku) | ⏳ Ready |
| **Wave 4** | 0.5 hrs | Builder (Haiku) | ⏳ Ready |
| **Wave 5** | 4 hrs | Builder (Haiku+Sonnet) | ⏳ Ready |
| **Wave 6** | 8 hrs | Builder (Haiku) | ⏳ Ready |
| Phase 6 | 1 hr | Gatekeeper | ⏳ Ready |
| Phase 7 | 1 hr | Archivist | ⏳ Ready |
| **TOTAL** | ~28 hrs | — | — |

---

## Success Criteria

✅ **Functional**: All 261 findings remediated (0 outstanding)  
✅ **Quality**: pytest + mypy gates pass  
✅ **Cost-Efficient**: Used g84 empirical data to select models (Haiku for 70%, Sonnet for 30%)  
✅ **Learnable**: Captured wave-by-wave costs + findings per model for future cycles  
✅ **Traceable**: Every finding ID → commit SHA mapping preserved  

---

## Starting Execution

This plan is ready for autopilot execution via mutl3y-foreman skill.

**To start**: `mutl3y-foreman-skill` will:
1. Dispatch Phase 1 scouts (or skip, already graded)
2. Dispatch 6 builders sequentially (one wave per builder)
3. Run Phase 6 validation gates after each wave
4. Execute Phase 7 closure with proof
5. Archive all artifacts

**Monitoring**: Watch progress in phase artifacts at `/raid5/source/test/prism/docs/plan/g84-remediation-mutl3y-cycle-20260509/`

---

**Plan Author**: GitHub Copilot  
**Plan Status**: ✅ READY FOR EXECUTION  
**Next Action**: Dispatch Phase 5 Wave 1 builder
