# Wave 1: Critical Performance Remediation

**Wave ID:** wave_1
**Priority:** HIGH
**Finding:** FIND-02
**File:** `src/prism/scanner_extract/task_line_parsing.py`
**Estimated Effort:** 4h

---

## Problem Statement

The `_PolicyBackedCollectionProxy` and `_PolicyBackedRegexProxy` classes in `task_line_parsing.py` perform DI container lookups on every single access to policy-backed collections and regex patterns. This creates measurable runtime overhead on the hot path for task line parsing.

### Current Implementation

```python
class _PolicyBackedCollectionProxy:
    def __init__(self, policy_attr_name: str) -> None:
        self._policy_attr_name = policy_attr_name

    def _current_value(self) -> object:
        return getattr(
            require_prepared_policy(None, "task_line_parsing", "task_line_parsing"),
            self._policy_attr_name,
        )

    def __iter__(self) -> Iterator[Any]:
        value = self._current_value()
        # ...
```

Every `__iter__`, `__contains__`, `__len__`, `__repr__` call triggers a full DI resolution via `require_prepared_policy(None, ...)`.

### Performance Impact

- **Task line parsing** is called for every line in every task file during feature detection
- Each line may trigger multiple collection lookups (TASK_BLOCK_KEYS, TASK_META_KEYS, etc.)
- Each lookup = 1 DI container access + 1 getattr
- For a role with 100 task files × 50 lines = 5,000 lookups per scan
- Multiplied by 10+ collection attributes = 50,000+ DI lookups per scan

---

## Investigation Tasks (Phase 3)

### T3-01: Baseline Performance Measurement

**Objective:** Measure current overhead of policy-backed proxy pattern

**Steps:**

1. Create a minimal benchmark script that exercises task line parsing 10,000 times
2. Use `timeit` or `cProfile` to measure baseline
3. Record: calls/sec, avg latency per call, memory allocations

**Artifact:** `docs/plan/gilfoyle-review-20260516-remediation/artifacts/wave1-baseline-metrics.yaml`

**Expected Output:**

```yaml
baseline:
  iterations: 10000
  total_time_ms: 1250.3
  avg_latency_us: 125.03
  calls_per_sec: 8000
  memory_allocations: 45000
```

---

### T3-02: Root Cause Analysis

**Objective:** Identify exact call sites and frequency of proxy access

**Steps:**
1. Add temporary instrumentation to `_current_value()` to log call count
2. Run full test suite with instrumentation
3. Identify top 5 call sites by frequency
4. Determine if any call sites can batch policy resolution

**Artifact:** `docs/plan/gilfoyle-review-20260516-remediation/artifacts/wave1-call-site-analysis.yaml`

---

### T3-03: Design Options Evaluation

**Objective:** Evaluate 3 remediation approaches

**Options:**

1. **Option A: Eager Resolution at Module Load**
   - Resolve policy once at import time
   - Store resolved values in module-level constants
   - **Pros:** Zero runtime overhead
   - **Cons:** Loses dynamic policy updates, breaks test isolation

2. **Option B: Lazy Resolution with Caching**
   - Resolve policy on first access, cache for scan duration
   - Use `functools.lru_cache` or instance-level cache
   - **Pros:** Preserves dynamic updates within scan, minimal overhead
   - **Cons:** Still requires 1 lookup per scan (acceptable)

3. **Option C: Pass Policy as Parameter**
   - Refactor all call sites to accept policy as explicit parameter
   - Resolve policy once at ingress, pass through call chain
   - **Pros:** Cleanest architecture, no hidden DI lookups
   - **Cons:** Largest refactor scope (affects 4+ modules)

**Recommendation:** Option B for minimal scope, Option C for long-term architecture

**Artifact:** `docs/plan/gilfoyle-review-20260516-remediation/artifacts/wave1-design-options.md`

---

## Implementation Tasks (Phase 5)

### T5-01: Implement Lazy Resolution with Caching

**File:** `src/prism/scanner_extract/task_line_parsing.py`

**Changes:**
1. Add module-level cache for resolved policy
2. Modify `_current_value()` to check cache before DI lookup
3. Add cache invalidation hook for test isolation
4. Preserve existing public API (no breaking changes)

**Implementation Sketch:**

