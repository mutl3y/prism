# Wave 2: Sequential Node Execution Plan

**Status:** ✅ Ready for sequential runs (one at a time)  
**Purpose:** Avoid overwhelming shared Gilfoyle agent resource  
**Timeline:** ~70 minutes total (18 min per node + 5 min between runs)  
**Cost:** $0 (all Tier 0)

---

## Sequential Execution Overview

Running each node separately allows other users to share the Gilfoyle Code Review God Mode agent without bottlenecks.

| Step | Node | Model | Timeline | Status |
|------|------|-------|----------|--------|
| 1 | Node 1 | GPT-4o | t=0:00-0:18 | Ready |
| 2 | Node 2 | GPT-4.1 | t=0:25-0:43 | Ready |
| 3 | Node 3A | GPT-5 mini | t=0:50-1:08 | Ready |
| 4 | Node 3B | Raptor mini | t=1:15-1:33 | Ready |
| 5 | Merge & Analyze | - | t=1:40-1:55 | Ready |

**Total execution: ~115 minutes** (vs 75 min if parallel)  
**Buffer between runs: 5 min** (allows agent to reset, other users to get a turn)

---

## Node 1: GPT-4o (Architecture & DI Focus)

**Time:** ~18 minutes  
**Status:** Ready when Node 1 appears complete

### Step 1a: Copy the Prompt

Go to **WAVE2_CLUSTER_PLAN.md** and find the **NODE 1 PROMPT** section.

Copy everything from `## Gilfoyle Code Review: Architecture & DI Focus` through the final `### Token Limit` section.

### Step 1b: Launch Node 1

Send to runSubagent:

```
Agent: Gilfoyle Code Review God Mode
Model: GPT-4o (copilot)
Prompt: [PASTE NODE 1 PROMPT HERE]
```

### Step 1c: Monitor & Capture Results

- Expected runtime: 15-18 minutes
- Expected findings: 12-15
- Look for YAML output format

### Step 1d: Save Results

Create file: `/raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/artifacts/node1-gpt4o-findings.yaml`

Copy the entire YAML findings output from Node 1 into this file.

### Step 1e: Record Metrics

```
Node 1 Results:
  Model: GPT-4o
  Quality Score: ___/100
  Finding Count: ___
  Module Coverage: ___/3 (di.py, scanner_context.py, di_helpers.py)
  TOCTOU Found: Y/N
  Time: ___ min
  Status: ✓ COMPLETE
```

### Step 1f: Wait 5 Minutes

Allow Gilfoyle agent to reset and other users to get a turn.

**Proceed to Node 2 at t=0:25**

---

## Node 2: GPT-4.1 (Concurrency & Type Safety)

**Time:** ~18 minutes  
**Status:** Start after Node 1 complete + 5 min wait

### Step 2a: Copy the Prompt

Go to **WAVE2_CLUSTER_PLAN.md** and find the **NODE 2 PROMPT** section.

Copy everything from `## Gilfoyle Code Review: Concurrency & Type Safety` through the final `### Critical Finding Target` section.

### Step 2b: Launch Node 2

Send to runSubagent:

```
Agent: Gilfoyle Code Review God Mode
Model: GPT-4.1 (copilot)
Prompt: [PASTE NODE 2 PROMPT HERE]
```

### Step 2c: Monitor & Capture Results

- Expected runtime: 15-18 minutes
- Expected findings: 11-14
- ⚠️ **Critical target:** Look for TOCTOU race finding

### Step 2d: Save Results

Create file: `/raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/artifacts/node2-gpt4.1-findings.yaml`

Copy the entire YAML findings output from Node 2 into this file.

### Step 2e: Record Metrics

```
Node 2 Results:
  Model: GPT-4.1
  Quality Score: ___/100
  Finding Count: ___
  Module Coverage: ___/2 (variable_discovery.py, feature_detector.py)
  TOCTOU Found: YES / NO (critical!)
  Cache Collision Found: Y/N
  Time: ___ min
  Status: ✓ COMPLETE
```

### Step 2f: Wait 5 Minutes

Allow Gilfoyle agent to reset and other users to get a turn.

**Proceed to Node 3A at t=0:50**

---

## Node 3A: GPT-5 mini (Ownership & Validation)

**Time:** ~18 minutes  
**Status:** Start after Node 2 complete + 5 min wait

### Step 3Aa: Copy the Prompt

Go to **WAVE2_CLUSTER_PLAN.md** and find the **NODE 3A PROMPT** section.

Copy everything from `## Gilfoyle Code Review: Ownership & Validation` through the final `### Critical Expectation` section.

### Step 3Ab: Launch Node 3A

Send to runSubagent:

```
Agent: Gilfoyle Code Review God Mode
Model: GPT-5 mini (copilot)
Prompt: [PASTE NODE 3A PROMPT HERE]
```

