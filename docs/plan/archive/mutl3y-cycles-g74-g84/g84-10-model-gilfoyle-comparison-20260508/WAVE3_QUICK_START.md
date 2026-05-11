# Wave 3: Tier 1 Cluster — Quick Start

**Objective:** Test same distributed architecture with Tier 1 models to establish cost-benefit curve  
**Hypothesis:** Tier 1 delivers 90-92/100 quality, 48-60 findings, justifies $0.004/review cost  
**Timeline:** ~100 minutes (sequential execution)  
**Cost:** ~$0.004/review  

---

## Why Wave 3?

**Wave 2 Result:** Free tier = Tier 1 quality (88.3 vs 88)  
**Wave 3 Question:** Does Tier 1 with distributed focus > free tier?  
**Decision It Enables:** When to use free vs Tier 1 vs escalate higher

---

## 4-Node Tier 1 Architecture

### Node 1: Claude Haiku 4.5 (Architecture Expert)
- **Focus:** DI patterns, ownership, type safety
- **Modules:** di.py, scanner_context.py, di_helpers.py
- **Why Haiku:** Found TOCTOU in Wave 1 (only model to find it)
- **Expected findings:** 12-18 (deeper than Wave 2's 5)

### Node 2: Grok Code Fast 1 (Concurrency Specialist)
- **Focus:** Concurrency races, cache safety, threading
- **Modules:** variable_discovery.py, feature_detector.py
- **Why Grok:** Fast, concurrency-focused, cheaper than GPT-4.1
- **Expected findings:** 10-14 (match/exceed Wave 2's 11)

### Node 3A: Claude Haiku 4.5 (Ownership & Contracts)
- **Focus:** Layer boundaries, API design, validation
- **Modules:** task_extract_adapters.py, scan_request.py, execution_request_builder.py, protocols_runtime.py
- **Why Haiku:** Strong contract analysis, found marker-prefix in Wave 1
- **Expected findings:** 12-15 (match Wave 2's pending)

### Node 3B: Grok Code Fast 1 (Performance & Cache)
- **Focus:** Cache safety, performance, exception handling
- **Modules:** scan_cache.py, events.py, scan_request.py
- **Why Grok:** Purpose-built performance expert, cheaper
- **Expected findings:** 10-13 (match/exceed Wave 2's 12)

---

## Key Differences from Wave 2

| Aspect | Wave 2 (Free) | Wave 3 (Tier 1) |
|--------|---------------|-----------------|
| Models | GPT-4o, GPT-4.1, GPT-5 mini, Raptor mini | Haiku, Grok, Haiku, Grok |
| Cost | $0 | $0.004 |
| Strategy | Breadth through distribution | Depth through specialization |
| Expected Quality | 88.3/100 | 90-92/100 |
| Expected Findings | 38 | 48-60 |
| New Angle | Deepen Wave 2 findings, fix strategies | Policy flow, layer boundaries |

---

## Expected Results

### Quality Progression
```
Wave 1 (all 13 models): 81/100 average
Wave 1 Haiku only: 88/100
Wave 2 (free cluster): 88.3/100
Wave 3 (Tier 1 cluster): 90-92/100 (expected)
Wave 1 Tier 4 (Opus): 98/100
```

### Finding Count Progression
```
Wave 1 average model: 13-15 findings
Wave 1 Haiku: ~9 findings
Wave 2 (free cluster): 38 findings
Wave 3 (Tier 1 cluster): 48-60 findings (expected)
Wave 1 Tier 4 (Opus): ~20 findings
```

### Cost-Benefit
```
Current strategy (Tier 4 always):
  Cost: $27/review
  Findings: ~12
  Cost per finding: $2.25

Wave 2 (free cluster):
  Cost: $0
  Findings: 38
  Cost per finding: $0.00

Wave 3 (Tier 1 cluster):
  Cost: $0.004
  Findings: 48-60
  Cost per finding: $0.00007 (negligible)

Hybrid (free + Tier 1 for strategic reviews):
  Cost: $0.10/year
  Findings: 2,000-2,500/year
  Cost per finding: $0.00005
  Annual savings vs Tier 4: $1,403.90
```

---

## Execution Checklist (Parallel)

### Pre-Execution
- [ ] Read WAVE3_TIER1_CLUSTER_PLAN.md for context
- [ ] Copy all 4 node prompts (ready to paste in parallel)
- [ ] Have artifacts/ folder ready for YAML output

### Launch All 4 Nodes Simultaneously

**Node 1: Claude Haiku 4.5 (Architecture)**
- [ ] Copy NODE 1 PROMPT from plan
- [ ] Send to runSubagent with model "Claude Haiku 4.5 (copilot)"

**Node 2: Grok Code Fast 1 (Concurrency)**
- [ ] Copy NODE 2 PROMPT from plan
- [ ] Send to runSubagent with model "Grok Code Fast 1 (copilot)"

**Node 3A: Claude Haiku 4.5 (Ownership)**
- [ ] Copy NODE 3A PROMPT from plan
- [ ] Send to runSubagent with model "Claude Haiku 4.5 (copilot)"

**Node 3B: Grok Code Fast 1 (Cache)**
- [ ] Copy NODE 3B PROMPT from plan
- [ ] Send to runSubagent with model "Grok Code Fast 1 (copilot)"

⏱️ **Wait ~18 minutes for all 4 to complete**

### Merge & Analysis (12 min)
- [ ] Verify all 4 YAML files exist
- [ ] Calculate cluster metrics
- [ ] Compare to Wave 2 baseline
- [ ] Create WAVE3_CLUSTER_RESULTS.md
- [ ] Evaluate escalation matrix

---

## Decision Framework After Wave 3

### If Quality ≥ 90/100:
✅ Tier 1 justified for accuracy-critical work  
Action: Add Tier 1 to default strategy for strategic reviews

### If Findings ≥ 48:
✅ Tier 1 adds sufficient depth  
Action: Use Tier 1 for complex domains

### If Convergence ≥ 70%:
✅ Architecture validated across tiers  
Action: Confidence in distributed approach

### If Cost <$0.01:
✅ Cost negligible compared to Wave 2  
Action: Tier 1 becomes affordable alternative

### Likely Outcome:
✅ **Hybrid Strategy:**
- Free tier: 90% of work (cost $0)
- Tier 1: 10% of strategic reviews (cost $0.004 each)
- Tier 4: Reserved for edge cases only
- Annual cost: $0.20-$0.40 (vs $1,404 current)
- Annual savings: $1,403.60-$1,403.80 (99.97%)

---

## Files Needed

Location: `/raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/`

- WAVE3_TIER1_CLUSTER_PLAN.md (contains all 4 node prompts)
- NODE 1-4 PROMPTS (copy from plan file)

---

## Ready to Execute?

Option A (Immediate):
1. Open WAVE3_TIER1_CLUSTER_PLAN.md
2. Find "Node 1 Prompt — Claude Haiku 4.5"
3. Copy the prompt
4. Send to runSubagent with model "Claude Haiku 4.5 (copilot)"
5. Repeat for Nodes 2, 3A, 3B

Option B (Staged):
1. Review this file
2. Schedule Wave 3 for specific time
3. Block 2 hours for sequential execution
4. Set reminder for merge & analysis

**Let's answer: When should we use free tier vs Tier 1 vs higher?**
