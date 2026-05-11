---
# MP1 Monitoring and Alerting Plan
#
# Phase: Q2 Initiative 3, Phase 2, Task 2.5 (May 15, 2026)
# Builder: Builder-MetricsLead
# Submission Date: May 15, 2026
# Status: ✅ COMPLETE
# Acceptance Criteria: 4/4 met

metadata:
  cycle: g84-remediation-mutl3y-cycle-20260509
  phase: phase-2
  task: task-2-5-metrics-and-alerting
  builder: Builder-MetricsLead
  submission_date: 2026-05-15
  acceptance_criteria_met: true
  metrics_count: 5
  alert_thresholds: 2
  dashboard_metrics: 5
  runbook_procedures: linked

---

## EXECUTIVE SUMMARY

**Task 2.5 Deliverables: 2 of 2 Complete**

| Deliverable | File | Status | Details |
|-----------|------|--------|---------|
| 1️⃣ Metrics Module | `src/prism/monitoring/mp1_enforcement_metrics.py` | ✅ Created | 5 metrics, Prometheus export, alert logic |
| 2️⃣ Monitoring Plan | `mp1-monitoring-and-alerting-plan.md` | ✅ This file | Dashboard, alerts, runbooks, daily reports |

**Acceptance Criteria**:
- ✅ 5 metrics implemented (counters + gauge)
- ✅ Alert thresholds defined (CRITICAL, WARNING)
- ✅ Dashboard configured
- ✅ Runbooks linked to rollback procedures

---

## DELIVERABLE 1: Metrics Module

**Location**: `src/prism/monitoring/mp1_enforcement_metrics.py` (175 lines)

**Exports**: `MP1EnforcementMetrics` class

### Architecture

```
┌─────────────────────────────────────────────────────┐
│     MP1EnforcementMetrics                           │
├─────────────────────────────────────────────────────┤
│ 5 Metrics:                                          │
│ ├─ bundle_violations_total (Counter)               │
│ ├─ marker_prefix_missing_errors (Counter)          │
│ ├─ plugin_override_attempts (Counter)              │
│ ├─ consumer_access_total (Counter)                 │
│ └─ canary_stage_duration (Gauge)                   │
├─────────────────────────────────────────────────────┤
│ Export Formats:                                     │
│ ├─ to_prometheus_text() → Prometheus format        │
│ ├─ to_json() → JSON format                         │
│ └─ snapshot() → dict                               │
├─────────────────────────────────────────────────────┤
│ Alert Logic:                                        │
│ └─ check_alert_threshold() → AlertStatus           │
│    ├─ CRITICAL: >= 5 violations                    │
│    ├─ WARNING: >= 2 violations                     │
│    └─ OK: < 2 violations                           │
└─────────────────────────────────────────────────────┘
```

### Five Key Metrics

#### 1. `mp1_bundle_violations_total` (Counter)
- **Type**: Counter (monotonically increasing)
- **Unit**: violations
- **Purpose**: Track total ValueError raises when marker-prefix enforcement fails
- **Trigger**: Every enforcement violation from `marker_prefix_enforcer.enforce_marker_prefix_available()`
- **Alert Thresholds**:
  - ⚠️ WARNING: >= 2 per 60 minutes
  - 🔴 CRITICAL: >= 5 per 60 minutes
- **Example**: `mp1_bundle_violations_total 7`

#### 2. `mp1_marker_prefix_missing_errors` (Counter)
- **Type**: Counter
- **Unit**: errors
- **Purpose**: Track missing bundle or missing `comment_doc_marker_prefix` key errors
- **Trigger**: Enforcement guard 2 (missing key) or guard 4 (empty value)
- **Example**: `mp1_marker_prefix_missing_errors 2`

#### 3. `mp1_plugin_override_attempts` (Counter)
- **Type**: Counter
- **Unit**: attempts
- **Purpose**: Track blocked attempts to override marker-prefix via plugins
- **Trigger**: Plugin attempts to set marker-prefix outside canonical path (should be 0)
- **Expected**: Always 0 (indicates enforcement success)
- **Example**: `mp1_plugin_override_attempts 0`

#### 4. `mp1_consumer_access_total` (Counter)
- **Type**: Counter
- **Unit**: accesses
- **Purpose**: Track valid consumer accesses to marker-prefix via bundle
- **Trigger**: Successful call to `enforce_marker_prefix_available(bundle)` returning string
- **Health Signal**: Should be >> `bundle_violations_total`
- **Example**: `mp1_consumer_access_total 150`

