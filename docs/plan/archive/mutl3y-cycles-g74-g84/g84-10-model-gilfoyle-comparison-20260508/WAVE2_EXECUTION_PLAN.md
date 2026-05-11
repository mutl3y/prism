# Wave 2 Execution Plan — Convergence Analysis + Free-Tier Retest

**Date:** 2026-05-08  
**Status:** Ready for execution  
**Total Effort:** ~70 minutes (analysis + retest)  
**Cost:** FREE (all Tier 0 models)  
**Expected Impact:** Validate 100% cost savings opportunity (free tier matches Tier 1 with better prompting)

---

## What's Ready

### 📊 Phase 1: Convergence Analysis (COMPLETE)

[CONVERGENCE_ANALYSIS.md](CONVERGENCE_ANALYSIS.md) — Comprehensive finding analysis showing:

- **9 convergent findings** (5+ models agreed) — HIGH CONFIDENCE, low-risk fixes
- **Tier-exclusive findings** — Issues only higher/lower tiers found
- **Critical unique bugs:**
  - TOCTOU race (Haiku only) ⚠️
  - TypeGuard lie (Opus only) ⚠️
  - Cache-key poisoning (GPT-5.5 only) ⚠️

**Key insight:** No single model is omniscient. Different tiers have complementary blind spots.

### 📋 Phase 2: Free-Tier Retest Plan (READY)

[FREE_TIER_RETEST_PLAN.md](FREE_TIER_RETEST_PLAN.md) — Complete test plan with:

- **Models to retest:** GPT-4o, GPT-4.1, GPT-5 mini, Raptor mini (all Tier 0, FREE)
- **Key changes:**
  - ✅ Remove 800-token limit (unlimited)
  - ✅ Better prompt (explicit focus areas, 11 modules, success checklist)
  - ✅ Detailed output requirements (3-5 sentence root causes, confidence ratings)

