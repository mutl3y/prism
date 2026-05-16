# 13-Model Gilfoyle Comparison — Complete Report Package

**Test ID:** g84-10-model-gilfoyle-comparison-20260508  
**Date:** 2026-05-08  
**Status:** ✅ COMPLETE  

---

## Quick Navigation

### 📊 **Start Here**

1. **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** — 5-minute read, key findings and recommendations
2. **[MODEL_RANKING_REPORT_FINAL.md](MODEL_RANKING_REPORT_FINAL.md)** — Complete 13-model ranking with analysis
3. **[LESSONS_LEARNED.md](LESSONS_LEARNED.md)** — Strategic and tactical lessons for future work

---

## Report Package Contents

### Core Reports

| File | Purpose | Audience |
|------|---------|----------|
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Quick reference, bottom-line recommendations | Leaders, decision-makers |
| [MODEL_RANKING_REPORT_FINAL.md](MODEL_RANKING_REPORT_FINAL.md) | Comprehensive ranking, tier analysis, quality metrics | Engineers, architects |
| [LESSONS_LEARNED.md](LESSONS_LEARNED.md) | Strategic insights, tactical learnings, future testing | Mutl3y maintainers |
| [README.md](README.md) (this file) | Navigation index | All users |

---

## Key Findings at a Glance

### 🏆 Final Rankings

1. **Claude Opus 4.7** (Tier 4, 15x) — 98/100, refactor proposals
2. **GPT-5.4** (Tier 2, 1x) — 95/100, ownership analysis
3. **Claude Sonnet 4.5** (Tier 2, 1x) — 93/100, meta-architecture
4. **GPT-5.5** (Tier 4, 7.5x) — 91/100, cache-key bugs
5. **Claude Haiku 4.5** (Tier 1, 0.33x) — 88/100, **BEST VALUE** ⭐

### 💡 Key Insights

- **Quality plateaus at Tier 2** — Tier 4 costs 7-15x more for 3-5% improvement
- **Lower tiers can find what higher miss** — Haiku caught CRITICAL TOCTOU race ALL Tier 2 missed
- **Grok has format instability** — produced YAML first run, prose second run
- **Free tier is viable** — GPT-5 mini/Raptor mini delivered 80-82/100 quality at zero cost
- **Three-tier strategy = 97% savings** — vs Tier 4-always approach

---

## Model-Specific Findings

### Tier 4 (Top-Tier)

- [gilfoyle-tier4-opus47-findings.yaml](artifacts/gilfoyle-tier4-opus47-findings.yaml) — Claude Opus 4.7 (7 findings, refactor blueprints)
- [gilfoyle-tier4-gpt55-findings.yaml](artifacts/gilfoyle-tier4-gpt55-findings.yaml) — GPT-5.5 (8 findings, cache-key collision bug)

### Tier 2 (1x)

- [gilfoyle-tier2-sonnet45-findings.yaml](artifacts/gilfoyle-tier2-sonnet45-findings.yaml) — Claude Sonnet 4.5 (9 findings, identity crisis)
- [gilfoyle-tier2-gpt54-findings.yaml](artifacts/gilfoyle-tier2-gpt54-findings.yaml) — GPT-5.4 (9 findings, ownership collapse)
- [gilfoyle-tier2-gemini25pro-findings.yaml](artifacts/gilfoyle-tier2-gemini25pro-findings.yaml) — Gemini 2.5 Pro (5 findings, macro-architecture)

### Tier 1 (0.33x)

- [gilfoyle-tier1-haiku45-findings.yaml](artifacts/gilfoyle-tier1-haiku45-findings.yaml) — Claude Haiku 4.5 (9 findings, **TOCTOU race**)
- [gilfoyle-tier1-gpt54mini-findings.yaml](artifacts/gilfoyle-tier1-gpt54mini-findings.yaml) — GPT-5.4 mini (5 findings)
- [gilfoyle-tier1-gemini3flash-findings.yaml](artifacts/gilfoyle-tier1-gemini3flash-findings.yaml) — Gemini 3 Flash (6 findings)
- [gilfoyle-tier1-grok-findings.yaml](artifacts/gilfoyle-tier1-grok-findings.yaml) — Grok Code Fast 1 first run (8 findings)
- [gilfoyle-tier1-grok-retest-findings.txt](artifacts/gilfoyle-tier1-grok-retest-findings.txt) — Grok retest (**format failure**, prose only)

### Tier 0 (FREE)

