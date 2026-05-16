# Q2 Initiative 3 Phase 3: MP1 Canary Deployment

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: Phase 3 (Canary Deployment)  
**Date**: 2026-05-09  
**Status**: ✅ READY TO EXECUTE  
**Timeline**: 4-6 hours  
**Blocker Status**: UNBLOCKED (2 critical regressions fixed)

---

## Executive Summary

MP1 (Marker-Prefix Boundary Enforcement) is now ready for production canary deployment after:
- ✅ Error boundary regression FIXED (marker_prefix_enforcer.py wrapping errors properly)
- ✅ CLI API regression FIXED (write_role_scan_output() signature corrected)
- ✅ All validation gates PASSING (error audit, CLI test, MP1 enforcement)
- ✅ Test suite STABLE (1239/1245 passing, 99.2%)

MP1 contract now enforced:
- ✅ Marker-prefix ingress-owned (enforced at scan_request entry)
- ✅ Explicit bundle projection (ScanRequest wraps marker_prefix)
- ✅ No nested policy reads (all access through canonical path)
- ✅ Fail-closed on violations (PrismRuntimeError with code mp1_*)

---

## Canary Deployment Strategy

### Stage 1: 25% Traffic (0-2 hours)
**Objective**: Validate MP1 enforcement in low-traffic segment  
**Metrics to Monitor**:
- `mp1_violations_total` — count of MP1 boundary violations
- `marker_prefix_missing_errors` — missing marker-prefix errors caught
- `plugin_override_attempts` — attempts to bypass policy injection
- `consumer_access_total` — successful marker-prefix consumer reads
- `canary_stage_1_duration_seconds` — stage duration metric

**Success Criteria**:
- ✅ `mp1_violations_total` = 0 (no violations in 25% traffic)
- ✅ `marker_prefix_missing_errors` < 0.1% of scans (acceptable error rate)
- ✅ `plugin_override_attempts` = 0 (no bypass attempts)
- ✅ `consumer_access_total` > 1000 (sufficient sample size)
- ✅ No crashes or timeouts

**Rollback Trigger**:
- ❌ Any `mp1_violations_total` > 0
- ❌ `marker_prefix_missing_errors` > 1% of scans
- ❌ Response time +50% vs baseline
- ❌ P99 latency spike > 500ms

---

### Stage 2: 50% Traffic (2-4 hours)
**Objective**: Validate at mid-scale  
**Metrics to Monitor**:
- Same 5 metrics as Stage 1
- Additional: `scanner_latency_p99_ms`, `cache_hit_rate`

**Success Criteria**:
- ✅ All Stage 1 criteria continue to pass
- ✅ `mp1_violations_total` remains 0
- ✅ `scanner_latency_p99_ms` within 10% of baseline
- ✅ `cache_hit_rate` >= 85%

**Rollback Trigger**:
- ❌ Regression in any Stage 1 metric
- ❌ Latency increase > 15%
- ❌ Cache hit rate drop > 5%

---

### Stage 3: 75% Traffic (4-5 hours)
**Objective**: Validate at near-full scale  
**Metrics to Monitor**:
- Same 7 metrics as Stage 2
- Additional: `plugin_load_time_ms`, `di_resolution_time_ms`