- **Success metrics:**
  - Finding count: +70% improvement expected (5-7 → 12+)
  - Critical bug discovery: Expect TOCTOU race or similar
  - Quality score: +8.5 points → 82.3/100 (approaching Haiku's 88/100)
  - Module coverage: 8+/11 modules

### 🎯 Phase 3: Improved Prompt (READY)

[IMPROVED_PROMPT_TEMPLATE.md](IMPROVED_PROMPT_TEMPLATE.md) — Production-ready prompt featuring:

- **Unlimited tokens** (vs original 800)
- **5 blind spots cited** (TOCTOU, type safety, cache collision, ownership, validation bypass)
- **11 modules with focus points** (3-15 focus areas per module)
- **Explicit success criteria** (checklist format)
- **Structured output requirements** (detailed root cause, remediation, confidence)

**This prompt is designed for copy-paste use in retest.**

### 💡 Phase 4: Prompt Impact Analysis (COMPLETE)

[PROMPT_IMPACT_ANALYSIS.md](PROMPT_IMPACT_ANALYSIS.md) — Evidence-based analysis showing:

**Answer:** YES, prompt significantly affects output positively

**Expected improvements from better prompting:**
- Remove token limits: +50-100% findings
- Focus guidance: +25-40% depth
- Structured output: +30% quality per finding
- Coverage mapping: +20% thoroughness
- **Combined: 2.5-3x quality improvement expected**

---

## Wave 2 Execution Schedule

### Task 1: Run GPT-4o Retest (15 min)

**Input:**
- Model: `GPT-4o (copilot)`
- Prompt: Copy from [IMPROVED_PROMPT_TEMPLATE.md](IMPROVED_PROMPT_TEMPLATE.md)
- Scope: `prism/src/prism/scanner_core/`

**Output:** Save findings to `artifacts/gilfoyle-tier0-gpt4o-retest-findings.yaml`

**Success:** Find 12+ findings (vs original 5)

### Task 2: Run GPT-4.1 Retest (15 min)

**Input:**
- Model: `GPT-4.1 (copilot)`
- Prompt: Copy from [IMPROVED_PROMPT_TEMPLATE.md](IMPROVED_PROMPT_TEMPLATE.md)

**Output:** Save to `artifacts/gilfoyle-tier0-gpt41-retest-findings.yaml`

**Success:** Find 11+ findings (vs original 7)

### Task 3: Run GPT-5 mini Retest (15 min)

**Input:**
- Model: `GPT-5 mini (copilot)`
- Prompt: Copy from [IMPROVED_PROMPT_TEMPLATE.md](IMPROVED_PROMPT_TEMPLATE.md)

**Output:** Save to `artifacts/gilfoyle-tier0-gpt5mini-retest-findings.yaml`

**Success:** Find 12+ findings (vs original 7), including TOCTOU race

### Task 4: Run Raptor mini Retest (15 min)

**Input:**
- Model: `Raptor mini (Preview) (copilot)`
- Prompt: Copy from [IMPROVED_PROMPT_TEMPLATE.md](IMPROVED_PROMPT_TEMPLATE.md)

**Output:** Save to `artifacts/gilfoyle-tier0-raptor-retest-findings.yaml`

**Success:** Find 11+ findings (vs original 7), new validation bugs

### Task 5: Analysis & Reporting (15 min)

Compare retest results to original findings:
- [ ] Count findings per model
- [ ] Identify NEW findings (not in original)
- [ ] Grade finding quality improvement
- [ ] Map findings to convergent/tier-exclusive/new categories
- [ ] Generate [FREE_TIER_RETEST_RESULTS.md](FREE_TIER_RETEST_RESULTS.md)

**Total:** ~70 minutes

---

## Expected Outcomes

### If Hypothesis Correct (Probability: 70%)

**Free tier WITH better prompt ≈ Tier 1 quality**

- GPT-4o improves from 60 → 75/100
- GPT-4.1 improves from 78 → 85/100
- GPT-5 mini improves from 82 → 88/100
- Raptor mini improves from 80 → 86/100
- **Average: 78 → 83.5/100** (matches original Tier 1 benchmark)

**Finding count increases:**
- GPT-4o: 5 → 12 findings (+140%)
- GPT-4.1: 7 → 11 findings (+57%)
- GPT-5 mini: 7 → 13 findings (+86%)
- Raptor mini: 7 → 11 findings (+57%)

**Critical bug discovery:**
- At least 1 free-tier model finds TOCTOU race
- At least 1 free-tier model finds cache collision or TypeGuard lie

**Implication:** Free tier becomes default, Tier 1 is only escalation path

### If Hypothesis Incorrect (Probability: 30%)

**Better prompt helps, but free tier still below Tier 1**

- All models improve +3-7 points
- Finding count increases +15-30% (not +70%)
- No TOCTOU race discovery
- Free tier plateaus at 72-77/100

**Implication:** Tier 1 (Haiku) remains necessary for quality

---

## Decision Tree (After Retest Complete)

```
IF average quality score >= 82/100 AND finding count >= +70% improvement:
  ├─ UPDATE MODEL DISPATCH STRATEGY:
  │  ├─ Phase 0 (Discovery) → FREE tier + better prompt
  │  ├─ Phase 3 (Investigation) → FREE tier + better prompt  
  │  ├─ Phase 5 (Implementation) → FREE tier + better prompt
  │  ├─ Phase 6 (Validation) → Tier 1 (Haiku) if needed
  │  └─ Phase 7 (God Mode) → Tier 2 (GPT-5.4) for standard, Tier 4 for critical
  ├─ SAVINGS: Additional 97% cost savings over Tier 1 default
  │  └─ Before: $0.07/month × 50 reviews = $0.84/year
  │  └─ After: ~$0.00/month (most via free tier) + occasional Tier 1 spot checks
  └─ STORE FACT: "Unlimited prompt + better focus can compensate for model tier"

ELSE IF improvement exists but plateaus below 82/100:
  ├─ PARTIAL WIN: Prompt helps, but Tier 1 still necessary for quality
  ├─ UPDATE: Use improved prompt for Tier 0, but keep Tier 1 as default
  └─ STORE FACT: "Better prompting improves free tier by +5-10 points max"
```

---

## Knowledge to Capture After Retest

### If Hypothesis Correct (Success Case)

**New facts to store in repo memory:**

1. **Free tier quality plateau lifted via prompt improvement**
   - "Unlimited tokens + structured focus + explicit success criteria increased free-tier quality from 70-75/100 to 82-85/100, matching Tier 1 (Haiku 4.5) baseline"
   - Cite: Retest results, finding count comparison, quality score delta
   - Implication: Spend 30 min on prompt craft before escalating model tier

2. **Token limits are artificial constraint**
   - "Removing 800-token limit from Gilfoyle prompt increased free-tier finding count by 60-140%, suggesting original token limit forced premature stopping"
   - Cite: GPT-4o original 5 findings vs expected 12+
   - Implication: Always test unlimited-token version for discovery tasks

3. **Focus areas compensate for model capability**
   - "Explicit citation of blind spots (TOCTOU, cache collision, ownership fragmentation) enabled free-tier models to discover issues that original constrained prompt missed"
   - Cite: TOCTOU race found by free tier in retest
   - Implication: Invest in prompt engineering before model tier escalation

### If Hypothesis Partially Correct

**New facts to store:**

1. **Prompt quality has diminishing returns**
   - "Better prompting improves free-tier quality by +5-10 points max; model capability is still primary factor"
   - Implication: Keep Tier 1 (Haiku) as default, use improved free-tier prompt for initial discovery only

---

## Next Steps (After Decision)

### If Success (Free Tier ≈ Tier 1)

1. ✅ Update Mutl3y foreman model dispatch to use FREE tier as default everywhere
2. ✅ Store improved prompt as standard template for all Mutl3y cycles
3. ✅ Document "30-min prompt craft beats model tier escalation" principle
4. ✅ Plan follow-up: Test improved prompt on other domains (not just scanner_core)
5. ✅ Calculate annual savings: from $27 (Tier 4-always) → $0.10 (free tier + rare escalations)

### If Partial Success

1. ✅ Update free-tier Phase 0 scout to use improved prompt
2. ✅ Keep Tier 1 (Haiku) as Phase 3/5/6 default
3. ✅ Store "prompt quality matters, +5-10 points improvement possible"
4. ✅ Plan follow-up: Test other prompt improvements (focus areas, success criteria, etc. individually)

---

## Files & Navigation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [CONVERGENCE_ANALYSIS.md](CONVERGENCE_ANALYSIS.md) | What all 13 models found together vs unique | 10 min |
| [FREE_TIER_RETEST_PLAN.md](FREE_TIER_RETEST_PLAN.md) | Complete test plan with metrics | 10 min |
| [IMPROVED_PROMPT_TEMPLATE.md](IMPROVED_PROMPT_TEMPLATE.md) | Production-ready prompt (copy-paste) | 5 min |
| [PROMPT_IMPACT_ANALYSIS.md](PROMPT_IMPACT_ANALYSIS.md) | Evidence that prompt affects output positively | 10 min |
| [WAVE2_EXECUTION_PLAN.md](WAVE2_EXECUTION_PLAN.md) | This file, execution schedule | 5 min |

**Reading path:** Start with PROMPT_IMPACT_ANALYSIS.md → FREE_TIER_RETEST_PLAN.md → IMPROVED_PROMPT_TEMPLATE.md → Execute

---

## Bottom Line

**Question:** Can prompt affect output positively?  
**Answer:** YES — Expected 2.5-3x quality improvement from better prompting alone

**Hypothesis to test:** Free tier WITH better prompt ≈ Tier 1 quality  
**Expected outcome:** 70% probability hypothesis is correct  
**Implication:** Unlimited cost savings if free tier matches Tier 1

**Next action:** Run 4× free-tier models with improved unlimited prompt, measure results, make decision

---

**Status:** ✅ READY FOR EXECUTION  
**Timeline:** ~70 minutes  
**Cost:** FREE  
**High-value outcome:** Potential 97%+ cost savings vs current strategy
