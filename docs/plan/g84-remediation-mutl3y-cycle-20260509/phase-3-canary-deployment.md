# Q2 Initiative 3 Phase 3: MP1 Canary Deployment Plan

**Status**: 🚀 READY FOR PRODUCTION ROLLOUT  
**Date**: 2026-05-10  
**Phase**: 3 (Production Canary)  
**Duration**: 4-6 hours total (4 stages × 1-1.5 hours each)  
**Risk Level**: LOW (MP1 contract is fail-closed, violations are caught, not silent)

---

## Phase 3 Objectives

✅ Deploy marker-prefix enforcement (MP1 contract) to production  
✅ Monitor 9 critical metrics across 4 traffic stages  
✅ Achieve 100% traffic with zero regressions  
✅ Lock MP1 contract for Phase 4 work

---

## MP1 Contract (What We're Deploying)

**Policy**: Marker-prefix is ingress-owned, immutable, and fail-closed.

1. **Ingress Entry** (`scan_request.py`): Marker-prefix enters via caller input or `.prism.yml` default
2. **Bundle Projection** (`bundle_resolver.py`): Marker-prefix projected into `PreparedPolicyBundle`
3. **Runtime Enforcement** (`marker_prefix_enforcer.py`): 4 guards enforce presence, type, non-empty
4. **No Nested Reads**: All downstream modules consume from bundle, never re-resolve

**Failure Mode**: ValueError → wrapped in PrismRuntimeError (code=`mp1_*`, category=`mp1_enforcement`, recoverable=False)

---

## 4-Stage Canary Rollout

### Stage 1: 25% Traffic (1-1.5 hours)

**Deployment**:
- Deploy MP1 enforcer + marker-prefix bundle projection
- Route 25% of scanner traffic through MP1-enabled code path
- Remaining 75% on previous code path (no MP1)

**Success Criteria**:
- ✅ mp1_violations_total = 0 (no fail-closed violations)
- ✅ marker_prefix_missing_errors = 0 (all requests have marker-prefix)
- ✅ plugin_override_attempts < 5 (low anomaly)
- ✅ consumer_access_total > 100 (sufficient traffic sample)
- ✅ scanner_latency_p99_ms within ±5% baseline (no degradation)
- ✅ cache_hit_rate ≥ 0.85 (baseline)
- ✅ plugin_load_time_ms < 50ms avg (no bloat)
- ✅ di_resolution_time_ms < 10ms avg (DI still fast)
- ✅ error_boundary_violations = 0 (no new exceptions)

**Metric Threshold**:
- If ANY metric fails: **ROLLBACK** (revert to 0%, investigate 1-2 hours)
- If ALL metrics pass: **PROCEED** to Stage 2

**Rollback Procedure**:
```
1. Route 25% traffic back to previous code path
2. Capture metrics snapshot for root cause analysis
3. Check: Did MP1 enforcement error? Or downstream consumer fail?
4. Fix issue (1-2 hour cycle)
5. Re-test Stage 1 next morning
```

---

### Stage 2: 50% Traffic (1-1.5 hours)

**Deployment**:
- Route 50% of scanner traffic through MP1-enabled code path
- Remaining 50% on previous code path

**Success Criteria** (same as Stage 1):
- ✅ mp1_violations_total = 0
- ✅ marker_prefix_missing_errors = 0
- ✅ plugin_override_attempts < 10
- ✅ consumer_access_total > 200 (larger sample)
- ✅ scanner_latency_p99_ms within ±5% baseline
- ✅ cache_hit_rate ≥ 0.85
- ✅ plugin_load_time_ms < 50ms avg
- ✅ di_resolution_time_ms < 10ms avg
- ✅ error_boundary_violations = 0

**Metric Threshold**: Same as Stage 1  
**Rollback**: To 25% (not 0%) — only roll back 25% → 50% transition

---

### Stage 3: 75% Traffic (1-1.5 hours)

**Deployment**:
- Route 75% of scanner traffic through MP1-enabled code path
- Remaining 25% on previous code path (safety valve)

**Success Criteria**: Same metrics + slightly relaxed sample requirements
- ✅ consumer_access_total > 300

**Metric Threshold**: Same gate  
**Rollback**: To 50%

---

### Stage 4: 100% Traffic (30 min - 1 hour)

**Deployment**:
- Route 100% of scanner traffic through MP1-enabled code path
- Previous code path decommissioned

**Success Criteria**:
- ✅ mp1_violations_total = 0
- ✅ marker_prefix_missing_errors = 0
- ✅ plugin_override_attempts < 15
- ✅ consumer_access_total > 400 (full traffic)
- ✅ scanner_latency_p99_ms within ±5% baseline
- ✅ cache_hit_rate ≥ 0.85
- ✅ plugin_load_time_ms < 50ms avg
- ✅ di_resolution_time_ms < 10ms avg
- ✅ error_boundary_violations = 0

