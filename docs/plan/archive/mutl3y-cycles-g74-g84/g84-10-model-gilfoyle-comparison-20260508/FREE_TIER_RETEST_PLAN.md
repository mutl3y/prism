# Free-Tier Retest Plan — Unlimited Tokens + Improved Prompt

**Date:** 2026-05-08  
**Objective:** Validate whether removing token limits + better prompting improves free-tier coverage to near-Tier 1 levels

---

## Hypothesis

Free-tier models (GPT-4o, GPT-4.1, GPT-5 mini, Raptor mini) with:
- ✅ **No token limits** (vs original 800 tokens)
- ✅ **Better prompt** (emphasize thoroughness, cite focus areas)
- ✅ **Explicit focus areas** (ownership, concurrency, type safety)

Will match or exceed Tier 1 (Haiku 4.5) coverage in:
- Finding count (9+ findings)
- CRITICAL discovery (find TOCTOU race like Haiku did)
- Quality score (85+/100)

**Cost:** FREE (all Tier 0)
**Savings vs Tier 1 default:** 100% (currently using Tier 1 Haiku at $0.001)

---

## Original vs Improved Prompt

### Original Prompt (800 tokens, generic)

```
You are Gilfoyle. Code review prism/src/prism/scanner_core/ with your usual brutal honesty.

Context: Comprehensive model comparison test. Report which model you're running on.

Scope: scanner_core/ only
Focus: Architecture, type safety, ownership, god-level findings only

Return: 5-10 highest-impact findings (CRITICAL/HIGH only)
Format: YAML with severity, category, location, issue, root_cause, impact

Constraint: 800 tokens max (we'll evaluate model quality).
```

### Improved Prompt (Unlimited, thorough emphasis)

```
You are Gilfoyle. Conduct a COMPREHENSIVE code review of prism/src/prism/scanner_core/ with brutal honesty and MAXIMUM DEPTH.

Context: We previously tested 13 models and found significant blind spots. This retest validates whether better prompting + unlimited depth can improve free-tier model findings.

**Key areas where previous models diverged** (guide your attention):
1. **Concurrency bugs** — Haiku 4.5 found TOCTOU race in _get_prepared_policy_bundle that ALL higher-cost tiers missed
2. **Type safety illusions** — TypeGuard type guards claiming identity at compile-time but lying at runtime
3. **Cache-key collisions** — Opaque types collapsing to same hash, causing silent data corruption
4. **Ownership fragmentation** — Policy logic scattered across 4+ modules with unclear accountability
5. **Validation bypass** — Factory overrides skip validation while registry path enforces it

**Scope**: scanner_core/ ONLY. Leave other layers out of scope.

**Critical constraint**: You must investigate ALL 11 modules in scanner_core/, not just surface-level:
- di.py (15 focus points: DI god-object, lazy imports, factory defaults)
- scanner_context.py (12 focus points: ownership, blocker facts, validation)
- task_extract_adapters.py (10 focus points: marker-prefix ownership, policy reads)
- variable_discovery.py (8 focus points: prepared_policy fallback, plugin resolution)
- execution_request_builder.py (7 focus points: state smuggling, request building)
- feature_detector.py (6 focus points: policy injection, runtime resolution)
- scan_request.py (8 focus points: normalization, prepared_policy shaping)
- scan_cache.py (5 focus points: cache semantics, key collisions)
- di_helpers.py (5 focus points: shared DI patterns, duplicate logic)
- events.py (4 focus points: error handling, side effects)
- protocols_runtime.py (3 focus points: type safety, protocol compliance)

**Return format**: 
```yaml
model_used: [exact model name]
tier_estimate: [your estimate]
prompt_unlimited: true
module_coverage: [number of modules analyzed]

findings:
  - id: GILF-FREETIER-{NN}
    severity: CRITICAL|HIGH|MEDIUM
    category: Concurrency|Type|Ownership|Validation|Architecture|Performance
    module: [module name]
    location: file:line or file:function
    issue: (1-2 sentence description)
    root_cause: (3-5 sentence deep analysis)
    impact: (business/system impact)
    remediation: (specific fix or pattern)
    confidence: 90%|75%|60%
```

**Requirements**:
- MINIMUM 10 findings (aim for 15+, unlimited tokens available)
- Report what model you're actually using
- Distinguish between: tier-exclusive issues vs convergent issues vs potentially new discoveries
- If you find a concurrency bug, escalate to CRITICAL even if it seems low-probability
- If you find a type safety gap, investigate its runtime implications

**Success criteria**:
- Find the TOCTOU race (or explain why you don't think it exists)
- Find at least 2-3 ownership fragmentation patterns
- Find at least 1 type safety or validation bypass
- Coverage of 8+ modules (out of 11)

Do your worst. Be thorough. No token limits.
```

---

## Test Plan

### Models to Retest (Free Tier Only)

1. **GPT-4o** (current score: 5 findings, 60/100)
   - Original: 5 findings, narrow scope (scanner_context only)
   - Expected improvement: 12+ findings with thorough prompting
   - Why: Stopped early, likely had more to say

2. **GPT-4.1** (current score: 7 findings, 78/100)
   - Original: 7 findings, good coverage
   - Expected improvement: 10+ findings, find ownership fragmentation
   - Why: Solid foundation, better prompting should unlock deeper patterns

3. **GPT-5 mini** (current score: 7 findings, 82/100)
   - Original: 7 findings (2 CRITICAL, 5 HIGH), DI bootstrap issues
   - Expected improvement: 12+ findings, find TOCTOU or cache bugs
   - Why: Already strong, unlimited tokens should find harder patterns

