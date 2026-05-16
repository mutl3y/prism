# 3-Node Cluster: READY TO LAUNCH

**Status:** ✅ All nodes configured and ready  
**Cost:** $0 (all Tier 0)  
**Timeline:** ~75 minutes to completion  
**Expected Finding Count:** 45-57 (vs original 20-28)  
**Expected Quality:** 87/100 (matches Haiku baseline)

---

## Quick Launch Guide

### Node 1: GPT-4o (Architecture & DI Focus)

**Copy the prompt from WAVE2_CLUSTER_PLAN.md → NODE 1 PROMPT section**

**Send to runSubagent:**
```
Agent: Gilfoyle Code Review God Mode
Model: GPT-4o (copilot)
Prompt: [Copy from WAVE2_CLUSTER_PLAN.md NODE1_PROMPT]
```

**Expected:** 12-15 findings (ownership fragmentation, DI god-object, type erasure)

---

### Node 2: GPT-4.1 (Concurrency & Type Safety)

**Copy the prompt from WAVE2_CLUSTER_PLAN.md → NODE 2 PROMPT section**

**Send to runSubagent:**
```
Agent: Gilfoyle Code Review God Mode
Model: GPT-4.1 (copilot)
Prompt: [Copy from WAVE2_CLUSTER_PLAN.md NODE2_PROMPT]
```

**Expected:** 11-14 findings (TOCTOU race, type erasure, cache collision)

---

### Node 3A: GPT-5 mini (Ownership & Validation)

**Copy the prompt from WAVE2_CLUSTER_PLAN.md → NODE 3A PROMPT section**

**Send to runSubagent:**
```
Agent: Gilfoyle Code Review God Mode
Model: GPT-5 mini (copilot)
Prompt: [Copy from WAVE2_CLUSTER_PLAN.md NODE3A_PROMPT]
```

**Expected:** 12-15 findings (marker-prefix ownership, lazy imports, validation proliferation)

---

### Node 3B: Raptor mini (Caching & Performance)

**Copy the prompt from WAVE2_CLUSTER_PLAN.md → NODE 3B PROMPT section**

**Send to runSubagent:**
```
Agent: Gilfoyle Code Review God Mode
Model: Raptor mini (Preview) (copilot)
Prompt: [Copy from WAVE2_CLUSTER_PLAN.md NODE3B_PROMPT]
```

**Expected:** 10-13 findings (cache safety, performance footguns, exception handling, dead code)

---

## Execution Timeline

```
t=0:00  Launch ALL 4 models in parallel (not sequentially)
        ├─ Node 1 (GPT-4o)
        ├─ Node 2 (GPT-4.1)
        ├─ Node 3A (GPT-5 mini)
        └─ Node 3B (Raptor mini)

t=0:18  All 4 complete (18 min each, running in parallel)
        Wait for all to finish before proceeding

t=0:30  Collect results from all 4 YAML outputs
        Save to artifacts folder:
        - node1-gpt4o-findings.yaml
        - node2-gpt4.1-findings.yaml
        - node3a-gpt5mini-findings.yaml
        - node3b-raptormini-findings.yaml

t=0:45  Merge findings
        - Identify convergent issues (2+ nodes)
        - Identify unique issues (1 node only)
        - Calculate cluster metrics

t=0:60  Analysis complete
        - Compare to hypothesis
        - Generate final report
```

**Total time: ~60 minutes to decision point**

---

## Success Criteria (ALL 4 must be met)

✅ **Quality ≥ 85/100**  
Expected: 87/100 (matching Haiku 88/100)

✅ **Finding count ≥ 45**  
Expected: 48 findings (5-6x individual)

✅ **Module coverage 9/11 minimum**  
Expected: All 11 modules touched

✅ **Critical discovery: TOCTOU race or cache collision**  
Expected: Node 2 finds TOCTOU, Node 3B finds cache collision

---

## Key Metrics to Capture

### Per-Node Results

**Node 1 (GPT-4o):** ___/100 quality, ___ findings
- DI god-object identified? Y/N
- Type erasure quantified? Y/N
- Ownership fragmentation map created? Y/N

