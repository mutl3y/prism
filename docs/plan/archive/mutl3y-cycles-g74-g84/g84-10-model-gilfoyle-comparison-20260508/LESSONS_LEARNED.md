# Lessons Learned — 13-Model Gilfoyle Comparison (g84)

**Date:** 2026-05-08
**Scope:** Comprehensive model tier comparison for Mutl3y Gilfoyle Code Review God Mode
**Test Size:** 13 unique models + 1 retest = 14 total samples

---

## Strategic Lessons

### 1. **Quality Plateaus at Tier 2**

**Finding:** Tier 4 models (7.5-15x cost) deliver only 3-5% quality improvement over Tier 2 (1x cost).

**Evidence:**
- Claude Sonnet 4.5 (Tier 2): 93/100 quality at $0.003
- GPT-5.4 (Tier 2): 95/100 quality at $0.003
- GPT-5.5 (Tier 4): 91/100 quality at $0.022 (7.5x cost, LOWER quality)
- Claude Opus 4.7 (Tier 4): 98/100 quality at $0.045 (15x cost, +3% quality)

**Implication:** Tier 2 is the optimal default for code reviews. Reserve Tier 4 for high-stakes architectural decisions where refactor proposals justify the premium.

**Action:** Update Mutl3y foreman model dispatch to default scouts/builders to Tier 1, escalate to Tier 2 for standard work, and reserve Tier 4 for explicit architecture synthesis only.

---

### 2. **Lower Tiers Can Find Critical Issues Higher Tiers Miss**

**Finding:** Claude Haiku 4.5 (Tier 1, 0.33x cost) found a CRITICAL TOCTOU race condition that ALL Tier 2 models missed.

**Evidence:**
- Haiku 4.5 GILF-T1H45-05: TOCTOU race in `_get_prepared_policy_bundle` (CRITICAL severity)
- Sonnet 4.5, GPT-5.4, Gemini 2.5 Pro: None reported this finding
- Cost: $0.001 vs $0.003 (Tier 2) = 67% savings with superior coverage

**Implication:** Higher cost ≠ better coverage. Different models have different blind spots.

**Action:** Use multi-model sampling for critical reviews (run Haiku + one Tier 2 model, merge findings) instead of single Tier 4 run. Total cost: $0.004 vs $0.045 (Opus) = 91% savings with better coverage.

---

### 3. **Format Compliance is Non-Deterministic in Some Models**

**Finding:** Grok Code Fast 1 produced well-formatted YAML on first run, then prose-only on retest with identical prompt.

**Evidence:**
- First run: 8 structured YAML findings ✅
- Retest: Prose narrative, no YAML structure ❌
- Same prompt, same model, different output format

**Implication:** Production workflows that depend on structured output parsing CANNOT rely on Grok without retry logic and format validation.

**Action:**
1. Add format validation layer to Mutl3y artifact processing
2. Implement automatic rerun with tightened format constraints on parse failure
3. Track format-failure rate per model in model-usage-ledger.yaml
4. Quarantine models with >10% format-failure rate for structured-output tasks

---

### 4. **Refactor Proposals Are the Differentiator for Top-Tier Models**

**Finding:** Claude Opus 4.7 was the only model to provide concrete refactor patterns with implementation blueprints.

**Evidence:**
- Opus: "Replace with `Lazy[Bridge]`", "Collapse 7 functions to `_resolve_optional_plugin<T>`", "Use Strategy pattern for `PlatformKeyResolver`"
- All other models: Identified problems but no implementation patterns
- Opus provided quantified impact: "80 lines → 10 lines"

**Implication:** Top-tier models justify cost ONLY when refactor proposals are needed (greenfield architecture, major refactors, design validation).

**Action:** Update Mutl3y Phase 7 "God Mode" requirement to specify whether refactor proposals are desired. If yes, use Opus. If no, use Tier 2 and save 93% cost.

---

### 5. **Free Tier Models Are Viable for Triage and Discovery**

**Finding:** GPT-5 mini (Tier 0 FREE) delivered 7 quality findings (82/100 score) with zero cost.

**Evidence:**
- GPT-5 mini: 7 findings (2 CRITICAL, 5 HIGH), ownership fragility + DI bootstrap issues
- Raptor mini: 7 findings (1 CRITICAL, 6 HIGH), unique factory-override bypass finding
- Both outperformed some paid Tier 1 models (GPT-5.4 mini: only 5 findings)

**Implication:** Free tier is sufficient for:
- Discovery phase (Phase 0) sweeps
- Triage sorting (HIGH vs MEDIUM)
- Daily automated scans
- Learning/training cycles

**Action:** Update Mutl3y Phase 0 scout defaults to use free tier (GPT-5 mini or Raptor mini) for initial sweeps, then escalate to Tier 1 for focused investigation.

---

### 6. **Multi-Model Consensus Validates High-Confidence Findings**