4. **Raptor mini** (current score: 7 findings, 80/100)
   - Original: 7 findings (1 CRITICAL, 6 HIGH), unique factory override bypass
   - Expected improvement: 11+ findings, find validation gaps
   - Why: Found unique bug, thorough prompting should find more

---

## Success Metrics

### Metric 1: Finding Count Improvement

| Model | Original | Expected | Success Criterion |
|-------|----------|----------|-------------------|
| GPT-4o | 5 | 12+ | +140% |
| GPT-4.1 | 7 | 11+ | +57% |
| GPT-5 mini | 7 | 12+ | +71% |
| Raptor mini | 7 | 11+ | +57% |
| **Average** | **6.5** | **11.5** | **+77%** |

**Target:** Average of +70% finding count increase with better prompting

### Metric 2: Critical Bug Discovery

- **Original:** Free tier found: 2 CRITICAL (GPT-5 mini) + 1 CRITICAL (Raptor)
- **Target:** Free tier finds: TOCTOU race (Haiku originally found), cache collision, or TypeGuard lie
- **Success:** At least 1 new CRITICAL finding across 4 models

### Metric 3: Coverage Breadth

- **Original:** Most models covered 4-6 modules
- **Target:** All models cover 8+ modules
- **Success:** Average module coverage 9+/11

### Metric 4: Tier-Exclusive Issue Detection

- **Target:** Free tier detects at least 1-2 findings that were originally "Tier 2 only" or "Tier 4 only"
- **Why:** Validates that prompt improvement can compensate for model capability limits

### Metric 5: Quality Score Improvement

| Model | Original Score | Expected Score | Delta |
|-------|----------------|-----------------|-------|
| GPT-4o | 60/100 | 75/100 | +15 |
| GPT-4.1 | 78/100 | 85/100 | +7 |
| GPT-5 mini | 82/100 | 88/100 | +6 |
| Raptor mini | 80/100 | 86/100 | +6 |

**Target:** Average quality score +8.5 points → 82.3/100 for free tier (approaching Haiku's 88/100)

---

## Expected Outcomes

### If Hypothesis is CORRECT (High probability: 70%)

- Free tier with better prompt achieves 82-85/100 quality
- Retest matches original Tier 1 (Haiku 4.5) finding count (9 findings)
- Free tier finds TOCTOU race or similar critical concurrency bug
- **Implication:** Free tier is adequate default, only escalate to Tier 1 for edge cases

### If Hypothesis is INCORRECT (Lower probability: 30%)

- Free tier plateaus at 70-75/100 even with unlimited tokens
- Doesn't find TOCTOU race or other critical bugs
- Only finds convergent findings (which 5+ models already found)
- **Implication:** Tier 1 (Haiku) is necessary for critical issues, free tier is triage-only

---

## Execution Plan

### Phase 1: Baseline Verification (5 min)
- [ ] Confirm original scores for each free-tier model
- [ ] Document original finding list for comparison

### Phase 2: Retest Dispatch (20 min)
- [ ] Run GPT-4o with improved unlimited prompt
- [ ] Run GPT-4.1 with improved unlimited prompt
- [ ] Run GPT-5 mini with improved unlimited prompt
- [ ] Run Raptor mini with improved unlimited prompt

### Phase 3: Analysis (30 min)
- [ ] Count findings per model, compare to original
- [ ] Identify NEW findings (not in original run)
- [ ] Grade finding quality vs original
- [ ] Map findings to convergent/tier-exclusive/new categories

### Phase 4: Reporting (15 min)
- [ ] Generate retest findings document
- [ ] Produce improvement metrics table
- [ ] Deliver recommendations for model strategy update

**Total time:** ~70 minutes

---

## Follow-Up Decision Tree

### If Free Tier Retest Succeeds (82+/100, finds TOCTOU)

**New recommendation:**
- **Tier 0 (FREE)** → Default for Phase 0 + Phase 3 + Phase 5
- **Tier 1 (Haiku)** → Escalate only for security-critical modules (scanner_context, di.py)
- **Tier 2 (GPT-5.4)** → Standard PR reviews, refactor planning
- **Tier 4 (Opus)** → Architecture decisions only

**Cost impact:** $0.07 → $0.02/review (additional 85% savings) 🎉

### If Free Tier Retest Fails (<75/100, doesn't find TOCTOU)

**Recommendation stays:**
- **Tier 1 (Haiku)** → Keep as default
- Free tier → Use for non-critical discovery only
- No change to three-tier strategy

---

## Questions This Retest Answers

1. **Can prompt affect output positively?** → YES/NO evidence
2. **Do token limits constrain free-tier models?** → YES if retest shows massive improvement
3. **Is 800 tokens too restrictive?** → YES if unlimited prompt unlocks critical bugs
4. **Can free tier match Tier 1 quality?** → YES if retest achieves 85+/100 and finds TOCTOU

---

## Next Steps (After Retest Complete)

1. Update [CONVERGENCE_ANALYSIS.md](CONVERGENCE_ANALYSIS.md) with retest findings
2. Create [FREE_TIER_RETEST_RESULTS.md](FREE_TIER_RETEST_RESULTS.md) with metrics
3. Update model dispatch strategy if free tier succeeds
4. Store new "unlimited prompt improves coverage" fact in repo memory

---

**Status:** Ready to execute  
**Cost:** FREE (all Tier 0)  
**Timeline:** ~70 minutes to completion  
**Expected impact:** Potentially unlock additional 85% cost savings if free tier matches Tier 1 quality