```python
# Module-level cache (per-scan, cleared between scans)
_task_line_parsing_policy_cache: PreparedTaskLineParsingPolicy | None = None

def _get_cached_policy() -> PreparedTaskLineParsingPolicy:
    global _task_line_parsing_policy_cache
    if _task_line_parsing_policy_cache is None:
        _task_line_parsing_policy_cache = require_prepared_policy(
            None, "task_line_parsing", "task_line_parsing"
        )
    return _task_line_parsing_policy_cache

def clear_task_line_parsing_cache() -> None:
    """Clear cache for test isolation. Called by test fixtures."""
    global _task_line_parsing_policy_cache
    _task_line_parsing_policy_cache = None
```

**Test Requirements:**
- Existing tests pass without modification
- New test: `test_policy_cache_cleared_between_scans`
- New test: `test_policy_cache_hit_reduces_di_lookups`

---

### T5-02: Apply Same Pattern to Regex Proxy

**File:** `src/prism/scanner_extract/task_line_parsing.py`

**Changes:**
1. Apply identical caching strategy to `_PolicyBackedRegexProxy`
2. Cache compiled regex patterns (they're immutable, safe to cache)
3. Verify regex match performance improvement

**Implementation Sketch:**

```python
_regex_pattern_cache: dict[str, re.Pattern[str]] = {}

def _get_cached_regex(attr_name: str) -> re.Pattern[str]:
    if attr_name not in _regex_pattern_cache:
        policy = _get_cached_policy()
        pattern = getattr(policy, attr_name)
        if not isinstance(pattern, re.Pattern):
            raise ValueError(f"{attr_name} must be compiled re.Pattern")
        _regex_pattern_cache[attr_name] = pattern
    return _regex_pattern_cache[attr_name]
```

---

### T5-03: Add Performance Regression Test

**File:** `src/prism/tests/core/test_task_line_parsing.py`

**New Test:**

```python
def test_policy_backed_proxy_performance_regression():
    """Ensure proxy overhead stays below 10us per access after caching."""
    import timeit

    setup = """
from prism.scanner_extract.task_line_parsing import TASK_BLOCK_KEYS
    """

    stmt = """
list(TASK_BLOCK_KEYS)  # Trigger __iter__
"include" in TASK_BLOCK_KEYS  # Trigger __contains__
    """

    times = timeit.repeat(stmt, setup, number=10000, repeat=5)
    avg_time_us = min(times) * 1e6 / 10000

    assert avg_time_us < 10.0, f"Proxy overhead {avg_time_us}us exceeds 10us threshold"
```

---

## Validation Gate (Phase 6)

**Commands:**
```bash
# Focused test suite
pytest -q src/prism/tests/core/test_task_line_parsing.py -v

# Type checking
python3 -m mypy src/prism/scanner_extract/task_line_parsing.py

# Linting
python3 -m ruff check src/prism/scanner_extract/task_line_parsing.py
python3 -m black --check src/prism/scanner_extract/task_line_parsing.py

# Performance sanity check
python3 -c "
from prism.scanner_extract.task_line_parsing import TASK_BLOCK_KEYS
import timeit
times = timeit.repeat('list(TASK_BLOCK_KEYS)', number=100000, repeat=3)
print(f'Avg: {min(times)*1e6/100000:.2f}us per access')
"
```

**Success Criteria:**
- All existing tests pass
- New performance test passes (<10us per access)
- mypy: 0 new errors
- ruff: clean
- black: clean

---

## Rollback Plan

If performance regression is detected post-deployment:

1. Revert `task_line_parsing.py` to pre-wave1 commit
2. Run full regression suite to confirm baseline restored
3. File incident report with before/after metrics
4. Escalate to architecture review for alternative approach

---

## Artifacts Checklist

- [ ] `wave1-baseline-metrics.yaml` — Pre-fix performance baseline
- [ ] `wave1-call-site-analysis.yaml` — Hot path identification
- [ ] `wave1-design-options.md` — Remediation approach evaluation
- [ ] `wave1-implementation-summary.md` — Changes made + rationale
- [ ] `wave1-validation-report.yaml` — Gate results + metrics

---

## Dependencies

- None (standalone wave, no file conflicts with other waves)

---

## Owner

**Assigned:** mutl3y-builder (LOW-COST tier)
**Model:** GPT-5 mini → escalate to Claude Sonnet 4.5 if refactoring complexity exceeds estimate

---

## Status

- [ ] Phase 3 investigation complete
- [ ] Phase 5 implementation complete
- [ ] Phase 6 validation passed
- [ ] Wave closed