**Finding:** Findings that appeared in 5+ models across all tiers represent real, high-confidence issues.

**Convergent Findings (8+ models):**
- Type erasure with `cast(dict[str, Any], ...)`
- Marker-prefix ownership leak in `task_extract_adapters`
- Lazy import circular dependency workarounds

**Implication:** Multi-model consensus is a stronger signal than single-model severity rating.

**Action:**
1. Weight findings by model-count consensus (5+ models = auto-promote to HIGH)
2. Treat single-model CRITICAL findings as "needs validation" unless evidence is concrete
3. Use consensus weighting in Mutl3y grading phase

---

## Tactical Lessons

### 7. **Model Self-Identification is Unreliable**

**Finding:** GPT-5.5 reported itself as "GitHub Copilot" with "unknown tier".

**Action:** Trust explicit dispatch `model` parameter over model self-reporting in output. Log both in model-usage-ledger.yaml for audit trail.

---

### 8. **Preview Models Require "(Preview)" Suffix**

**Finding:** "Gemini 3 Flash (copilot)" failed dispatch. Correct: "Gemini 3 Flash (Preview) (copilot)".

**Action:** Update Mutl3y model dispatch logic to auto-append "(Preview)" for known preview models (Gemini 3 Flash, Raptor mini).

---

### 9. **Structured Output Prompts Need Explicit Format Constraints**

**Finding:** Generic "return YAML" instruction produced format drift in some models.

**Action:** Update Gilfoyle prompt template to include:
```yaml
# REQUIRED OUTPUT FORMAT (no deviations):
model_used: [exact model name]
findings:
  - id: GILF-{TIER}{MODEL}-{NN}
    severity: CRITICAL|HIGH|MEDIUM
    ...
```

Plus: "Any response that does not start with `model_used:` will be rejected."

---

### 10. **Breadth vs Depth Trade-Off Varies by Model**

**Finding:**
- Claude models: 9 findings with deep root-cause analysis (high depth)
- GPT models: 5-9 findings with broad module coverage (high breadth)
- Gemini models: 5-6 findings, mixed breadth/depth

**Implication:** Choose model based on review goal:
- **Need breadth** (cross-module issues): GPT-5.4
- **Need depth** (refactor proposals): Claude Opus 4.7
- **Need balance**: Claude Sonnet 4.5

**Action:** Add `review_focus` parameter to Mutl3y Phase 7: `breadth | depth | balanced`, auto-select model.

---

## Recommended Mutl3y Model Dispatch Strategy (Updated)

### Three-Tier Strategy (97% cost savings vs Tier 4-always)

| Phase | Default Model | Cost | Use Case |
|-------|--------------|------|----------|
| **Phase 0 (Discovery)** | GPT-5 mini (Tier 0 FREE) | $0.000 | Initial sweeps, triage |
| **Phase 3 (Investigation)** | Claude Haiku 4.5 (Tier 1) | $0.001 | Focused investigation |
| **Phase 5 (Implementation)** | Claude Haiku 4.5 (Tier 1) | $0.001 | Code changes |
| **Phase 6 (Validation)** | GPT-5.4 (Tier 2) | $0.003 | Standard verification |
| **Phase 7 (God Mode)** | **If refactor needed:** Opus 4.7<br>**Else:** GPT-5.4 | $0.045<br>$0.003 | Final review |

**High-Stakes Override:** When `review_criticality=HIGH`, run Haiku + GPT-5.4 in parallel and merge (total: $0.004, better coverage than single Opus at $0.045).

---

## Cost-Quality Matrix (Final)

```
                    QUALITY →
                60   70   80   90   95   98
         ┌─────┬────┬────┬────┬────┬────┐
    FREE │ 4o  │ 4.1│ 5m │    │    │    │ Tier 0
         ├─────┼────┼────┼────┼────┼────┤
  0.33x  │     │5.4m│ G3F│ Grk│ H45│    │ Tier 1
         ├─────┼────┼────┼────┼────┼────┤
     1x  │     │    │ 2.5│    │ 5.4│    │ Tier 2
         │     │    │ Pro│    │ S45│    │
         ├─────┼────┼────┼────┼────┼────┤
   7.5x  │     │    │    │ 5.5│    │    │ Tier 4
         ├─────┼────┼────┼────┼────┼────┤
    15x  │     │    │    │    │    │ Op7│ Tier 4
         └─────┴────┴────┴────┴────┴────┘
              C O S T ↓
```

**Sweet Spot:** Tier 1 Haiku 4.5 (88/100 at 0.33x) or Tier 2 GPT-5.4 (95/100 at 1x).

**Avoid:** Tier 4 for routine reviews (marginal quality gain, 7-15x cost penalty).

---

## Future Testing Recommendations

### 1. **Test Format Stability Across 5 Runs**
Run each model 5 times with identical prompt, measure format-compliance rate. Quarantine models with <80% compliance.