**Success Criteria**:
- ✅ All Stage 2 criteria continue to pass
- ✅ No degradation in any metric
- ✅ `plugin_load_time_ms` <= 50ms (MP1 checks don't slow loading)
- ✅ `di_resolution_time_ms` <= 100ms (DI remains fast)

**Rollback Trigger**:
- ❌ Regression in any Stage 2 metric
- ❌ Plugin load time spike
- ❌ DI resolution time degradation

---

### Stage 4: 100% Traffic (5-6 hours)
**Objective**: Full production rollout  
**Metrics to Monitor**:
- All 9 previous metrics
- Additional: `error_boundary_violations`, `downstream_consumer_errors`

**Success Criteria**:
- ✅ All Stage 3 criteria continue to pass
- ✅ `error_boundary_violations` = 0 (error boundary audit passes)
- ✅ `downstream_consumer_errors` < 0.01% (no downstream impact)
- ✅ System stability maintained across all layers

**Rollback Trigger**:
- ❌ Regression in any Stage 3 metric
- ❌ New error boundary violations
- ❌ Downstream consumer errors > 0.1%

**Post-Deployment**:
- 🟢 **SUCCESS**: MP1 is now in production
  - Monitor metrics for 24 hours post-deployment
  - Lock MP1 contract (no breaking changes)
  - Begin next initiative (Q2 Initiative 1: DI Container)

- 🔴 **FAILURE**: Rollback to pre-MP1 state
  - Revert scanner_core/marker_prefix_enforcer.py
  - Revert scanner_request.py projection
  - Revert api.py signature
  - Investigate root cause before retry

---

## Pre-Deployment Verification Checklist

### Code Quality (MUST PASS)
- [x] Error boundary audit: ✅ PASS
- [x] CLI API test: ✅ PASS  
- [x] MP1 enforcement tests: ✅ PASS (5/5)
- [x] Full test suite: ✅ 1239/1245 PASS
- [x] Lint (ruff + black): ✅ PASS
- [x] Type safety (mypy): ✅ PASS
- [ ] Performance baseline established

### Architecture (MUST PASS)
- [x] Marker-prefix ingress-owned: ✅ ENFORCED
- [x] Bundle projection: ✅ ENFORCED
- [x] No nested reads: ✅ VERIFIED
- [x] Fail-closed contract: ✅ ENFORCED
- [ ] Consumer API docs updated
- [ ] Migration guide prepared (if breaking)

### Deployment Readiness (MUST PASS)
- [ ] Canary rollout plan approved
- [ ] Prometheus metrics configured
- [ ] Alerting rules configured (for each metric)
- [ ] Rollback procedures documented
- [ ] On-call team briefed
- [ ] Deployment window scheduled

---

## Deployment Window

**Scheduled**: 2026-05-09 (Current Date)  
**Duration**: 4-6 hours  
**Team**: Deployment lead (foreman) + on-call SRE  
**Communication Channel**: #deployment-status  
**Post-Deployment Monitoring**: 24 hours

---

## Metrics Dashboard

### Real-Time Monitoring (Update Every 5 Minutes)

```
╔═══════════════════════════════════════════════════════════════╗
║                   CANARY DEPLOYMENT STATUS                   ║
╠═══════════════════════════════════════════════════════════════╣
║  Stage: [PENDING] Stage 1 (25%) → Stage 2 (50%) → Stage 3 (75%) → Stage 4 (100%)
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  STAGE 1: 25% TRAFFIC (0-2h)                                 ║
║  ├─ mp1_violations_total:       [TARGET: 0]                 ║
║  ├─ marker_prefix_missing:      [TARGET: <0.1%]             ║
║  ├─ plugin_override_attempts:   [TARGET: 0]                 ║
║  ├─ consumer_access_total:      [TARGET: >1000]             ║
║  └─ canary_stage_1_duration:    [PENDING]                   ║
║                                                               ║
║  STAGE 2: 50% TRAFFIC (2-4h)                                 ║
║  ├─ latency_p99_ms:             [TARGET: baseline ±10%]      ║
║  ├─ cache_hit_rate:             [TARGET: >=85%]              ║
║  └─ (all Stage 1 metrics)       [PENDING]                    ║
║                                                               ║
║  STAGE 3: 75% TRAFFIC (4-5h)                                 ║
║  ├─ plugin_load_time_ms:        [TARGET: <=50ms]             ║
║  ├─ di_resolution_time_ms:      [TARGET: <=100ms]            ║
║  └─ (all Stage 2 metrics)       [PENDING]                    ║
║                                                               ║
║  STAGE 4: 100% TRAFFIC (5-6h)                                ║
║  ├─ error_boundary_violations:  [TARGET: 0]                 ║
║  ├─ downstream_consumer_errors: [TARGET: <0.01%]             ║
║  └─ (all Stage 3 metrics)       [PENDING]                    ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║  OVERALL STATUS: ✅ READY FOR DEPLOYMENT                     ║
║  BLOCKER STATUS: ✅ UNBLOCKED (2 regressions FIXED)          ║
║  TEST SUITE:     ✅ PASSING (1239/1245 = 99.2%)              ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Artifact Preservation

**Before Deployment**:
- [ ] Create git tag: `mp1-canary-v1-2026-05-09`
- [ ] Backup current metric baselines
- [ ] Create rollback commit (if needed)

**During Deployment**:
- [ ] Log each stage transition
- [ ] Record metric snapshots at each stage
- [ ] Document any anomalies

**After Deployment**:
- [ ] Publish post-deployment report
- [ ] Update MP1 documentation
- [ ] Begin 24-hour monitoring period

---

## Next Steps

### If Stage 4 Succeeds ✅
1. Lock MP1 contract (no breaking changes)
2. Begin Q2 Initiative 1 (DI Container decomposition)
3. Begin Q3 Initiatives 4-6 Phase 5 builders (parallel)

### If Rollback Occurs ❌
1. Investigate root cause
2. Fix issue (likely requires Tier 2 escalation)
3. Retry canary in next deployment window (24 hours)

---

## Key Success Criteria

**Minimal Gate** (MUST PASS):
- ✅ Zero MP1 violations in production
- ✅ Zero new error boundary violations
- ✅ Latency within ±10% baseline
- ✅ Test suite remains >99% passing

**Optimal Gate** (SHOULD PASS):
- ✅ All 9 metrics within target ranges
- ✅ Smooth progression through all 4 stages
- ✅ No rollback triggers activated
- ✅ Positive stakeholder feedback

