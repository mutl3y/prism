# Wave 3: Comprehensive Multi-Model Tier Testing — Final Design Matrix

**Purpose:** Establish definitive cost-benefit curves AND within-tier model variance for Tier 0 vs Tier 1 vs Tier 2

**Scope:** 3 tiers × 3 models per tier × 3 nodes = 27 total test runs (resumable, comparable format)

**Duration:** ~6 hours (3 tiers × 3 models × 40 min per model with sequential execution)

---

## Module Distribution (Consistent Across All Tiers)

| Node | Modules | Line Count | Focus Area |
|------|---------|-----------|-----------|
| **Node 1** | di.py, di_helpers.py, scanner_context.py | 950 lines | DI & Context Layer |
| **Node 2** | variable_discovery.py, feature_detector.py, task_extract_adapters.py | 890 lines | Extraction & Detection |
| **Node 3** | scan_cache.py, events.py, scan_request.py | 680 lines | Cache, Events & Requests |
| | **TOTAL: 8 modules** | **2,520 lines** | **Full scope** |

---

## Test Matrix: 3 Tiers × Multiple Models × 3 Nodes (30 Runs + Decision Gate)

```
WAVE 3 MULTI-MODEL TEST MATRIX
═══════════════════════════════════════════════════════════════════════════

TIER 0 (FREE) — 4 models × 3 nodes each = 12 runs (Deep Free-Tier Analysis)
───────────────────────────────────────────────────────────────────────────

MODEL 1: GPT-4o
  T0M1-Node1 │ GPT-4o   │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T0M1-Node2 │ GPT-4o   │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T0M1-Node3 │ GPT-4o   │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 1A (parallel) ───────────────┘ 36 min

MODEL 2: GPT-4.1
  T0M2-Node1 │ GPT-4.1  │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T0M2-Node2 │ GPT-4.1  │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T0M2-Node3 │ GPT-4.1  │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 1B (parallel) ───────────────┘ 36 min

MODEL 3: GPT-5 mini
  T0M3-Node1 │ GPT-5m   │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T0M3-Node2 │ GPT-5m   │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T0M3-Node3 │ GPT-5m   │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 1C (parallel) ───────────────┘ 36 min

MODEL 4: Raptor mini
  T0M4-Node1 │ Raptorm  │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T0M4-Node2 │ Raptorm  │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T0M4-Node3 │ Raptorm  │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 1D (parallel) ───────────────┘ 36 min
              └─ Tier 0 Complete (subtotal: 12 runs) ──────────┘ 144 min

TIER 1 (0.33x) — 3 models × 3 nodes each = 9 runs
───────────────────────────────────────────────────────────────────────────

MODEL 1: Claude Haiku 4.5
  T1M1-Node1 │ Haiku45  │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T1M1-Node2 │ Haiku45  │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T1M1-Node3 │ Haiku45  │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 2A (parallel) ───────────────┘ 36 min

MODEL 2: Grok Code Fast 1
  T1M2-Node1 │ Grok1    │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T1M2-Node2 │ Grok1    │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T1M2-Node3 │ Grok1    │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 2B (parallel) ───────────────┘ 36 min

MODEL 3: Gemini 3 Flash (Preview)
  T1M3-Node1 │ G3Flash  │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T1M3-Node2 │ G3Flash  │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T1M3-Node3 │ G3Flash  │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 2C (parallel) ───────────────┘ 36 min
              └─ Tier 1 Complete (subtotal: 9 runs) ────────────┘ 108 min

═══════════════════════════════════════════════════════════════════════════
🛑 DECISION GATE: CHECKPOINT BEFORE TIER 2 EXECUTION
═══════════════════════════════════════════════════════════════════════════

REVIEW REQUIRED (Duration: ~30 min team analysis)
- Analyze T0 results: Are free models sufficient? Which is best (GPT-4o vs 4.1 vs 5m vs Raptor)?
- Analyze T1 results: Quality improvement over T0? Worth 0.33x cost?
- Cost-benefit question: "Should we test Tier 2 (1x cost) or stop here?"
- Risk analysis: Will higher-reasoning models be worth the cost increase?

DECISION OPTIONS:
  ✅ APPROVE → Proceed to Tier 2 (Phase 3, 108 min, +$0.027)
  ⏸️  PAUSE → Hold on T2, analyze T0+T1 deeper first
  ❌ STOP → Don't test Tier 2, proceed to analysis with T0+T1 only

TOTAL IF TIER 2 APPROVED: 30 runs | 6+ hours | $0.036 cost
TOTAL IF TIER 2 SKIPPED: 21 runs | 4.2 hours | $0.009 cost (T0 + T1 only)

───────────────────────────────────────────────────────────────────────────

IF APPROVED: Continue to Phase 3

TIER 2 (1x) — 3 models × 3 nodes each = 9 runs (Conditional on Gate Approval)
───────────────────────────────────────────────────────────────────────────

MODEL 1: Claude Sonnet 4.5
  T2M1-Node1 │ Sonnet45 │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T2M1-Node2 │ Sonnet45 │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T2M1-Node3 │ Sonnet45 │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 3A (parallel) ───────────────┘ 36 min

MODEL 2: GPT-5.4
  T2M2-Node1 │ GPT-5.4  │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T2M2-Node2 │ GPT-5.4  │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T2M2-Node3 │ GPT-5.4  │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 3B (parallel) ───────────────┘ 36 min

MODEL 3: Gemini 2.5 Pro
  T2M3-Node1 │ G2.5Pro  │ Node 1 Prompt (DI & Context)      │ 950L  │ ~12 min
  T2M3-Node2 │ G2.5Pro  │ Node 2 Prompt (Extraction)        │ 890L  │ ~12 min
  T2M3-Node3 │ G2.5Pro  │ Node 3 Prompt (Cache, Events)     │ 680L  │ ~12 min
              └─ Phase 3C (parallel) ───────────────┘ 36 min
              └─ Tier 2 Complete (subtotal: 9 runs) ────────────┘ 108 min

═══════════════════════════════════════════════════════════════════════════
TOTAL: 21-30 RUNS | 4.2-6 HOURS | $0.009-$0.036 COST (Depends on Gate Decision)
═══════════════════════════════════════════════════════════════════════════
```

