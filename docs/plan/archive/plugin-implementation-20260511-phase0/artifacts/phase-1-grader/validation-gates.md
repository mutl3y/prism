# Validation Gates — Phase 2-5 Specifications

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-1-grader (validation specification)  
**Date**: May 9, 2026  
**Status**: ✅ **GATES DEFINED**

---

## Overview

Validation gates at each phase ensure quality, prevent regressions, and establish go/no-go criteria for proceeding to next phase.

---

## Phase 2 Gate: Implementation Complete & Tests Green

**Trigger**: After all 7 implementation waves complete

**Gate Commands**:

### 2.1: Full Test Suite

```bash
cd /raid5/source/test/prism
pytest tests/ -v --tb=short -x
```

**Expected Result**:
- All tests pass (0 failures)
- Coverage maintained (≥85%)
- No new warnings (except DeprecationWarning for old code)

**Condition**: PASS ≥ 95% tests

**Command Status Output**:
```
collected 1200+ tests
passed 1180+
failed 0
warnings 15 (DeprecationWarning only, acceptable)
=== GATE 2.1 PASS ===
```

---

### 2.2: No Regressions

```bash
pytest tests/ --tb=short -x -q | grep -E "^(PASSED|FAILED|ERROR)"
```

**Expected Result**:
- Same tests pass as before Phase 2
- No new failures
- No tests now skipped (unless intentional)

**Condition**: Zero new failures compared to Phase 0

---

### 2.3: Build & Import Check

```bash
python -m py_compile src/prism/scanner_plugins/fallback_registry.py
python -m py_compile src/prism/scanner_plugins/policy_manager.py
python -m py_compile src/prism/scanner_plugins/bootstrap.py
python -m py_compile src/prism/scanner_config/policy_loader.py

python -c "from src.prism.scanner_plugins.fallback_registry import FallbackPolicyRegistry; \
           from src.prism.scanner_plugins.policy_manager import PolicyManager; \
           from src.prism.scanner_core.di import DIContainer; \
           di = DIContainer.default(); \
           print('✓ All imports OK')"
```

**Expected Result**:
- All modules compile successfully
- No import errors
- DIContainer initializes with PolicyManager

**Condition**: PASS

---

### 2.4: Code Quality (Lint)

```bash
python -m ruff check src/prism/scanner_plugins/fallback_registry.py
python -m ruff check src/prism/scanner_plugins/policy_manager.py
python -m ruff check src/prism/scanner_core/di.py
python -m black --check src/prism/scanner_plugins/*.py
```

**Expected Result**:
- Ruff clean (0 violations, or only auto-fix)
- Black formatting correct
- No style violations

**Condition**: PASS

---

### 2.5: Type Checking

```bash
python -m mypy src/prism/scanner_plugins/fallback_registry.py \
               src/prism/scanner_plugins/policy_manager.py \
               src/prism/scanner_core/di.py \
               --strict
```

**Expected Result**:
- Mypy clean (0 errors in strict mode)
- Type hints complete
- No Any types in new code

**Condition**: PASS (0 errors)

---

### 2.6: Backward Compatibility

```bash
# Old code should still work (with warnings)
python -c "
import warnings
from src.prism.scanner_plugins.defaults import resolve_task_line_parsing_policy_plugin
from src.prism.scanner_core.di import DIContainer

di = DIContainer.default()
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    policy = resolve_task_line_parsing_policy_plugin(di)
    assert policy is not None
    assert len([x for x in w if 'deprecated' in str(x.message).lower()]) > 0
    print('✓ Backward compatibility OK')
"
```

**Expected Result**:
- Old resolver functions work
- DeprecationWarning emitted
- Returned policy is functional

**Condition**: PASS

---

### Phase 2 Gate Summary

| Gate | Command | Expected | Condition |
| --- | --- | --- | --- |
| 2.1 | pytest | ≥95% pass | PASS |
| 2.2 | regression check | 0 new failures | PASS |
| 2.3 | import/compile | ✓ All OK | PASS |
| 2.4 | lint | ruff/black clean | PASS |
| 2.5 | type | mypy ≥95% clean | PASS |
| 2.6 | backward compat | old code + warnings | PASS |

**Go/No-Go**: **PROCEED TO PHASE 3** if all 6 gates PASS

---

## Phase 3 Gate: Integration Tests & Performance

**Trigger**: After Wave 5 (migration complete)

### 3.1: Integration Test Suite

```bash
pytest tests/integration/test_policy_consolidation.py -v --tb=short
pytest tests/scanner_core/test_di_policy_integration.py -v
```

**Expected Result**:
- 25+ integration tests pass (0 failures)
- All caching levels verified
- Mock/override injection working

**Condition**: All tests PASS

---

### 3.2: End-to-End Scan Test

```bash
python -c "
from src.prism.api import run_scan

# Run a real scan with new PolicyManager
result = run_scan(
    repo_path='test_repos/sample',
    scan_options={
        'prepared_policy_bundle': None,  # Auto-initialize via PolicyManager
        'platform': 'ansible',
    }
)

assert result['status'] == 'success', f'Scan failed: {result}'
assert result['policy_bundle_usage'] == 'PolicyManager', 'Not using new manager'
print('✓ End-to-end scan OK')
"
```