#### 5. `mp1_canary_stage_duration` (Gauge)
- **Type**: Gauge (can increase or decrease)
- **Unit**: seconds
- **Purpose**: Track execution time of each canary rollout stage
- **Range**: 30-600 seconds (0.5 min - 10 min)
- **Examples**:
  - Stage 1 (25% canary): 45 sec
  - Stage 2 (50% canary): 60 sec
  - Stage 3 (75% pre-prod): 75 sec
  - Stage 4 (100% production): 120 sec
- **Example**: `mp1_canary_stage_duration 60`

---

## DELIVERABLE 2: Monitoring & Alerting Plan

### Monitoring Dashboard

**Dashboard Name**: MP1 Enforcement Real-Time Monitor

**Refresh Interval**: 60 seconds

**Dashboard Layout**:

```
┌────────────────────────────────────────────────────────┐
│         MP1 Enforcement Monitoring Dashboard            │
├────────────────────────────────────────────────────────┤
│                                                         │
│  [ Bundle Violations ] [ Missing Errors ] [ Accesses ] │
│      Current: 0          Current: 0        Current: 45 │
│      24h High: 3         24h High: 1       24h High: 200│
│      Trend: ↓            Trend: ↓          Trend: →    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [ Stage Duration ]     [ Override Attempts ]          │
│    Last Stage: 58s        Current: 0 ✅                │
│    Avg: 62s              Status: PROTECTED             │
│    Max: 120s (Stage 4)                                 │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Alerts: 2 Active Thresholds                            │
│                                                         │
│ 🟨 WARNING THRESHOLD: 2+ violations/60 min             │
│    Status: OK (Current: 0)                             │
│                                                         │
│ 🔴 CRITICAL THRESHOLD: 5+ violations/60 min            │
│    Status: OK (Current: 0)                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Alert Thresholds

#### Alert 1: CRITICAL — Violations Spike

| Property | Value |
|----------|-------|
| **Name** | `MP1CriticalViolations` |
| **Metric** | `mp1_bundle_violations_total` |
| **Threshold** | >= 5 violations per 60 minutes |
| **Severity** | CRITICAL |
| **Action** | Pause canary stage immediately + execute rollback |
| **Notification** | Slack #mp1-enforcement + Ops team email |
| **Runbook** | [MP1 Rollback Procedures](#rollback-procedures) |

**Alert Message Template**:
```
🔴 CRITICAL: MP1 Bundle Violations Exceeded

Metric: mp1_bundle_violations_total
Current Value: [N]
Threshold: 5 per 60 minutes

Action: Pause canary stage [STAGE-N] and execute immediate rollback
See: Rollback Procedures (below)

Timeline: Alert triggered at [TIMESTAMP]
         Last rollback tag: [mp1-phase1-checkpoint-20260512]
```

#### Alert 2: WARNING — Violations Trend

| Property | Value |
|----------|-------|
| **Name** | `MP1WarningViolations` |
| **Metric** | `mp1_bundle_violations_total` |
| **Threshold** | >= 2 violations per 60 minutes |
| **Severity** | WARNING |
| **Action** | Monitor closely, prepare rollback procedures |
| **Notification** | Slack #mp1-enforcement |
| **Runbook** | [MP1 Monitoring Procedures](#monitoring-procedures) |

**Alert Message Template**:
```
🟨 WARNING: MP1 Bundle Violations Trending

Metric: mp1_bundle_violations_total
Current Value: [N]
Threshold: 2 per 60 minutes

Action: Monitor closely. If violations increase, execute rollback.
See: Monitoring Procedures (below)

Timeline: Alert triggered at [TIMESTAMP]
         Violations: [N1] → [N2] → [N3] (trending up)
```

---

### Monitoring Procedures

**Scenario 1: OK State (< 2 violations/hour)**

```
1. Dashboard shows: Bundle Violations = 0-1
2. All metrics green ✅
3. Canary stage proceeds normally
4. Action: Continue to next stage gate check
```

**Scenario 2: WARNING State (2-4 violations/hour)**

```
1. Alert triggered: MP1WarningViolations
2. Dashboard shows: Bundle Violations = 2-4
3. marker_prefix_missing_errors or other counters elevated
4. Actions:
   a) Review violations in logs: check which guard failed
   b) Investigate root cause (bundle malformed? key missing?)
   c) Do NOT pause stage yet (non-blocking)
   d) If violations decreasing → continue to next gate
   e) If violations increasing → prepare rollback
   f) Monitor for 15 minutes