---

## Execution Order (Sequential Tiers → Sequential Models → Parallel Nodes → Decision Gate)

### Phase 1: Tier 0 Deep Analysis (4 Free Models = 12 Runs)

**Phase 1A: GPT-4o × 3 nodes (36 min)**
- Execution: Launch T0M1-Node1, T0M1-Node2, T0M1-Node3 in parallel
- Output: tier0-gpt4o-node[1-3]-findings.yaml

**Phase 1B: GPT-4.1 × 3 nodes (36 min)**
- Execution: Launch T0M2-Node1, T0M2-Node2, T0M2-Node3 in parallel
- Output: tier0-gpt41-node[1-3]-findings.yaml

**Phase 1C: GPT-5 mini × 3 nodes (36 min)**
- Execution: Launch T0M3-Node1, T0M3-Node2, T0M3-Node3 in parallel
- Output: tier0-gpt5m-node[1-3]-findings.yaml

**Phase 1D: Raptor mini × 3 nodes (36 min)**
- Execution: Launch T0M4-Node1, T0M4-Node2, T0M4-Node3 in parallel
- Output: tier0-raptor-node[1-3]-findings.yaml
- **Tier 0 Complete: 144 minutes, 12 files saved**

### Phase 2: Tier 1 Comparable (3 Models = 9 Runs)

**Phase 2A: Claude Haiku 4.5 × 3 nodes (36 min)**
- Execution: Launch T1M1-Node1, T1M1-Node2, T1M1-Node3 in parallel
- Output: tier1-haiku45-node[1-3]-findings.yaml

**Phase 2B: Grok Code Fast 1 × 3 nodes (36 min)**
- Execution: Launch T1M2-Node1, T1M2-Node2, T1M2-Node3 in parallel
- Output: tier1-grok1-node[1-3]-findings.yaml

**Phase 2C: Gemini 3 Flash (Preview) × 3 nodes (36 min)**
- Execution: Launch T1M3-Node1, T1M3-Node2, T1M3-Node3 in parallel
- Output: tier1-g3flash-node[1-3]-findings.yaml
- **Tier 1 Complete: 108 minutes, 9 files saved**

---

## 🛑 DECISION GATE CHECKPOINT (30 min review)

**Required Analysis Before Tier 2:**

1. **Tier 0 Findings Summary:** How many findings per model? Which free model is best?
   - GPT-4o vs GPT-4.1 vs GPT-5 mini vs Raptor mini quality comparison
   - Are findings consistent across free tier or model-specific?

2. **Tier 1 Findings Summary:** Quality jump from T0→T1?
   - Haiku vs Grok vs Gemini variance at 0.33x cost
   - Additional findings vs T0? Worth the cost?

