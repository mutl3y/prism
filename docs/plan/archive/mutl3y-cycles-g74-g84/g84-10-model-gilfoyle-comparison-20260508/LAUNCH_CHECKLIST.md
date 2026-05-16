# Wave 2: 3-Node Cluster Launch Checklist

**Status:** ✅ READY TO EXECUTE  
**Date:** 2026-05-08  
**Cost:** $0 (all Tier 0)  
**Timeline:** ~18 min parallel (vs 60 min serial)

---

## Pre-Launch Verification

### Documentation Complete
- [x] WAVE2_CLUSTER_PLAN.md — Full architecture + all 4 prompts
- [x] WAVE2_CLUSTER_LAUNCH.md — Quick launch guide  
- [x] WAVE2_STATUS.txt — Cluster status overview
- [x] CONVERGENCE_ANALYSIS.md — Wave 1 baseline for comparison

### Node Configuration Ready
- [x] NODE 1 (GPT-4o): 3 modules (di.py, scanner_context.py, di_helpers.py)
- [x] NODE 2 (GPT-4.1): 2 modules (variable_discovery.py, feature_detector.py)
- [x] NODE 3A (GPT-5 mini): 4 modules (task_extract_adapters, scan_request, etc.)
- [x] NODE 3B (Raptor mini): 3 modules (scan_cache, events, scan_request)

### Prompts Prepared
- [x] NODE 1 PROMPT: Architecture & DI focus (12 points)
- [x] NODE 2 PROMPT: Concurrency & type safety (10 points, TOCTOU target)
- [x] NODE 3A PROMPT: Ownership & validation (10 points)
- [x] NODE 3B PROMPT: Caching & performance (11 points)

### Success Criteria Defined
- [x] Quality ≥ 85/100 (expect 87/100)
- [x] Finding count ≥ 45 (expect 48)
- [x] Module coverage ≥ 9/11 (expect 11/11)
- [x] Critical discovery (TOCTOU or cache collision)

### Results Infrastructure
- [x] Artifacts folder ready for output
- [x] YAML output format specified in all prompts
- [x] Merge strategy documented
- [x] Analysis metrics defined

---

## Launch Instructions

### Copy-Paste Ready Prompts

All 4 prompts are in: **WAVE2_CLUSTER_PLAN.md**

Extract and use these sections:
```
WAVE2_CLUSTER_PLAN.md → NODE 1 PROMPT
WAVE2_CLUSTER_PLAN.md → NODE 2 PROMPT  
WAVE2_CLUSTER_PLAN.md → NODE 3A PROMPT
WAVE2_CLUSTER_PLAN.md → NODE 3B PROMPT
```

### Launch Node 1 (GPT-4o)

```
Agent: Gilfoyle Code Review God Mode
Model: GPT-4o (copilot)
Prompt: [Copy NODE 1 PROMPT from WAVE2_CLUSTER_PLAN.md]
```

**Expected:** 12-15 findings (ownership, DI patterns, type erasure)

---

### Launch Node 2 (GPT-4.1)

```
Agent: Gilfoyle Code Review God Mode
Model: GPT-4.1 (copilot)
Prompt: [Copy NODE 2 PROMPT from WAVE2_CLUSTER_PLAN.md]
```

**Expected:** 11-14 findings (TOCTOU race, type safety)

---

### Launch Node 3A (GPT-5 mini)

```
Agent: Gilfoyle Code Review God Mode
Model: GPT-5 mini (copilot)
Prompt: [Copy NODE 3A PROMPT from WAVE2_CLUSTER_PLAN.md]
```

**Expected:** 12-15 findings (marker-prefix, validation)

---

### Launch Node 3B (Raptor mini)

```
Agent: Gilfoyle Code Review God Mode
Model: Raptor mini (Preview) (copilot)
Prompt: [Copy NODE 3B PROMPT from WAVE2_CLUSTER_PLAN.md]
```

**Expected:** 10-13 findings (cache, performance, exceptions)

---

## Execution Timeline

```
t=0:00  Launch ALL 4 models in PARALLEL (not sequentially)
        - If available: launch in 1 sec intervals
        - All 4 should be running within 5 seconds

t=0:18  All 4 complete (18 min each, running in parallel)
        - Verify all results returned
        - Check for YAML format

t=0:30  Merge findings into combined YAML
        - node1-gpt4o-findings.yaml
        - node2-gpt4.1-findings.yaml
        - node3a-gpt5mini-findings.yaml
        - node3b-raptormini-findings.yaml

t=0:45  Analysis complete
        - Calculate cluster metrics
        - Compare to hypothesis (87/100, 48 findings)
        - Check success criteria

t=1:00  Decision gate
        - All 4 criteria met? → Free-tier default viable
        - 3/4 criteria met? → Hybrid approach
        - < 3 criteria met? → Tier 1 still needed
```

---

## Results Capture Template

After each node completes, save results:

### Node 1 Results
```yaml
# node1-gpt4o-findings.yaml
node: 1
model: GPT-4o
focus: "Architecture & DI"
quality_score: ___/100
finding_count: ___
module_coverage: ___/3 (di.py, scanner_context.py, di_helpers.py)
toctou_found: Y/N
cache_collision_found: Y/N
findings:
  - id: N1001
    severity: [CRITICAL|HIGH|MEDIUM|LOW]
    category: [ownership|type-safety|concurrency|validation|architecture]
    location: "module:line"
    issue: "..."
    root_cause: "..."
    confidence: 0-100
  - id: N1002
    ...
```

### Node 2 Results
```yaml
# node2-gpt4.1-findings.yaml
node: 2
model: GPT-4.1
focus: "Concurrency & Type Safety"
quality_score: ___/100
finding_count: ___
module_coverage: ___/2 (variable_discovery.py, feature_detector.py)
toctou_found: Y/N
cache_collision_found: Y/N
findings: [...]
```