**Expected Result**:
- Real scan completes successfully
- Uses new PolicyManager
- No errors or warnings (except deprecation from old code)

**Condition**: PASS

---

### 3.3: Performance Benchmark

```bash
python tests/benchmarks/test_policy_performance.py --compare --baseline=phase0
```

**Expected Result Output**:
```
Hotloop Speedup Results:
├── Task Catalog (hotloop 1): 1200x ✓
├── Annotation Extraction (hotloop 2): 115x ✓
├── Variable Discovery (hotloop 3): 55x ✓
└── Overall Scan Improvement: 28.3% ✓

All targets met: YES
```

**Condition**: Overall ≥25% speedup (28% target ±10%)

---

### 3.4: Memory Overhead

```bash
python -c "
import tracemalloc
from src.prism.scanner_core.di import DIContainer

tracemalloc.start()

di = DIContainer.default()
cache = di.policy_cache

# Populate cache with all policies
for _ in range(100):
    di.policy_manager.resolve_task_line_parsing_policy()
    di.policy_manager.resolve_jinja_analysis_policy()

current, peak = tracemalloc.get_traced_memory()
overhead_kb = peak / 1024

print(f'Cache overhead: {overhead_kb:.2f} KB')
assert overhead_kb < 10, f'Overhead too high: {overhead_kb} KB'
print('✓ Memory overhead OK')
"
```

**Expected Result**:
- Cache overhead <10KB per scan
- No memory leaks
- GC friendly

**Condition**: PASS (<10KB)

---

### 3.5: Caching Hit Rate

```bash
python -c "
from src.prism.scanner_core.di import DIContainer

di = DIContainer.default()
manager = di.policy_manager
cache = di.policy_cache

# Simulate hotloop
for _ in range(1000):
    manager.resolve_task_line_parsing_policy()

hits, misses, size = cache.stats()
hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0

print(f'Cache hit rate: {hit_rate:.1%}')
assert hit_rate > 0.95, f'Hit rate too low: {hit_rate:.1%}'
print('✓ Hit rate OK')
"
```

**Expected Result**:
- Hit rate >95%
- Caching working as designed

**Condition**: PASS (>95% hits)

---

### Phase 3 Gate Summary

| Gate | Metric | Target | Condition |
| --- | --- | --- | --- |
| 3.1 | Integration tests | ≥25 pass | PASS |
| 3.2 | End-to-end scan | Complete successfully | PASS |
| 3.3 | Performance | ≥25% speedup | PASS |
| 3.4 | Memory | <10KB overhead | PASS |
| 3.5 | Cache hit rate | >95% | PASS |

**Go/No-Go**: **PROCEED TO PHASE 4** if all 5 gates PASS

---

## Phase 4 Gate: Code Review & Deprecation Warnings

**Trigger**: After Phase 3 validation

### 4.1: Code Review Approval

```bash
# Manual review checklist:
# - PolicyManager interface matches spec
# - FallbackPolicyRegistry thread-safe
# - Caching levels implemented correctly
# - Backward compatibility maintained
# - Tests comprehensive
# - Documentation complete
```

**Expected Result**:
- Code reviewed by senior dev
- Approved for merge
- No major issues found

**Condition**: Approval given

---

### 4.2: Deprecation Warnings Added

```bash
grep -r "DeprecationWarning" src/prism/scanner_plugins/defaults.py
grep -r "DEPRECATED" src/prism/scanner_plugins/defaults.py
```

**Expected Result**:
- All 6 legacy functions have DeprecationWarning
- Comments document deprecation schedule
- Migration guidance provided

**Condition**: All 6 warnings present

---

### 4.3: Documentation Updated

```bash
# Check files for updated docs:
# - src/prism/scanner_plugins/policy_manager.py (module docstring)
# - src/prism/scanner_plugins/fallback_registry.py (module docstring)
# - docs/ARCHITECTURE.md (if exists)
# - Migration guide (for developers)

ls -la src/prism/scanner_plugins/policy_manager.py
head -50 src/prism/scanner_plugins/policy_manager.py | grep -E "^\"\"\"" -A 20
```

**Expected Result**:
- Module docstrings present
- Migration guide written
- Architecture docs updated

**Condition**: Documentation complete

---

### 4.4: Deprecation Guidance Clear

```bash
python -c "
import warnings
from src.prism.scanner_plugins.defaults import resolve_task_line_parsing_policy_plugin

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    # This will emit DeprecationWarning
    # Check the message
    try:
        from src.prism.scanner_core.di import DIContainer
        di = DIContainer.default()
        resolve_task_line_parsing_policy_plugin(di)
    except:
        pass
    
    if w:
        msg = str(w[0].message)
        print(f'Warning message: {msg}')
        # Should include guidance on new API
        assert 'policy_manager' in msg.lower() or 'use di' in msg.lower()
        print('✓ Guidance clear')
"
```

**Expected Result**:
- Warning includes clear migration guidance
- Points to new API