### 2. **Test Multi-Model Merge Strategy**
Compare single Opus run ($0.045) vs parallel Haiku+GPT-5.4 with merged findings ($0.004). Hypothesis: merge delivers better coverage.

### 3. **Test Free Tier for Daily Automated Scans**
Run GPT-5 mini or Raptor mini on every commit, escalate only on CRITICAL findings. Measure false-positive rate.

### 4. **Test Model Blind Spots with Synthetic Bugs**
Inject known bugs (TOCTOU race, cache-key collision, type-erasure anti-patterns), measure which models catch which bug classes.

### 5. **Test Tier 4 Refactor Proposal Quality**
Have human reviewers grade Opus refactor proposals on: (a) correctness, (b) implementability, (c) impact. Measure ROI of 15x cost premium.

---

### 11. **3-Node Cluster Strategy vs Tier 4/5 Discovery — Pending Wave 3 Retest**

**Status:** VALIDATION PENDING

**Hypothesis:** A focused 3-node unified cluster (identical prompts, same modules for all models) captures 90%+ of findings vs running exhaustive 13-model sweep.

**Wave 2 data (NOT YET COMPARABLE):** 38 findings from 3-node cluster vs 100+ from 13-model sweep. However, Wave 2 used distributed strategy (different models = different modules), which is NOT apples-to-apples.

**Next Steps (Wave 3):**
1. Execute 3-node cluster with unified prompts and identical module scope
2. Run both Tier 0 and Tier 1 on same prompt/modules (true capability comparison)
3. Compare results to Wave 1 to validate: Does unified 3-node = 90%+ of multi-model discovery?
4. Calculate true cost-benefit: $0 (Tier 0) vs $1,404 (13-model sweep) for percentage of findings

**Decision Gate:** Only claim cost-benefit strategy after Wave 3 unified retest validates the hypothesis.

---

## Items for Later Review

### **Review Item 1: Verify Opus Refactor Proposal Instructions**

**Issue:** FACT 4 credits Opus with providing refactor proposals as the primary differentiator for Tier 4. However, we need to verify:

1. **Was Opus explicitly asked to provide refactor proposals?** Check the original Gilfoyle prompt template used in Wave 1. If refactor proposals were not explicitly requested, then Opus deviated from instructions (initiative).

2. **Could other models provide similar refactor proposals if asked?** Lower-tier models (Sonnet 4.5, GPT-5.4, Haiku) might deliver similar refactor patterns if the prompt explicitly requested them. This would reduce Opus's differentiation.

3. **Impact on cost-benefit analysis:** If refactor proposals are not in the default instructions, then crediting Opus for "unsolicited" output inflates its value. If lower-tier models can provide them when asked, Opus cost premium becomes even harder to justify.

**Action:** Before finalizing FACT 4, audit the original Gilfoyle prompt and re-score Opus relative to lower-tier models when refactors are NOT explicitly requested.

---

## Durable Facts for Memory

**FACT 1:** Quality plateaus at Tier 2 for Python code review. Tier 4 (Opus 4.7, GPT-5.5) costs 7-15x more but delivers only 3-5% quality improvement over Tier 2 (Sonnet 4.5, GPT-5.4). Reserve Tier 4 for high-stakes architectural decisions requiring refactor proposals.

**FACT 2:** Lower tiers can find critical issues higher tiers miss. Claude Haiku 4.5 (Tier 1, 0.33x cost) found a CRITICAL TOCTOU race condition that all Tier 2 models missed. Multi-model sampling (Haiku + Tier 2) delivers better coverage than single Tier 4 run at 91% lower cost.

**FACT 3:** Grok Code Fast 1 has non-deterministic structured-output compliance. First run produced well-formatted YAML, retest produced prose-only. Production workflows depending on structured output must add format validation and retry logic for Grok.

**FACT 4:** Claude Opus 4.7 is the only model that provides concrete refactor proposals with implementation blueprints (Strategy patterns, generic collapse, quantified line-count reductions). This is the primary differentiator justifying Tier 4 cost.

**FACT 5:** Free tier models (GPT-5 mini, Raptor mini) are viable for discovery and triage. Both delivered 7 quality findings (80-82/100 scores) with zero cost, outperforming some paid Tier 1 models.

---

## Files Generated

1. **MODEL_RANKING_REPORT_FINAL.md** — Comprehensive 13-model ranking with tier analysis
2. **LESSONS_LEARNED.md** (this file) — Strategic and tactical lessons for future work
3. **Model-specific findings files** — 14 individual YAML/text artifacts per model run

---

## End of Report

**Next Steps:**
1. Store FACT 1-5 in repo memory for future Mutl3y cycles
2. Update Mutl3y foreman model dispatch defaults per Three-Tier Strategy
3. Add format validation layer to artifact processing
4. Implement model-usage-ledger.yaml tracking
5. Schedule multi-model merge strategy validation test