### Node 3A Results
```yaml
# node3a-gpt5mini-findings.yaml
node: 3
node_variant: A
model: GPT-5 mini
focus: "Ownership & Validation"
quality_score: ___/100
finding_count: ___
module_coverage: ___/4
toctou_found: Y/N
cache_collision_found: Y/N
findings: [...]
```

### Node 3B Results
```yaml
# node3b-raptormini-findings.yaml
node: 3
node_variant: B
model: Raptor mini
focus: "Caching & Performance"
quality_score: ___/100
finding_count: ___
module_coverage: ___/3
toctou_found: Y/N
cache_collision_found: Y/N
findings: [...]
```

---

## Cluster-Level Merge

After collecting all 4:

```yaml
# WAVE2_CLUSTER_RESULTS.md

cluster_summary:
  total_findings: ___ (target ≥45)
  average_quality: ___/100 (target ≥85)
  module_coverage: ___/11 (target ≥9)
  
node_results:
  node_1:
    findings: ___
    quality: ___
  node_2:
    findings: ___
    quality: ___
  node_3a:
    findings: ___
    quality: ___
  node_3b:
    findings: ___
    quality: ___

convergent_findings: ___ (issues found by 2+ nodes)
unique_findings: ___ (issues found by 1 node)
critical_discoveries: ___ (TOCTOU, cache collision, etc.)

hypothesis_validation:
  quality_target_87: [PASS|FAIL] (actual: ___)
  finding_count_target_48: [PASS|FAIL] (actual: ___)
  module_coverage_target_11: [PASS|FAIL] (actual: ___)
  critical_discovery: [YES|NO]

decision:
  all_4_criteria_met: [YES|NO]
  cluster_viable_as_default: [YES|NO]
  recommendation: [Free-tier cluster default | Tier 1 still needed | Hybrid approach]
```

---

## Success Criteria Reminder

After merging all findings, check:

### ✅ Criterion 1: Quality ≥ 85/100
- Average of 4 node scores
- Expected: 87/100 (approaching Haiku 88/100)
- Status: PASS / FAIL

### ✅ Criterion 2: Finding Count ≥ 45
- Sum of all nodes
- Expected: 48 findings (5-6x individual)
- Status: PASS / FAIL

### ✅ Criterion 3: Module Coverage ≥ 9/11
- Union of all modules touched across 4 nodes
- Expected: All 11 modules
- Status: PASS / FAIL

### ✅ Criterion 4: Critical Discovery
- TOCTOU race found (Node 2 target)
- OR cache collision found (Node 3B target)
- Expected: Both found
- Status: YES / NO / PARTIAL

---

## Decision Points

### If ALL 4 criteria met (Expected: 70% probability)
```
✅ Free-tier cluster ≥ Tier 1 quality
✅ FREE default viable (additional 97% cost savings)
✅ Annual cost: $27 → $0.10
✅ Quality: 87/100 (matches Haiku)
✅ Store repo memory: "Distributed cluster beats single expensive model"

Action: Update model dispatch strategy
  Phase 0: Free-tier cluster (discovery)
  Phase 3: Free-tier cluster (investigation)
  Phase 5: Free-tier cluster (standard review)
  Phase 6: Free-tier cluster (validation)
  Phase 4/7: Tier 1 for edge cases
```

### If 3/4 criteria met
```
✓ Cluster near Tier 1 (partial win)
✓ Use hybrid: Tier 1 for critical, free-tier for discovery
✓ Annual cost: $27 → $1-2 (92-96% savings)
✓ Quality: 82-85/100 (close to Haiku)

Action: Hybrid strategy
  Phase 0: Free-tier cluster (discovery)
  Phase 3: Free-tier cluster or Tier 1 (depends on finding count)
  Phase 5: Tier 1 (standard)
  Phase 6: Tier 1 (validation)
```

### If 2/4 criteria met
```
! Cluster > individual (modest improvement)
! Keep Tier 1 (Haiku) as default
! Free-tier cluster for Phase 0 only
! Annual cost: $27 (no change)

Action: Conservative approach
  Phase 0: Free-tier cluster (discovery, if time permits)
  Phase 3: Tier 1 (investigation)
  Phase 5: Tier 1 (standard)
  Phase 6: Tier 1 (validation)
```

### If < 2 criteria met
```
✗ Tier 1 needed for all work
✗ Free tier for Phase 0 discovery only
✗ Annual cost: $27 (no change)

Action: Maintain status quo
  Phase 0: Free tier (Phase 0, one model, hope for best)
  Phases 3-6: Tier 1 (Haiku)
```

---

## Ready to Launch?

### Pre-Launch Checklist
- [x] All 4 prompts copied and verified
- [x] Model parameters correct
- [x] Artifacts folder exists
- [x] Success criteria understood
- [x] Timeline clear (18 min parallel execution)
- [x] Results capture template ready

### Launch Command
Launch all 4 in rapid succession (within 5 seconds):

```
1. runSubagent with NODE 1 PROMPT + Model: GPT-4o
2. runSubagent with NODE 2 PROMPT + Model: GPT-4.1
3. runSubagent with NODE 3A PROMPT + Model: GPT-5 mini
4. runSubagent with NODE 3B PROMPT + Model: Raptor mini (Preview)
```

All run in PARALLEL. Wait ~18 min for all to complete.

---

## Go/No-Go for Launch

- [x] Documentation complete
- [x] Prompts prepared
- [x] Nodes configured
- [x] Success criteria defined
- [x] Results infrastructure ready
- [x] Timeline understood
- [x] Decision matrix prepared

**Status: GO FOR LAUNCH** 🚀

Let's execute Wave 2 cluster now!