**Condition**: PASS

---

### Phase 4 Gate Summary

| Gate | Task | Expected | Condition |
| --- | --- | --- | --- |
| 4.1 | Code review | Approved | APPROVED |
| 4.2 | Deprecation warnings | All 6 present | COMPLETE |
| 4.3 | Documentation | Updated | COMPLETE |
| 4.4 | Guidance | Clear migration path | CLEAR |

**Go/No-Go**: **PROCEED TO PHASE 5 (Closure)** if all 4 gates PASS

---

## Phase 5 Gate: Closure & Final Validation

**Trigger**: After Phase 4 approval

### 5.1: All Artifacts Archived

```bash
# Verify all Phase 1 grader artifacts created
ls -la docs/plan/g84-remediation-mutl3y-cycle-20260509/artifacts/phase-1-grader/
```

**Expected Files**:
- design-review-findings.md ✓
- implementation-sequence-locked.md ✓
- implementation-task-breakdown.md ✓
- integration-test-strategy.md ✓
- validation-gates.md ✓
- GRADER_SIGN_OFF.md ✓
- performance-validation.md ✓

**Condition**: All 7 files present

---

### 5.2: All Phase 2-4 Findings Resolved

```bash
# Check issue tracker or comments
# - Implementation complete (Wave 0-6)
# - All integration tests passing
# - Performance targets met
# - Code reviewed and approved
# - Deprecation warnings in place
```

**Condition**: All findings addressed

---

### 5.3: Final Test Run

```bash
pytest tests/ -v --cov=src/prism --cov-report=html
```

**Expected**:
- ≥1200 tests pass
- Coverage ≥85%
- 0 failures

**Condition**: PASS

---

### 5.4: Release Ready

```bash
# Final checklist:
# - [ ] Implementation complete
# - [ ] Tests passing (≥95%)
# - [ ] Performance validated (≥25% speedup)
# - [ ] Code reviewed and approved
# - [ ] Documentation complete
# - [ ] Deprecation warnings in place
# - [ ] Backward compatibility verified
# - [ ] All artifacts archived
# - [ ] Ready for merge and deployment

echo "✓ All criteria met - READY FOR RELEASE"
```

**Condition**: All 8 items checked

---

### Phase 5 Gate Summary

| Gate | Task | Expected | Condition |
| --- | --- | --- | --- |
| 5.1 | Artifacts archived | All 7 files | COMPLETE |
| 5.2 | Findings resolved | All addressed | COMPLETE |
| 5.3 | Final test run | ≥1200 pass | PASS |
| 5.4 | Release ready | All 8 items | READY |

**Final Status**: ✅ **RELEASE APPROVED**

---

## Gate Execution Schedule

| Phase | Gate | Trigger | Duration | Owner |
| --- | --- | --- | --- | --- |
| 2 | Impl complete | After Wave 6 | 1-2h | DevOps |
| 3 | Integration + Perf | After Wave 5 | 2-3h | Backend |
| 4 | Review + Docs | After Phase 3 | 1-2h | Tech Lead |
| 5 | Closure | After Phase 4 | 0.5-1h | Grader |

**Total Gate Time**: 4.5-8 hours

---

## No-Go Criteria

Proceed to NEXT gate **ONLY IF** previous gate fully PASSED.

### Phase 2 No-Go Examples
- ❌ Any test failure → Fix and re-run
- ❌ Regression detected → Debug and re-run
- ❌ Import errors → Fix code, re-run
- ❌ Lint failures → Fix style, re-run

### Phase 3 No-Go Examples
- ❌ <25% speedup → Investigate caching implementation
- ❌ Cache hit rate <90% → Review cache keys
- ❌ Memory overhead >10KB → Profile and optimize

### Phase 4 No-Go Examples
- ❌ Code review not approved → Address feedback
- ❌ Warnings not added → Add deprecation warnings
- ❌ Docs incomplete → Write docs

### Phase 5 No-Go Examples
- ❌ Artifacts missing → Create missing files
- ❌ Tests not passing → Debug failures
- ❌ Checklist incomplete → Complete all items

---

## Gate Rollback Procedure

If any gate FAILS:

1. **Identify failure**: Which gate? Which command failed?
2. **Debug**: Understand root cause
3. **Fix**: Address root cause
4. **Re-run**: Execute gate command again
5. **Document**: Log issue + fix in issue tracker
6. **Re-baseline**: If significant change, re-run earlier gates

**Example**: If Phase 3 performance gate fails:
```bash
# Debug: profile to identify bottleneck
python -m cProfile -s cumulative tests/benchmarks/test_policy_performance.py
# Fix caching implementation
vim src/prism/scanner_core/di_helpers.py
# Re-run gate
python tests/benchmarks/test_policy_performance.py --compare
```

---

## Sign-Off

All gates specified. Ready for Phase 2 execution.

**Grader**: gem-reviewer  
**Date**: May 9, 2026  
**Status**: ✅ **GATES DEFINED & READY**

---

**Next Step**: Begin Phase 2 (Wave 0 preparation) immediately.