3. **Cost-Benefit Decision:**
   - Finding count & quality gains per dollar?
   - Is T1 saturation point (diminishing returns from T2)?
   - Will higher-reasoning models in T2 justify 3x cost increase?

4. **Risk Assessment:**
   - Reasoning models historically drift on structured output (see Grok issue)
   - Cost volatility (Claude Opus peaked at $0.045, newer high-reasoning at variable pricing)

**VOTE REQUIRED:**
- ✅ **APPROVE Tier 2** → Continue to Phase 3 (adds 108 min, +$0.027)
- 🟡 **DEEP DIVE** → Pause, run additional T0/T1 analysis before deciding
- ❌ **STOP (T0+T1 sufficient)** → Skip T2, proceed to cross-tier analysis

---

## Phase 3: Tier 2 (CONDITIONAL - Requires Decision Gate Approval)

**IF TIER 2 APPROVED: 3 Models = 9 Runs**

**Phase 3A: Claude Sonnet 4.5 × 3 nodes (36 min)**
- Execution: Launch T2M1-Node1, T2M1-Node2, T2M1-Node3 in parallel
- Output: tier2-sonnet45-node[1-3]-findings.yaml

**Phase 3B: GPT-5.4 × 3 nodes (36 min)**
- Execution: Launch T2M2-Node1, T2M2-Node2, T2M2-Node3 in parallel
- Output: tier2-gpt54-node[1-3]-findings.yaml

**Phase 3C: Gemini 2.5 Pro × 3 nodes (36 min)**
- Execution: Launch T2M3-Node1, T2M3-Node2, T2M3-Node3 in parallel
- Output: tier2-g25pro-node[1-3]-findings.yaml
- **Tier 2 Complete: 108 minutes, 9 files saved (if approved)**

---

## Prompt Template (Identical for All 27 Nodes Across All Tiers & Models)

### Node 1 Prompt: DI & Context Layer

**Modules:** di.py (320 lines), di_helpers.py (180 lines), scanner_context.py (450 lines)

**Analysis Points:**
1. Type safety & erasure (cast() usage, protocol enforcement)
2. DI container god-object antipattern (coupling, testability)
3. Lazy imports and circular dependency workarounds
4. Policy flow ownership (where set vs where checked)
5. Error handling contracts and silent failures
6. Mocking/testability complexity from current design

**Output Format:** YAML with strict schema
```yaml
model_used: [exact model name]
tier: [0|1|2]
node: 1
findings:
  - id: GILF-{TIER}-{NODE}-{NN}
    severity: CRITICAL|HIGH|MEDIUM|LOW
    category: architecture|type-safety|ownership|error-handling|testability
    location: "[file.py:line-line]"
    issue: "[concise issue title]"
    root_cause: "[why this exists]"
    impact: "[what breaks or degrades]"
    confidence: 1-100
    fix_suggestion: "[concrete actionable fix]"
```

### Node 2 Prompt: Extraction & Detection Layer

**Modules:** variable_discovery.py (280 lines), feature_detector.py (320 lines), task_extract_adapters.py (290 lines)

**Analysis Points:**
1. Concurrency & thread safety (TOCTOU races, check-then-act patterns)
2. Data flow consistency (shared state, invariant violations)
3. Caching strategy (key collisions, TTL, invalidation)
4. Error handling in this layer (exceptions, data loss, silent failures)
5. Policy application & marker ownership
6. Performance optimizations & scalability

**Output Format:** Same YAML schema (id suffix indicates node 2)

### Node 3 Prompt: Cache, Events & Requests

**Modules:** scan_cache.py (160 lines), events.py (140 lines), scan_request.py (380 lines)

**Analysis Points:**
1. Cache safety (key canonicalization, collision risk, TTL logic)
2. Event bus reliability (listener failures, thread-safety, state corruption)
3. Copy semantics (shallow vs deep, shared references, mutability)
4. Request validation & normalization (data contracts)
5. Exception handling & silent failures (missing try-catch, swallowed errors)
6. Performance under load & scalability concerns

**Output Format:** Same YAML schema (id suffix indicates node 3)

---

## Result Comparison Matrix (After All Phases Complete)