- [gilfoyle-tier0-gpt4o-findings.yaml](artifacts/gilfoyle-tier0-gpt4o-findings.yaml) — GPT-4o (5 findings)
- [gilfoyle-tier0-gpt41-findings.yaml](artifacts/gilfoyle-tier0-gpt41-findings.yaml) — GPT-4.1 (7 findings)
- [gilfoyle-tier0-gpt5mini-findings.yaml](artifacts/gilfoyle-tier0-gpt5mini-findings.yaml) — GPT-5 mini (7 findings)
- [gilfoyle-tier0-raptor-findings.yaml](artifacts/gilfoyle-tier0-raptor-findings.yaml) — Raptor mini (7 findings, factory override bypass)

---

## Repo Memories Stored

Key findings have been stored in `/raid5/source/test/memories/repo/` for future reference:

1. **mutl3y-model-tier-quality-plateau.json** — Quality plateaus at Tier 2
2. **mutl3y-model-tier-blind-spots.json** — Lower tiers find issues higher miss
3. **mutl3y-model-grok-format-instability.json** — Grok structured-output reliability
4. **mutl3y-model-opus-refactor-proposals.json** — When Tier 4 premium is justified
5. **mutl3y-model-free-tier-viability.json** — Free tier for discovery/triage

---

## Recommended Action Plan

### Phase 1: Immediate (This Week)

- [ ] Update Mutl3y foreman model dispatch defaults
  - Phase 0 scouts → GPT-5 mini (FREE)
  - Phase 3/5 workers → Claude Haiku 4.5 (Tier 1)
  - Phase 6 validation → GPT-5.4 (Tier 2)
  - Phase 7 God Mode → GPT-5.4 (Tier 2), escalate to Opus only for refactor proposals

- [ ] Add format validation layer to artifact processing
  - Detect missing YAML structure
  - Auto-retry with tightened prompt on format failure
  - Log format-failure rate per model

- [ ] Create `model-usage-ledger.yaml` tracking
  - Log every dispatch attempt
  - Track quality scores, format failures, retry counts
  - Enable data-driven model selection

### Phase 2: Near-Term (This Month)

- [ ] Multi-model merge validation
  - Run Haiku + GPT-5.4 in parallel for 10 reviews
  - Compare merged findings vs single Opus run
  - Validate 91% cost savings claim with superior coverage

- [ ] Format stability testing
  - Run each model 5 times with identical prompt
  - Measure format-compliance rate
  - Quarantine models with <80% compliance for structured tasks

- [ ] Free tier daily automation
  - Set up GPT-5 mini daily commit scans
  - Alert only on CRITICAL findings
  - Measure false-positive rate

### Phase 3: Future (Next Quarter)

- [ ] Synthetic bug injection testing
  - Create test suite with known bugs (TOCTOU, cache collision, type erasure)
  - Map which models catch which bug classes
  - Build model-blind-spot matrix

- [ ] Opus refactor proposal ROI analysis
  - Human reviewers grade 20 Opus refactor proposals
  - Measure: correctness, implementability, impact
  - Validate 15x cost premium for architectural work

---

## Test Scope

**Target:** `prism/src/prism/scanner_core/`  
**Files Reviewed:** 11 modules (di.py, scanner_context.py, execution_request_builder.py, task_extract_adapters.py, variable_discovery.py, feature_detector.py, scan_request.py, scan_cache.py, di_helpers.py, events.py, protocols_runtime.py)

**Models Tested:** 13 unique models + 1 retest = 14 total samples

**Tiers Covered:**
- Tier 0 (FREE): 4 models
- Tier 1 (0.33x): 4 models
- Tier 2 (1x): 3 models
- Tier 4 (7.5-15x): 2 models

**Prompt:** Identical 800-token Gilfoyle god-mode review prompt for all runs

---

## Cost Analysis

### Monthly Cost (50 reviews)

| Strategy | Cost/Month | Cost/Year | Savings vs Tier 4 |
|----------|-----------|-----------|-------------------|
| All Tier 4 (Opus) | $2.25 | $27.00 | baseline |
| All Tier 2 | $0.15 | $1.80 | 93% |
| All Tier 1 (Haiku) | $0.05 | $0.60 | 97% |
| **Three-tier (recommended)** | **$0.07** | **$0.84** | **97%** ✅ |

**Three-tier mix:** 90% Tier 1, 8% Tier 2, 2% Tier 4

---

## Contact

For questions about this report or Mutl3y model dispatch strategy:

- See [LESSONS_LEARNED.md](LESSONS_LEARNED.md) for detailed analysis
- Check repo memories in `/raid5/source/test/memories/repo/mutl3y-model-*.json`
- Review individual model findings in `artifacts/` directory

---

**Report Status:** ✅ COMPLETE  
**Confidence Level:** HIGH (13-model sample, identical prompt, systematic scoring)  
**Last Updated:** 2026-05-08