**Node 2 (GPT-4.1):** ___/100 quality, ___ findings
- TOCTOU race found? Y/N (critical!)
- Type erasure impact shown? Y/N
- Cache-key collision scenario? Y/N

**Node 3A (GPT-5 mini):** ___/100 quality, ___ findings
- Marker-prefix ownership leak found? Y/N
- Lazy import coupling identified? Y/N
- Validation proliferation quantified? Y/N

**Node 3B (Raptor mini):** ___/100 quality, ___ findings
- Cache safety issues found? Y/N
- Performance footguns identified? Y/N
- Exception handling gaps? Y/N

### Cluster-Level Results

**Total findings:** ___ (target ≥45)  
**Average quality:** ___/100 (target ≥85)  
**Module coverage:** ___/11 (target ≥9)  
**Convergent findings:** ___ (target ≥8)  
**Unique findings:** ___ (target ≥25)  
**Critical bugs discovered:** ___ (target ≥2)

---

## Decision Matrix

After results:

```
IF all 4 success criteria met:
  → Free-tier cluster ≥ Tier 1 quality ✅
  → FREE default viable (annual $0.10 vs $27) 🎉
  → Store repo memory: "Distributed cluster beats single expensive model"
  
ELSE IF 3/4 criteria met:
  → Cluster near Tier 1 quality
  → Free tier for discovery + Tier 1 for validation (hybrid)
  → Store repo memory: "Cluster approach marginal win"
  
ELSE IF 2/4 criteria met:
  → Cluster > individual free tier
  → Tier 1 needed for critical work
  → Store repo memory: "Specialization helps but not enough"
  
ELSE:
  → Keep Tier 1 (Haiku) as default
  → Free tier for Phase 0 only
```

---

## Prompts Ready to Copy

All 4 node-specific prompts are in WAVE2_CLUSTER_PLAN.md:

- **NODE 1 PROMPT** (GPT-4o) — Architecture & DI focus
- **NODE 2 PROMPT** (GPT-4.1) — Concurrency & type safety focus
- **NODE 3A PROMPT** (GPT-5 mini) — Ownership & validation focus
- **NODE 3B PROMPT** (Raptor mini) — Caching & performance focus

---

## Files Reference

| File | Purpose |
|------|---------|
| WAVE2_CLUSTER_PLAN.md | Full cluster architecture + prompts |
| WAVE2_CLUSTER_LAUNCH.md | This file (quick reference) |
| CONVERGENCE_ANALYSIS.md | Wave 1 findings (for comparison) |
| artifacts/ | Where to save results |

---

## Next Actions

1. ✅ **Launch all 4 nodes NOW** (don't wait for any to complete)
2. ⏳ **Wait ~18 min** for all to finish
3. ⏳ **Collect YAML outputs** to artifacts folder
4. ⏳ **Merge & analyze** findings
5. ⏳ **Generate final report** (WAVE2_CLUSTER_RESULTS.md)
6. ⏳ **Make cost-optimization decision** based on results

---

## Why Cluster is Powerful

**Traditional approach:**
- 1 model = ~9 findings, some blind spots

**Cluster approach:**
- Node 1 (architecture) catches: DI god-object, ownership fragmentation
- Node 2 (concurrency) catches: TOCTOU race, threading issues  
- Node 3A (validation) catches: marker-prefix leak, validation proliferation
- Node 3B (performance) catches: cache collisions, perf footguns
- **Merge:** High-confidence convergent issues + specialization value

**Result:** 45-57 findings (5-6x better coverage)  
**Cost:** $0 (vs $0.045 for Tier 4)  
**Quality:** 87/100 (matches Tier 1 baseline)

---

## Ready?

All nodes configured. All prompts ready. All metrics defined.

Let's launch! 🚀

```
Node 1: GPT-4o
Node 2: GPT-4.1
Node 3A: GPT-5 mini
Node 3B: Raptor mini

Execute in PARALLEL (t=0:00)
Complete ~18 min (t=0:18)
Merge & report (t=0:45)
Decision (t=1:00)
```

**GO GO GO!**