```
CROSS-TIER ANALYSIS
═══════════════════════════════════════════════════════════════════════════

                 Node 1 (DI)    Node 2 (Extract)    Node 3 (Cache)    TOTAL
Tier 0 (FREE)    ? findings     ? findings          ? findings        ? findings
                 ?/100 quality  ?/100 quality       ?/100 quality     ?/100 quality

Tier 1 (0.33x)   ? findings     ? findings          ? findings        ? findings
                 ?/100 quality  ?/100 quality       ?/100 quality     ?/100 quality

Tier 2 (1x)      ? findings     ? findings          ? findings        ? findings
                 ?/100 quality  ?/100 quality       ?/100 quality     ?/100 quality

DELTA T1-T0      +? findings    +? findings         +? findings       +? findings
                 +? quality     +? quality          +? quality        +? quality

DELTA T2-T1      +? findings    +? findings         +? findings       +? findings
                 +? quality     +? quality          +? quality        +? quality

═══════════════════════════════════════════════════════════════════════════
```

---

## Decision Gates (Conditional - Some Gates Depend on Phase 3 Approval)

### 🛑 PRE-PHASE-3 GATE: Tier 2 Worth Testing? (TEAM DECISION)
- **Context:** Phase 1+2 complete, 21 findings files saved (T0: 12 runs, T1: 9 runs)
- **Questions:**
  1. Within Tier 0, which model is best (GPT-4o/4.1/5m/Raptor)?
  2. Does Tier 1 provide sufficient quality jump for 0.33x cost?
  3. Risk: Tier 2 costs 3x more, and reasoning models have format/cost volatility
- **Options:**
  - ✅ **APPROVE** → Continue to Phase 3 (Tier 2 testing, +$0.027 cost)
  - 🟡 **ANALYSIS LOOP** → Deep dive on T0+T1 before deciding
  - ❌ **REJECT** → Stop here, use T0+T1 for cost-benefit analysis
- **Result:** [PENDING USER DECISION]

### Gate 1: Tier 1 vs Tier 0 (Is $0.003/cycle worth it?)
- **Pass Criteria:** Tier 1 avg quality ≥ +3 points over Tier 0 avg AND Tier 1 avg +8 findings
- **Result:** [PENDING — after Phase 2 completion]
- **Decision:** If PASS, validates Tier 1 as standard tier. If FAIL, use Tier 0 for routine reviews.

### Gate 2: Tier 2 vs Tier 1 (Is $0.002 more worth it?) — CONDITIONAL
- **Prerequisite:** Phase 3 approved at pre-phase gate
- **Pass Criteria:** Tier 2 avg quality ≥ +2 points over Tier 1 avg AND Tier 2 avg +5 findings
- **Result:** [PENDING — only if Phase 3 approved]
- **Decision:** If PASS, validates tiered strategy. If FAIL, Tier 1 is cost-optimal.

### Gate 3: Critical Finding Convergence (Do all tiers find the same bugs?)
- **Prerequisite:** Phase 3 completed (or comparative analysis with available phases)
- **Pass Criteria:** TOCTOU race + cache collision consensus ≥70% across available tiers
- **Result:** [PENDING]
- **Decision:** Validates multi-tier strategy if PASS

### Gate 4: Cost-Benefit ROI (Annual savings potential?)
- **Pass Criteria:** T0 + selective T1 = 95%+ coverage at $0.004/cycle
- **Result:** [PENDING]
- **Decision:** Approve hybrid strategy ($1,400 annual savings vs Tier 2-always) if PASS

---

## Resumable Checkpoints

### ✅ Checkpoint 1: Phase 1 Complete (Tier 0 Deep Analysis)
- **Duration:** 144 minutes (4 models × 36 min each)
- **Files:** 12 YAML artifacts (tier0-gpt4o-node[1-3], tier0-gpt41-node[1-3], tier0-gpt5m-node[1-3], tier0-raptor-node[1-3])
- **Storage:** /raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/wave3-results/tier0/
- **Analysis:** Free-tier model comparison (which is best?), finding counts per model
- **Next:** Proceed to Phase 2

### ✅ Checkpoint 2: Phase 2 Complete (Tier 1 Analysis)
- **Duration:** 108 minutes (3 models × 36 min each)
- **Files:** 9 YAML artifacts (tier1-haiku45-node[1-3], tier1-grok1-node[1-3], tier1-g3flash-node[1-3])
- **Storage:** /raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/wave3-results/tier1/
- **Analysis:** Tier 1 model variance, quality improvement vs Tier 0, cost-justification assessment
- **🛑 NEXT:** **DECISION GATE — TEAM REVIEW REQUIRED** (Do NOT proceed to Phase 3 without approval)

### 🛑 Checkpoint 3: DECISION GATE (Team Review & Vote)
- **Duration:** ~30 minutes
- **Analysis Required:**
  1. Tier 0 finding count & quality per model (identify best free model)
  2. Tier 0→T1 quality delta per node
  3. Cost-benefit: Does $0.001 per run justify ~+N findings?
  4. Risk assessment: Tier 2 testing vs stopping at T0+T1