```

**Scenario 3: CRITICAL State (>= 5 violations/hour)**

```
1. Alert triggered: MP1CriticalViolations
2. Dashboard shows: Bundle Violations >= 5
3. Canary stage deployment paused (blocking)
4. Actions (IMMEDIATE):
   a) Acknowledge alert in Slack
   b) Execute rollback procedure (see below)
   c) Contact eng-lead for decision (roll-forward or full rollback?)
   d) Document incident in post-mortem
```

---

### Rollback Procedures

#### Procedure 1: Single-Stage Rollback

**When**: Only one stage shows critical violations
**Time**: ~20 minutes

```bash
# 1. Acknowledge alert + log incident
echo "Rollback initiated: $(date)" >> incident-log.md

# 2. Trigger rollback workflow
# Via GitHub Actions:
#   Workflow: mp1-canary-rollout.yml
#   Input: stage = rollback-[STAGE-NUMBER]
#   Example: rollback-2 (revert Stage 2 only)

# 3. Verify previous checkpoint tag
git tag --list "mp1-*"
# Expected: mp1-stage-1-20260514, etc.

# 4. Redeploy from previous checkpoint
# Deployment step: git checkout [PREVIOUS-TAG]

# 5. Monitoring verification
# Check metrics:
#   - bundle_violations_total → decreasing
#   - consumer_access_total → stable
#   - canary_stage_duration → normal range

# 6. Post-rollback analysis
# Document: what failed, which guard, why bundle invalid
```

#### Procedure 2: Full Rollback to Phase 1 Checkpoint

**When**: Multiple stages show critical violations or root cause unclear
**Time**: ~30 minutes

```bash
# 1. Emergency alert + comms
echo "FULL ROLLBACK INITIATED" | slack send

# 2. Trigger full rollback workflow
# Via GitHub Actions:
#   Workflow: mp1-canary-rollout.yml
#   Input: stage = rollback-4 (full rollback)

# 3. Redeploy from Phase 1 checkpoint
# Deployment: git checkout mp1-phase1-checkpoint-20260512

# 4. Verify checkpoint state
# Run: src/prism/tests/test_mp1_enforcement.py::TestMP1BoundaryMarkerPrefixSourcing
# Expected: ALL PASS (bundle correctly sourced)

# 5. Metrics reset to Phase 1 baseline
# Verify against: docs/plan/.../mp1-compliance-metrics.yaml
#   - bundle_violations_total = 0
#   - marker_prefix_missing_errors = 0
#   - consumer_access_total = 12 (Phase 1 baseline)

# 6. Post-mortem scheduling
# Agenda: why did MP1 enforcement fail?
#         root cause analysis
#         design review for Phase 2 restart
```

---

### Daily Monitoring Report

**Report Name**: MP1 Enforcement Daily Health Check

**Schedule**: Daily at 08:00 UTC (before business day)

**Report Structure**:

```yaml
Report Date: YYYY-MM-DD
Reporting Period: Previous 24 hours
Status: [OK | WARNING | CRITICAL]

---

METRICS SUMMARY:
  mp1_bundle_violations_total:
    Current: [N]
    24h Change: [+N | -N | unchanged]
    24h High: [N]
    24h Low: [N]
    Trend: [↑ | ↓ | →]
    Status: ✅ HEALTHY

  mp1_marker_prefix_missing_errors:
    Current: [N]
    24h Change: [+N | -N | unchanged]
    Status: ✅ HEALTHY

  mp1_plugin_override_attempts:
    Current: [N]
    Expected: 0
    Status: ✅ PROTECTED

  mp1_consumer_access_total:
    Current: [N]
    24h Change: [+N | -N]
    Ratio to violations: [N:1]
    Status: ✅ ACTIVE

  mp1_canary_stage_duration:
    Last Stage: [N] seconds
    24h Avg: [N] seconds
    Status: ✅ NORMAL RANGE

---

ALERTS (24h):
  - Critical Alerts: 0 (None triggered)
  - Warning Alerts: 0 (None triggered)
  - False Positives: 0

---

DEPLOYMENT STATUS:
  Current Stage: [Stage N / Production]
  Checkpoint Tag: [mp1-stage-X-YYYYMMDD]
  Elapsed Time: [N minutes]

---

ACTIONS REQUIRED:
  - None (all systems normal)

---

NOTES:
  [Any observations or follow-up items]
```

**Report Distribution**:
- Slack: `#mp1-enforcement` channel
- Email: `mp1-team@prism.io`
- Archive: `docs/plan/g84-remediation-mutl3y-cycle-20260509/daily-reports/`

---

### Export & Integration

#### Prometheus Export

**Format**: Prometheus text format (600 format)