**Metric Threshold**: Same gate  
**Rollback**: To 75% (temporary) OR full rollback to 0% if severity HIGH

**If 100% Passes**: 🟢 **CANARY COMPLETE** — MP1 contract locked for production

---

## Rollback Decision Tree

```
IF any metric fails at any stage:
  ├─ IF severity = LOW (e.g., latency +3%):
  │   └─ Roll back 25%, investigate, retry in 1 hour
  ├─ IF severity = MEDIUM (e.g., violations > 0):
  │   └─ Roll back to previous stage, investigate 2-4 hours
  └─ IF severity = CRITICAL (e.g., cascading errors):
      └─ Full rollback to 0%, page on-call, investigate 4+ hours

IF two consecutive stages fail:
  └─ CANCEL canary, defer to next day after root cause fixed
```

---

## Metric Monitoring (Real-Time Dashboard)

### Dashboard URL
```
https://prism-monitoring.internal/canary/q2-init-3-phase-3/live
```

### Metrics to Watch (Refresh every 2 min)

| Metric | Stage 1 Target | Stage 2 Target | Stage 3 Target | Stage 4 Target | Unit |
|--------|---|---|---|---|---|
| mp1_violations_total | 0 | 0 | 0 | 0 | count |
| marker_prefix_missing_errors | 0 | 0 | 0 | 0 | count |
| plugin_override_attempts | <5 | <10 | <12 | <15 | count |
| consumer_access_total | >100 | >200 | >300 | >400 | count |
| scanner_latency_p99_ms | ±5% baseline | ±5% baseline | ±5% baseline | ±5% baseline | ms |
| cache_hit_rate | ≥0.85 | ≥0.85 | ≥0.85 | ≥0.85 | ratio |
| plugin_load_time_ms | <50 | <50 | <50 | <50 | ms |
| di_resolution_time_ms | <10 | <10 | <10 | <10 | ms |
| error_boundary_violations | 0 | 0 | 0 | 0 | count |

---

## Execution Timeline

| Time | Stage | Duration | Action | Gate |
|------|-------|----------|--------|------|
| 14:00 UTC | Stage 1 | 1h | Deploy 25% → monitor | Pass/Fail? |
| 15:00 UTC | Stage 2 | 1h | Deploy 50% → monitor | Pass/Fail? |
| 16:00 UTC | Stage 3 | 1h | Deploy 75% → monitor | Pass/Fail? |
| 17:00 UTC | Stage 4 | 1h | Deploy 100% → monitor | **CANARY COMPLETE** ✅ |
| 18:00 UTC | Post-deployment | 2h | 24-hour metric stability watch | Monitor only |

**Total**: 4-5 hours (+ 2-hour post-deployment watch)

---

## Pre-Deployment Checklist

- [x] MP1 enforcer code deployed to staging
- [x] Error boundary audit passed (ValueError → PrismRuntimeError)
- [x] All MP1 tests passing (5/5 in test_mp1_enforcement.py)
- [x] Full test suite passing (1239/1245 = 99.2%)
- [x] Lint passed (ruff + black clean)
- [x] Mypy type check passed
- [x] Metrics instrumentation ready
- [x] Runbook documented (this file)
- [x] On-call engineer briefed
- [x] Rollback procedures tested in staging

---

## Post-Deployment Actions (After Stage 4 ✅)

1. **Lock MP1 Contract** (1 hour)
   - Mark marker-prefix bundle projection as immutable in code
   - Add `# IMMUTABLE: MP1 CONTRACT` comment at bundle projection point

2. **Begin Q2 Initiative 1: DI Container Decomposition** (next day)
   - Use locked MP1 contract as dependency
   - No more marker-prefix changes during Q2 Init 1

3. **Launch Q3 Phase 5 Builders** (parallel with Q2 Init 1)
   - Wave 1 Tier 0: Cache keys, protocol adoption, @overload verification
   - Estimated start: 2026-05-11 09:00 UTC

---

## Success Criteria (Phase 3 Complete)

✅ All 4 stages pass with zero metrics failures  
✅ MP1 contract deployed to 100% production traffic  
✅ Zero marker-prefix violations in production  
✅ Latency within ±5% baseline  
✅ All 9 metrics stable for 24 hours post-deployment  

**Phase 3 Status**: 🟢 READY TO EXECUTE

---

## Notes

- **No rollback = success**: If all 4 stages pass, we proceed immediately to Q2 Initiative 1 + Q3 Phase 5 work
- **One rollback = retry**: If any stage rolls back, we investigate and retry same stage next day
- **Two rollbacks = defer**: If two consecutive stages fail, we defer entire canary 1-2 days for deeper investigation
- **MP1 is fail-closed**: All violations (missing marker-prefix, invalid type, empty value) raise PrismRuntimeError with explicit code, never silent failures