- **Vote Required:**
  - ✅ **APPROVE PHASE 3** → Continue (adds 108 min + $0.027)
  - ⏸️ **HOLD** → More analysis needed, don't proceed yet
  - ❌ **STOP** → Use T0+T1 only, skip Tier 2 testing
- **Action:** If STOP, jump to Checkpoint 5. If APPROVE, proceed to Phase 3.
- **Result:** [PENDING USER DECISION]

### ✅ Checkpoint 4: Phase 3 Complete (Tier 2 Analysis) — CONDITIONAL
- **Prerequisite:** Checkpoint 3 vote = APPROVE
- **Duration:** 108 minutes (3 models × 36 min each)
- **Files:** 9 YAML artifacts (tier2-sonnet45-node[1-3], tier2-gpt54-node[1-3], tier2-g25pro-node[1-3])
- **Storage:** /raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/wave3-results/tier2/
- **Status:** 30 findings files total (if Phase 3 approved) OR 21 (if Phase 3 skipped)
- **Next:** Cross-tier analysis

### ✅ Checkpoint 5: Cross-Tier Analysis Complete
- **Duration:** ~60 minutes (comprehensive comparison matrix + gates validation)
- **Output:**
  - Result comparison matrix (all completed phases, model averages, tier deltas)
  - Decision gates 1-4 validation
  - Annual savings projection
  - Recommended Mutl3y model dispatch strategy
- **File:** wave3-analysis-report.md
- **Storage:** Same wave3-results/ directory
- **Status:** Wave 3 COMPLETE ✅

---

## Tracking & Validation

### Per-Node Validation (After Each Node Completes)
```yaml
checksum:
  node_id: "T0-Node1"
  model: "GPT-4o"
  tier: 0
  total_findings: [number]
  critical_count: [number]
  high_count: [number]
  medium_count: [number]
  low_count: [number]
  avg_quality: [0-100]
  output_file: "tier0-node1-findings.yaml"
  completion_time: "[ISO-8601]"
  status: "COMPLETE|FAILED|RUNNING"
```

### Per-Phase Summary (After Each Phase Completes)
```yaml
phase_1_tier0_summary:
  total_runs: 3
  successful_runs: 3
  failed_runs: 0
  total_findings: [sum of all nodes]
  avg_quality_score: [average across nodes]
  nodes_completed: [T0-Node1, T0-Node2, T0-Node3]
  phase_status: "COMPLETE|INCOMPLETE"
  next_action: "PROCEED_TO_PHASE_2"
```

---

## Cost Estimate

| Tier | Model | Runs | Cost/Run | Total Cost |
|------|-------|------|----------|-----------|
| **0** | GPT-4o | 3 | $0.000 | $0.000 |
| **1** | Haiku 4.5 | 3 | $0.001 | $0.003 |
| **2** | Sonnet 4.5 | 3 | $0.003 | $0.009 |
| | | **TOTAL** | | **$0.012** |

---

## Validation Checklist Before Execution

- [ ] All 3 prompts created (Node 1, 2, 3)
- [ ] Prompts include explicit output format constraints
- [ ] YAML schema defined for findings
- [ ] Results directory created: wave3-results/
- [ ] Checksum tracking file prepared
- [ ] Phase 1 scheduled (Tier 0)
- [ ] Phase 2 scheduled (Tier 1)
- [ ] Phase 3 scheduled (Tier 2)
- [ ] Analysis template prepared (comparative metrics)
- [ ] Decision gate thresholds confirmed
- [ ] Resume procedure documented

---

## Success Criteria

✅ **Wave 3 is successful if:**
1. All 9 nodes execute successfully (no format failures)
2. Decision gates 1-4 provide clear cost-benefit signals
3. Results enable hybrid Mutl3y strategy (Tier 0 default + Tier 1 for high-risk)
4. Annual savings projection quantified (target: $1,200+)
5. All findings data preserved in repo (resumable from any checkpoint)

---

## Next Steps (After Approval)

1. Confirm this matrix is the correct design
2. Create the 3 unified prompts
3. Prepare wave3-results/ directory
4. Execute Phase 1 (Tier 0 × 3 nodes)
5. Execute Phase 2 (Tier 1 × 3 nodes)
6. Execute Phase 3 (Tier 2 × 3 nodes)
7. Generate cross-tier analysis report
8. Present decision matrix to stakeholders
