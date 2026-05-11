# Tier 1 Resilient Execution Strategy

**Objective**: Fix all 261 g84 findings using Tier 1 (Claude Haiku 4.5) with smart rollback & retry  
**Strategy**: Cost-optimized with safety valves  
**Retry Limit**: 3 attempts per finding  
**Escalation**: Tier 2 on 4th failure + micro-swarm investigation  
**Status**: ✅ READY TO EXECUTE

---

## Execution Philosophy

**Primary**: Maximize Tier 1 success (233 findings/$ is excellent ROI)  
**Resilience**: Rollback + re-plan on each failure  
**Investigation**: Micro-swarm only when needed (ambiguous findings)  
**Learning**: Track which findings need Tier 2 (pattern analysis for future)

---

## Wave Execution Order (Tier 1 Priority)

All 6 waves executed in priority order using **Haiku 4.5 (Tier 1, 0.33x)**:

| Wave | Severity | Count | Tier 1 Confidence | Strategy |
|------|----------|-------|---|---|
| Wave 1 | CRITICAL | 33 | 75-85% | Try Tier 1; escalate if pattern emerges |
| Wave 2 | HIGH (DI/Arch) | 59 | 60-70% | Try Tier 1; DI issues likely need escalation |
| Wave 3 | HIGH (Extract) | 29 | 85% | High Tier 1 confidence (parsing/extraction) |
| Wave 4 | HIGH (Output) | 1 | 90% | Single mechanical fix |
| Wave 5 | MEDIUM (Arch) | 41 | 70-80% | Try Tier 1; escalate complex issues |
| Wave 6 | MEDIUM/LOW | 112 | 90%+ | Cleanup/polish → Tier 1 ideal |

**Total**: 275 findings through Tier 1 with safety valves

---

## Per-Finding Retry Protocol

### Attempt 1: Tier 1 (Haiku 4.5)

```
dispatch_builder(
    findings: [finding_id],
    model: query_model_router(
        task_type="implementation",
        cost_priority="low",  # Force Tier 1
        focus_area="[category]"
    ),
    retry_count: 0
)
```

**Outcome**:
- ✅ **PASS**: Move to next finding
- ❌ **FAIL**: → Attempt 2 (re-plan + same model)

---

### Attempt 2: Tier 1 + Re-Planning

**On failure**:
1. **Rollback**: Revert all changes from Attempt 1
2. **Re-plan**: Update artifact with failure reason + revised approach
3. **Dispatch**: Same builder, **new plan** (same model)

```yaml
finding_status:
  id: GILF-XXX
  attempt: 2
  previous_failure: "[error from attempt 1]"
  new_approach: "[revised strategy]"
  retry_count: 1
```

**Outcome**:
- ✅ **PASS**: Move to next finding
- ❌ **FAIL**: → Attempt 3

---

### Attempt 3: Tier 1 + Micro-Swarm Investigation

**On failure again**:
1. **Investigate**: Dispatch `mutl3y-probe` with single finding
   - Probe scope: imports, test coverage, ownership
   - Duration: 15 min max
2. **Document**: Capture investigation findings
3. **Redispatch**: Builder with investigation insights (same Tier 1)

```yaml
finding_status:
  id: GILF-XXX
  attempt: 3
  investigation: "[micro-swarm findings]"
  final_approach: "[insights-informed strategy]"
  retry_count: 2
```

**Outcome**:
- ✅ **PASS**: Move to next finding
- ❌ **FAIL**: → Defer to Tier 2

---

### Defer to Tier 2 (After 3 Failures)

**On 4th failure** (3 unsuccessful retries):
1. **Mark**: Status = `DEFERRED_TIER_2`
2. **Reason**: Document why Tier 1 couldn't fix
3. **Queue**: Add to Tier 2 remediation batch (run after all Tier 1 complete)

```yaml
finding_status:
  id: GILF-XXX
  status: "DEFERRED_TIER_2"
  tier_1_attempts: 3
  defer_reason: "[consolidated reason from all 3 attempts]"
  needed_reasoning: "[what Tier 2 must provide]"
```

---

## Tracking Artifacts

### Per-Wave Execution Log

```
/raid5/source/test/prism/docs/plan/g84-remediation-mutl3y-cycle-20260509/
├── wave_1_tier1_execution.yaml      # Attempt counts, pass/fail, defer list
├── wave_2_tier1_execution.yaml
├── ...
└── tier1_summary.yaml               # Aggregate: pass count, defer count, cost
```

### Tier 1 Ledger (Cumulative)

```yaml
metadata:
  total_findings: 261
  tier_1_mode: true
  retry_limit: 3

statistics:
  pass_wave1: 28/33
  defer_wave1: 5/33
  pass_wave2: 52/59
  defer_wave2: 7/59
  # ... etc
  
  total_pass: 250/261
  total_defer: 11/261
  cost_saved: ~0.008  # vs Tier 2 all

deferred_findings:
  - GILF-X001: "Circular DI dependency"
  - GILF-X002: "Complex async event flow"
  # ... up to 11 items
```