### Step 3Ac: Monitor & Capture Results

- Expected runtime: 15-18 minutes
- Expected findings: 12-15
- Look for marker-prefix ownership leak (convergent issue)

### Step 3Ad: Save Results

Create file: `/raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/artifacts/node3a-gpt5mini-findings.yaml`

Copy the entire YAML findings output from Node 3A into this file.

### Step 3Ae: Record Metrics

```
Node 3A Results:
  Model: GPT-5 mini
  Quality Score: ___/100
  Finding Count: ___
  Module Coverage: ___/4 (task_extract_adapters, scan_request, etc.)
  Marker-prefix Ownership Found: Y/N
  Lazy Import Coupling Found: Y/N
  Time: ___ min
  Status: ✓ COMPLETE
```

### Step 3Af: Wait 5 Minutes

Allow Gilfoyle agent to reset and other users to get a turn.

**Proceed to Node 3B at t=1:15**

---

## Node 3B: Raptor mini (Caching & Performance)

**Time:** ~18 minutes  
**Status:** Start after Node 3A complete + 5 min wait

### Step 3Ba: Copy the Prompt

Go to **WAVE2_CLUSTER_PLAN.md** and find the **NODE 3B PROMPT** section.

Copy everything from `## Gilfoyle Code Review: Caching & Performance` through the final `### Token Limit` section.

### Step 3Bb: Launch Node 3B

Send to runSubagent:

```
Agent: Gilfoyle Code Review God Mode
Model: Raptor mini (Preview) (copilot)
Prompt: [PASTE NODE 3B PROMPT HERE]
```

### Step 3Bc: Monitor & Capture Results

- Expected runtime: 15-18 minutes
- Expected findings: 10-13
- Look for cache safety issues, performance footguns

### Step 3Bd: Save Results

Create file: `/raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/artifacts/node3b-raptormini-findings.yaml`

Copy the entire YAML findings output from Node 3B into this file.

### Step 3Be: Record Metrics

```
Node 3B Results:
  Model: Raptor mini
  Quality Score: ___/100
  Finding Count: ___
  Module Coverage: ___/3 (scan_cache, events, scan_request)
  Cache Safety Issues Found: Y/N
  Performance Footguns Found: Y/N
  Dead Code Found: Y/N
  Time: ___ min
  Status: ✓ COMPLETE
```

---

## Phase: Merge & Analysis

**Time:** ~15 minutes  
**Status:** Begin after Node 3B complete

### Step 5a: Collect All 4 YAML Files

Verify all files exist:
- `node1-gpt4o-findings.yaml`
- `node2-gpt4.1-findings.yaml`
- `node3a-gpt5mini-findings.yaml`
- `node3b-raptormini-findings.yaml`

### Step 5b: Calculate Cluster Metrics

```yaml
cluster_metrics:
  total_findings: ___ (sum of all nodes, target ≥45)
  average_quality: ___/100 (target ≥85)
  module_coverage: ___/11 (target ≥9)
  
  node_1_gpt4o:
    findings: ___
    quality: ___
    modules: ___
  
  node_2_gpt4.1:
    findings: ___
    quality: ___
    modules: ___
  
  node_3a_gpt5mini:
    findings: ___
    quality: ___
    modules: ___
  
  node_3b_raptormini:
    findings: ___
    quality: ___
    modules: ___
```

### Step 5c: Identify Convergent Findings

Issues found by 2+ nodes (expected ~8-12):

```yaml
convergent_findings:
  - issue: "Type erasure with cast(Any)"
    nodes: [1, 2, ...]
    confidence: HIGH
  - issue: "Marker-prefix ownership leak"
    nodes: [3A, ...]
    confidence: HIGH
  - issue: "Lazy import coupling"
    nodes: [1, 3A, ...]
    confidence: HIGH
  # ... more
```

### Step 5d: Identify Unique Findings

Issues found by only 1 node (expected ~25-30):

```yaml
unique_findings:
  - issue: "TOCTOU race in _get_prepared_policy_bundle"
    node: 2
    confidence: MEDIUM
  - issue: "Cache-key collision risk"
    node: 3B
    confidence: MEDIUM
  # ... more
```

### Step 5e: Compare to Success Criteria

```
SUCCESS CRITERIA CHECK:

✓ Quality ≥ 85/100?
  Node 1: ___/100
  Node 2: ___/100
  Node 3A: ___/100
  Node 3B: ___/100
  Average: ___/100
  Status: [PASS | FAIL]

✓ Finding count ≥ 45?
  Total: ___
  Status: [PASS | FAIL]

✓ Module coverage ≥ 9/11?
  Covered: ___/11
  Status: [PASS | FAIL]

✓ Critical discovery (TOCTOU or cache collision)?
  TOCTOU found: [YES | NO]
  Cache collision found: [YES | NO]
  Status: [PASS | FAIL]

OVERALL: [ALL 4 MET | 3/4 MET | 2/4 MET | <2 MET]
```