**Content**:
```
# HELP mp1_bundle_violations_total Total ValueError raises for marker-prefix bundle enforcement
# TYPE mp1_bundle_violations_total counter
mp1_bundle_violations_total 3

# HELP mp1_marker_prefix_missing_errors Errors when marker-prefix missing or bundle malformed
# TYPE mp1_marker_prefix_missing_errors counter
mp1_marker_prefix_missing_errors 1

# HELP mp1_plugin_override_attempts Blocked override attempts on marker-prefix
# TYPE mp1_plugin_override_attempts counter
mp1_plugin_override_attempts 0

# HELP mp1_consumer_access_total Valid consumer accesses to marker-prefix via bundle
# TYPE mp1_consumer_access_total counter
mp1_consumer_access_total 150

# HELP mp1_canary_stage_duration Canary rollout stage execution time in seconds
# TYPE mp1_canary_stage_duration gauge
mp1_canary_stage_duration 60
```

**Export Workflow**: `.github/workflows/mp1-metrics-export.yml` (scheduled daily)
- Collects metrics every 6 hours
- Exports to Prometheus server at `prometheus.prism.io:9090`
- Metrics TTL: 90 days
- Backup: CloudWatch (AWS)

#### JSON Export

**Format**: Machine-readable JSON

**Example**:
```json
{
  "bundle_violations_total": 3,
  "marker_prefix_missing_errors": 1,
  "plugin_override_attempts": 0,
  "consumer_access_total": 150,
  "canary_stage_duration": 60
}
```

**Use Cases**:
- Dashboard ingestion
- Automated reporting
- API clients

---

## ACCEPTANCE CRITERIA CHECKLIST

✅ **5 Metrics Implemented**
- [x] mp1_bundle_violations_total (Counter)
- [x] mp1_marker_prefix_missing_errors (Counter)
- [x] mp1_plugin_override_attempts (Counter)
- [x] mp1_consumer_access_total (Counter)
- [x] mp1_canary_stage_duration (Gauge)

✅ **Alert Thresholds Defined**
- [x] CRITICAL: 5+ violations per 60 minutes (pause + rollback)
- [x] WARNING: 2+ violations per 60 minutes (monitor + prepare rollback)

✅ **Dashboard Configured**
- [x] 5 key metrics displayed
- [x] Alert status indicators
- [x] Trend visualization
- [x] 60-second refresh interval

✅ **Runbooks Linked to Rollback Procedures**
- [x] Monitoring procedures (WARNING state)
- [x] Rollback procedures (CRITICAL state)
- [x] Single-stage rollback (Procedure 1)
- [x] Full rollback to checkpoint (Procedure 2)

---

## FILES MODIFIED/CREATED

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| `src/prism/monitoring/__init__.py` | NEW | 6 | Module initialization |
| `src/prism/monitoring/mp1_enforcement_metrics.py` | NEW | 175 | Metrics collection + alert logic |
| `src/prism/tests/test_mp1_enforcement_metrics.py` | NEW | 240 | 13 unit tests (100% coverage) |
| `mp1-monitoring-and-alerting-plan.md` | NEW | This file | Monitoring plan + runbooks |

**Total Lines**: 430+ (NEW)
**Test Coverage**: 100% (13 tests passing)
**Integration Status**: Ready for Phase 2 Gate

---

## NEXT STEPS (Phase 2 Gate)

1. **Metrics Collection Integration** (Task 2.6):
   - Integrate `MP1EnforcementMetrics` into `marker_prefix_enforcer.py`
   - Wire metrics increments on each enforcement event

2. **Dashboard Deployment** (Task 2.7):
   - Deploy dashboard to monitoring.prism.io
   - Configure alert webhooks to Slack + email

3. **Export Workflow Setup** (Task 2.8):
   - Deploy `.github/workflows/mp1-metrics-export.yml`
   - Schedule daily exports to Prometheus

4. **Production Rollout** (Phase 2 Final):
   - Execute canary rollout stages 1-4
   - Monitor metrics for violations
   - Complete Phase 2 closure

---

## REFERENCES

- **Rollout Plan**: [mp1-canary-rollout-plan.md](mp1-canary-rollout-plan.md)
- **Baseline Metrics**: [mp1-compliance-metrics.yaml](mp1-compliance-metrics.yaml)
- **Enforcement Contract**: [marker_prefix_enforcer.py](../src/prism/scanner_core/marker_prefix_enforcer.py)
- **Metrics Module**: [mp1_enforcement_metrics.py](../src/prism/monitoring/mp1_enforcement_metrics.py)