---

## Success Criteria (Tier 1 Phase)

✅ **Attempt pass rate**: >= 85% (target 220+/261 on first attempt)  
✅ **Retry success rate**: >= 60% on attempts 2-3 (target 25+/41 failing initially)  
✅ **Deferred count**: <= 10 findings (target <4% need Tier 2)  
✅ **Cost efficiency**: Final cost ~0.008-0.012 (vs 0.025 if all Tier 2)

---

## Escalation Triggers (Auto Defer)

If **more than 15% of a wave** fails Tier 1 after 3 retries:
- Don't keep retrying that wave
- Escalate entire wave to Tier 2 investigation batch
- Example: Wave 2 has 59 findings, if 9+ defer → defer all 59 for Tier 2 specialist

---

## Tier 2 Batch (After All Tier 1 Complete)

Once Tier 1 completes on all 6 waves:

1. **Assess deferred findings**: Group by root cause (DI, concurrency, async, etc.)
2. **Dispatch Tier 2 specialist**: `mutl3y-builder` with full reasoning
   - Model: `query_model_router(cost_priority="balanced")`
   - Expected: Claude Sonnet 4.5 (1x)
3. **Batch size**: Run in 1-2 focused waves (not individual findings)

---

## Validation & Closure

### After All Tier 1 + Any Tier 2 Complete

**Phase 6 Gate**:
```bash
pytest -v src/prism/tests/       # All pass
ruff check src/prism/             # 0 violations
black --check src/prism/          # Formatted
mypy src/prism/ > /tmp/mypy.out   # No regressions
```

**Phase 7 Closure**:
- Verify all 261 findings remediated (defer count = 0 or < 5)
- Document Tier 1 effectiveness metrics
- Lessons for future remediation cycles

---

## Command Flow

```bash
# 1. Start Wave 1 Tier 1
runSubagent(
    name="mutl3y-builder",
    wave="wave_1",
    findings_file="docs/plan/g84-remediation-mutl3y-cycle-20260509/wave_1_tier1_execution.yaml",
    model="haiku_4_5",  # Tier 1 forced
    retry_limit=3,
    rollback_on_failure=true
)

# 2. Continue Waves 2-6 (same pattern, sequential)

# 3. After all Tier 1 complete, if defer_count > 0:
runSubagent(
    name="mutl3y-builder",
    wave="tier2_deferred_batch",
    findings_file="docs/plan/g84-remediation-mutl3y-cycle-20260509/tier1_deferred.yaml",
    model="sonnet_4_5",  # Tier 2 for escalated items
    retry_limit=1  # No retry needed, Tier 2 has full reasoning
)

# 4. Validation & Closure (standard gates)
```

---

## Expected Outcomes

### Best Case (Optimistic)
- Tier 1 success: 250+/261 findings (95%+)
- Deferred: 0-5 findings
- Total cost: ~0.008 (massive savings)
- Tier 2 run: Trivial (1 hour, 5 findings)

### Realistic Case (Balanced)
- Tier 1 success: 220+/261 findings (84%+)
- Deferred: 5-15 findings
- Total cost: ~0.010-0.012
- Tier 2 run: Medium (2-3 hours, 15 findings)

### Tough Case (Conservative)
- Tier 1 success: 180+/261 findings (69%+)
- Deferred: 40-80 findings (mostly Wave 1-2 complexity)
- Total cost: ~0.012-0.015 (still cheaper than all Tier 2)
- Tier 2 run: Significant (8+ hours, 80 findings)
- **Trigger**: Full Tier 2 specialist team for DI/architecture findings

---

## Key Decisions

🎯 **Decision 1**: Try Tier 1 first (cost optimization primary)  
🎯 **Decision 2**: 3 retries per finding (allows debugging + re-planning)  
🎯 **Decision 3**: Micro-swarm only on attempt 3 (reserve for ambiguous cases)  
🎯 **Decision 4**: Auto-defer after 3 failures (respect resource limits)  
🎯 **Decision 5**: Batch Tier 2 findings (not individual escalations)

---

## Launch Checklist

Before starting Wave 1:

- [ ] Wave plan verified: 6 waves, 261 findings, 275 in artifact
- [ ] Model-router skill working (test query with cost_priority="low")
- [ ] Rollback mechanism ready (revert last commit on failure)
- [ ] Ledger template created (tier1_summary.yaml)
- [ ] First builder ready (mutl3y-builder with Tier 1 config)
- [ ] Micro-swarm ready (mutl3y-probe on standby)

✅ **Status**: Ready to execute

---

## Start Execution

**Command**: Dispatch Wave 1 builder with Tier 1 + retry strategy

**Expected**: Attempt pass rate 75-95%, deferred <= 10 findings, total cost 0.008-0.015