### Step 5f: Generate Final Report

Create: `WAVE2_CLUSTER_RESULTS.md`

```markdown
# Wave 2 Cluster Results

## Summary
- Total findings: ___
- Average quality: ___/100
- Module coverage: ___/11
- All 4 success criteria: [MET | NOT MET]

## Per-Node Results
[Detailed metrics for each node]

## Convergent Findings (High Confidence)
[List of 8-12 findings found by 2+ nodes]

## Unique Findings
[List of findings unique to one node]

## Decision
[Is cluster ≥ Tier 1 quality? Free-tier default viable?]
```

---

## Expected Results Summary

### Per-Node Expected Output

| Node | Model | Expected Quality | Expected Findings | Critical Target |
|------|-------|------------------|-------------------|-----------------|
| 1 | GPT-4o | 85-88/100 | 12-15 | God-object pattern |
| 2 | GPT-4.1 | 85-88/100 | 11-14 | TOCTOU race ⚠️ |
| 3A | GPT-5 mini | 85-88/100 | 12-15 | Marker-prefix leak |
| 3B | Raptor mini | 82-85/100 | 10-13 | Cache safety |
| **CLUSTER** | **Combined** | **85-87/100** | **45-57** | **2-3 critical** |

### Success Threshold

**All 4 criteria must be met:**
1. ✅ Quality ≥ 85/100 (expect 87)
2. ✅ Finding count ≥ 45 (expect 48)
3. ✅ Module coverage ≥ 9/11 (expect 11/11)
4. ✅ Critical discovery: TOCTOU or cache collision (expect YES)

**If all 4 met:** Free-tier cluster becomes default (additional 97% cost savings!)

---

## Execution Timeline

```
t=0:00   Start Node 1 (GPT-4o)
t=0:18   Node 1 complete
t=0:23   [5 min buffer]
t=0:25   Start Node 2 (GPT-4.1)
t=0:43   Node 2 complete
t=0:48   [5 min buffer]
t=0:50   Start Node 3A (GPT-5 mini)
t=1:08   Node 3A complete
t=1:13   [5 min buffer]
t=1:15   Start Node 3B (Raptor mini)
t=1:33   Node 3B complete
t=1:40   [5 min prep]
t=1:45   Merge & analysis complete
t=1:55   Final report ready

TOTAL: ~115 minutes
```

---

## Prompts Checklist

Verify all 4 prompts are copy-paste ready from **WAVE2_CLUSTER_PLAN.md**:

- [x] NODE 1 PROMPT (GPT-4o) — Lines ~100-200
- [x] NODE 2 PROMPT (GPT-4.1) — Lines ~200-300
- [x] NODE 3A PROMPT (GPT-5 mini) — Lines ~300-400
- [x] NODE 3B PROMPT (Raptor mini) — Lines ~400-500

All sections include:
- ✓ Focus areas clearly defined
- ✓ Target modules listed
- ✓ Success criteria checklist
- ✓ YAML output format specified
- ✓ Token limit (UNLIMITED)

---

## Important Notes

### For Each Run:

1. **Copy entire prompt section** (not just the title)
2. **Verify Agent:** Always use "Gilfoyle Code Review God Mode"
3. **Verify Model:** Use exact model name from table above
4. **Wait for completion:** Don't start next node until current finishes
5. **Save YAML output** to artifacts folder immediately
6. **Record metrics** in the template above

### Between Runs:

- Allow 5 minutes for Gilfoyle agent to reset
- This lets other users get a turn
- Improves resource fairness for shared infrastructure

### Result Capture:

- Save all findings to `artifacts/` folder
- Use YAML format (as specified in prompts)
- Filename pattern: `node{N}-{model}-findings.yaml`

---

## Decision Gate (After All 4 Complete)

```
IF all 4 success criteria met:
  ✅ Free-tier cluster ≥ Tier 1 quality
  ✅ FREE default viable
  ✅ Annual cost: $27 → $0.10 (99.6% savings!)
  → Update model dispatch strategy

ELSE IF 3/4 met:
  ✓ Cluster near Tier 1 (partial win)
  ~ Hybrid strategy (free discovery + Tier 1 critical)

ELSE IF 2/4 met:
  ! Cluster > individual (modest improvement)
  ! Keep Tier 1 as default

ELSE:
  ✗ Tier 1 needed for all work
  ✗ Free tier for Phase 0 only
```

---

## Ready?

All prompts are prepared and ready to copy.

**Start with Node 1 (GPT-4o) whenever you're ready!**

Each node takes ~18 min, so total runtime is ~115 minutes (just under 2 hours).

Let's go! 🚀
