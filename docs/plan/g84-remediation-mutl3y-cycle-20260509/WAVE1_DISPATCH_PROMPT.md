# Wave 1 Tier 1 Builder Dispatch

**Wave**: wave_1_critical (33 CRITICAL findings)  
**Model**: Claude Haiku 4.5 (via model-router with cost_priority="low")  
**Tier**: TIER_1 (0.33x cost multiplier)  
**Retry Strategy**: 3 attempts per finding + rollback + re-plan

---

## Dispatch Command

```python
query_model_router(
    task_type="implementation",
    cost_priority="low",
    focus_area="architecture"
)
# Expected: Claude Haiku 4.5 (Tier 1, 0.33x)

dispatch_builder(
    agent_name="mutl3y-builder",
    task_id="wave-1-tier1-critical",
    findings_file="/raid5/source/test/prism/docs/plan/g84-remediation-mutl3y-cycle-20260509/wave_1_tier1_execution.yaml",
    model="Claude Haiku 4.5",
    tier="TIER_1",
    retry_limit=3,
    rollback_on_failure=True,
    strategy="tier1_resilient"
)
```

---

## Builder Instructions

### Phase 1: Fix CRITICAL Findings (Attempt 1)

1. Read Wave 1 findings from execution config
2. For each finding:
   - Understand the issue (read fix_suggestion)
   - Implement fix in code
   - Write/update tests
   - Run local validation
3. Record attempt result:
   - **PASS**: Update status → "FIXED", attempt[1] → { status: "SUCCESS" }
   - **FAIL**: Update attempt[1] → { status: "FAILED", reason: "[error]" }

### Phase 2: Retry Failed Findings (Attempt 2)

1. Identify failed findings from Attempt 1
2. For each failed finding:
   - **Re-plan**: Read failure reason, devise new approach
   - Document new strategy in attempt[2]
   - Rollback: `git checkout -- [files]`
   - Implement new strategy
3. Record results

### Phase 3: Investigate & Final Attempt (Attempt 3)

For findings still failing after Attempt 2:
1. **Investigate** (if time permits):
   - Check imports and dependencies
   - Review related test coverage
   - Analyze ownership/responsibility
2. **Document findings** in investigation field
3. **Final attempt** with investigation insights
4. Record results

### Phase 4: Defer to Tier 2

For findings failing all 3 attempts:
1. Update final_status → "DEFERRED_TIER_2"
2. Document consolidated failure reason
3. Mark for Tier 2 batch processing

---

## Success Metrics (Wave 1)

✅ **Attempt 1**: Target 75-95% pass rate (25-31/33 findings)  
✅ **Attempt 2**: Target 60% success on failures (4-6 additional fixed)  
✅ **Attempt 3**: Target 50% success on remaining (0-3 additional fixed)  
✅ **Final Defer**: Target <= 5 findings need Tier 2 (max 15%)

**Expected Wave 1 Outcome**: 28-31/33 FIXED, 2-5 deferred

---

## After Wave 1

Once Wave 1 complete (all 33 findings have final_status):

1. **Validate**: Run pytest to ensure fixes don't break tests
2. **Next**: Dispatch Wave 2 (59 HIGH findings, DI/Architecture domain)
3. **Continue**: Waves 3-6 sequentially (same Tier 1 strategy)
4. **Tier 2 Batch**: After all 6 waves, process deferred findings with Tier 2

---

## Cost Tracking

- Wave 1: 33 findings × ~0.005 per attempt = ~0.005-0.015 (3 attempts max)
- **Total Wave 1 cost**: 0.008-0.015 (vs 0.010 if all Tier 2)

---

## File Locations

- **Findings**: `/raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/g84-findings-consolidated.yaml` (filter CRITICAL severity)
- **Execution Config**: `/raid5/source/test/prism/docs/plan/g84-remediation-mutl3y-cycle-20260509/wave_1_tier1_execution.yaml` (track attempts)
- **Strategy Guide**: `/raid5/source/test/prism/docs/plan/g84-remediation-mutl3y-cycle-20260509/TIER1_RESILIENT_STRATEGY.md` (retry protocol)
- **Code**: `/raid5/source/test/prism/src/prism/` (target for fixes)

---

## Ready to Dispatch

✅ Wave 1 config created  
✅ 33 CRITICAL findings extracted  
✅ Retry slots initialized  
✅ Model (Haiku 4.5) confirmed  
✅ Rollback + re-plan enabled

**Next**: Dispatch builder via mutl3y-foreman skill
