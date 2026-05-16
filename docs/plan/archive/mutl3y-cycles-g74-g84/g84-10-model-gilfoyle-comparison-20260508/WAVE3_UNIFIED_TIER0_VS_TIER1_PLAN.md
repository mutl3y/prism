# Wave 3: Unified Tier 0 vs Tier 1 Comparison Study

**Objective:** True capability comparison using identical prompts across two tiers  
**Design:** 3-node distributed cluster, same prompts for both Tier 0 and Tier 1  
**Timeline:** Run Tier 0 cluster, then Tier 1 cluster (same prompts), compare results  
**Cost:** ~$0.003 (Tier 0 free) + ~$0.003 (Tier 1) = $0.006 total

---

## Module Distribution: 3-Node Cluster

### Node 1: DI & Context Layer
**Modules:** 
- di.py (320 lines)
- di_helpers.py (180 lines)
- scanner_context.py (450 lines)
**Total:** 950 lines

### Node 2: Extraction & Detection Layer
**Modules:**
- variable_discovery.py (280 lines)
- feature_detector.py (320 lines)
- task_extract_adapters.py (290 lines)
**Total:** 890 lines

### Node 3: Cache, Events & Requests
**Modules:**
- scan_cache.py (160 lines)
- events.py (140 lines)
- scan_request.py (380 lines)
**Total:** 680 lines

**Grand Total:** 8 modules, 2,520 lines (3 nodes, balanced distribution)

---

## Unified Prompts (Same for All Models in Both Tiers)

### Node 1 Unified Prompt: DI & Context Layer

```
## Code Review: DI & Context Layer

You are a code reviewer analyzing a Python Ansible scanner.
Review these modules for architecture issues, type safety, concurrency, and maintainability.

### Target Modules (950 lines)
- di.py (320 lines): Dependency injection container, factory functions
- di_helpers.py (180 lines): DI helper utilities, lazy imports
- scanner_context.py (450 lines): Scanner execution context, validation

### Analysis Points

1. **Type Safety & Erasure**
   - Where is type information lost via Any, cast(), or untyped parameters?
   - Are protocols properly enforced at boundaries?
   - Can type erasure be eliminated safely?

2. **DI Architecture & God Objects**
   - Does DIContainer have too many responsibilities?
   - What's the coupling between DI and scanner_context?
   - How many layers depend on the container?
   - What breaks if one factory fails?

3. **Lazy Imports & Initialization**
   - Are there race conditions in lazy initialization?
   - What happens if two threads access a lazy-loaded dependency simultaneously?
   - Are lazy imports worth the complexity?

4. **Policy & Configuration**
   - How is policy_context managed across the DI layer?
   - Where are policy decisions made vs validated?
   - Can policies be set once instead of checked multiple times?

5. **Error Handling**
   - What happens on DI initialization failure?
   - Are error contracts clear (ValueError, KeyError, etc)?
   - Can errors propagate clearly or are they swallowed?

6. **Testability & Mocking**
   - How difficult is it to mock the DI container for testing?
   - Are there circular dependencies that make testing hard?
   - Can components be tested in isolation?

### Success Criteria
✓ All 3 modules analyzed
✓ Type safety issues identified with locations
✓ DI architecture risks quantified
✓ Concurrency issues flagged with failure scenarios
✓ Policy ownership clarified
✓ Error handling gaps identified
✓ 5-15 findings total (quality > quantity)
✓ Confidence scores for each finding

### Output Format
Return YAML with: id, severity (CRITICAL/HIGH/MEDIUM/LOW), category, location (file:line), issue, root_cause, impact, confidence (0-100), fix_suggestion

### Notes
- Focus on root causes, not symptoms
- Prioritize issues affecting multiple components
- Flag architectural debt vs implementation bugs separately
- Explain why issues matter (not just "this is bad")
```

### Node 2 Unified Prompt: Extraction & Detection Layer

```
## Code Review: Extraction & Detection Layer

You are a code reviewer analyzing a Python Ansible scanner.
Review these modules for architecture issues, concurrency, data flow correctness, and performance.

### Target Modules (890 lines)
- variable_discovery.py (280 lines): Variable discovery orchestration
- feature_detector.py (320 lines): Feature detection and caching
- task_extract_adapters.py (290 lines): Task extraction adapters

### Analysis Points

1. **Concurrency & Thread Safety**
   - What check-then-act patterns exist? (e.g., cache misses)
   - Are there TOCTOU (time-of-check-time-of-use) races?
   - What happens if two threads access the same cache entry?
   - Are mutations guarded by locks or atomic operations?

2. **Data Flow & State Management**
   - How does data flow through variable_discovery → feature_detector → adapters?
   - What state is shared between components?
   - Can state become inconsistent if operations interleave?
   - Are there invariants that might be violated?

3. **Caching Strategy**
   - How are cache keys constructed? (Risk of collision?)
   - What's the cache TTL? (Stale data risk?)
   - How is cache invalidation handled?
   - Can cache operations corrupt or lose data?

4. **Error Handling & Failure Modes**
   - What happens if feature detection fails mid-way?
   - Are exceptions caught and swallowed?
   - Can errors cause data loss or inconsistent state?
   - Are error contracts clear?

5. **Policy & Conditional Logic**
   - How are policies applied in this layer?
   - Are there silent fallbacks or missing error paths?
   - Can policies conflict with data flow?
   - Is policy enforcement testable?

6. **Performance & Optimization**
   - Are there unnecessary iterations or re-computations?
   - Can expensive operations be cached or batched?
   - Are there algorithmic inefficiencies?
   - What's the memory footprint of data structures?

### Success Criteria
✓ All 3 modules analyzed
✓ Concurrency issues identified with failure scenarios
✓ Data flow consistency issues flagged
✓ Cache safety evaluated
✓ Error handling gaps identified
✓ Performance bottlenecks noted
✓ 5-15 findings total
✓ Confidence scores for each finding

### Output Format
Return YAML with: id, severity (CRITICAL/HIGH/MEDIUM/LOW), category, location (file:line), issue, root_cause, impact, confidence (0-100), fix_suggestion

### Notes
- TOCTOU races are high-priority (mark as CRITICAL if found)
- State corruption is worse than performance issues
- Silent failures are dangerous (flag these)
- Explain cascading failure scenarios if possible
```

### Node 3 Unified Prompt: Cache, Events & Requests

```
## Code Review: Cache, Events & Requests Layer

You are a code reviewer analyzing a Python Ansible scanner.
Review these modules for performance, reliability, data integrity, and maintainability.

### Target Modules (680 lines)
- scan_cache.py (160 lines): Caching layer
- events.py (140 lines): Event bus / observer pattern
- scan_request.py (380 lines): Scan request handling and validation

### Analysis Points

1. **Cache Safety & Correctness**
   - How are cache keys constructed? (Collision risk?)
   - Is cache invalidation correct? (Stale data risk?)
   - What data is cached and for how long? (TTL correctness?)
   - Can cache state become inconsistent?

2. **Event Bus Reliability**
   - How are listeners registered and called?
   - What happens if a listener fails? (Swallowed errors?)
   - Can listener failures affect other listeners?
   - Is the event bus thread-safe?

3. **Copy Semantics & Shallow Copies**
   - Where are objects copied (shallow vs deep)?
   - Are there unintended shared references?
   - Can mutations corrupt shared state?
   - Is copy behavior documented?

4. **Request Validation & Normalization**
   - Where is input validated?
   - What assumptions are made about request structure?
   - Can invalid requests pass through?
   - Are error messages clear?

5. **Exception Handling & Silent Failures**
   - Are exceptions caught and swallowed?
   - What exceptions should propagate vs be handled?
   - Can errors cause data loss?
   - Are there missing error paths?

6. **Performance & Type Safety**
   - Are there unnecessary allocations or copies?
   - Can operations be optimized?
   - Are type conversions safe? (e.g., dict to string)
   - What's the performance profile under load?

### Success Criteria
✓ All 3 modules analyzed
✓ Cache safety evaluated with concrete scenarios
✓ Event bus reliability assessed
✓ Copy semantics clarified with mutation risks
✓ Validation coverage identified
✓ Exception handling gaps flagged
✓ Performance opportunities noted
✓ 5-15 findings total
✓ Confidence scores for each finding

### Output Format
Return YAML with: id, severity (CRITICAL/HIGH/MEDIUM/LOW), category, location (file:line), issue, root_cause, impact, confidence (0-100), fix_suggestion

### Notes
- Cache collisions and stale data are high-priority
- Silent exception swallowing is dangerous (flag these)
- Shallow copy bugs are subtle but critical
- Type safety issues in request handling are important
- Performance issues are lower priority than correctness
```

---

## Cluster Execution Plan

### Phase 1: Tier 0 Baseline (Free Tier) — 3 Models

**Node 1 (Free Model A):** di.py, di_helpers.py, scanner_context.py
- Select from: GPT-4o, GPT-4.1, GPT-5 mini (same 3 models as Wave 2 represented)

**Node 2 (Free Model B):** variable_discovery.py, feature_detector.py, task_extract_adapters.py

**Node 3 (Free Model C):** scan_cache.py, events.py, scan_request.py

All 3 use **same unified prompts above** (just parametrized for each module set)

### Phase 2: Tier 1 Comparable (Tier 1) — 3 Models

**Node 1 (Tier 1 Model A):** di.py, di_helpers.py, scanner_context.py (Claude Haiku 4.5)
- **Same prompt as Tier 0 Node 1**

**Node 2 (Tier 1 Model B):** variable_discovery.py, feature_detector.py, task_extract_adapters.py (Grok Code Fast 1)
- **Same prompt as Tier 0 Node 2**

**Node 3 (Tier 1 Model C):** scan_cache.py, events.py, scan_request.py (Grok Code Fast 1)
- **Same prompt as Tier 0 Node 3**

---

## Comparison Framework

After both clusters execute, we can compare:

### Model-to-Model (Same prompt, same files, different tier)

| Node | Module Set | Tier 0 Model | Tier 1 Model | Quality Δ | Findings Δ |
|------|-----------|--------------|--------------|-----------|-----------|
| 1 | DI & Context | Free Tier A | Haiku 4.5 | ? | ? |
| 2 | Extract & Detect | Free Tier B | Grok 1 | ? | ? |
| 3 | Cache & Events | Free Tier C | Grok 1 | ? | ? |

### Key Questions Answered

**Q1: Does Tier 1 consistently beat Tier 0?**
- Compare quality scores across all 3 nodes
- Compare finding counts (same modules)
- Compare confidence scores

**Q2: Which tier finds more edge cases?**
- Are there findings in Tier 1 not in Tier 0?
- Are those findings valid or false positives?
- Pattern: What types of issues does each tier catch?

**Q3: What's the cost-benefit?**
- Tier 0: $0, ~30-40 findings
- Tier 1: $0.003, ~45-60 findings (expected)
- ROI: Worth $0.003 per review?

**Q4: Capability difference by domain?**
- Does Tier 1 excel in concurrency (Node 2)?
- Does Tier 1 excel in cache safety (Node 3)?
- Or is improvement uniform across domains?

---

## Execution Checklist

### Tier 0 Execution (3 nodes, parallel)

- [ ] Select 3 Free Tier models (GPT-4o, GPT-4.1, GPT-5 mini if available)
- [ ] Send Node 1 with "Node 1 Unified Prompt: DI & Context Layer" (parametrized)
- [ ] Send Node 2 with "Node 2 Unified Prompt: Extraction & Detection" (parametrized)
- [ ] Send Node 3 with "Node 3 Unified Prompt: Cache, Events & Requests" (parametrized)
- [ ] Wait 18 minutes for results
- [ ] Save 3 YAML files: node1-tier0.yaml, node2-tier0.yaml, node3-tier0.yaml

### Tier 1 Execution (3 nodes, parallel, same prompts)

- [ ] Send Node 1 with "Node 1 Unified Prompt" to Claude Haiku 4.5
- [ ] Send Node 2 with "Node 2 Unified Prompt" to Grok Code Fast 1
- [ ] Send Node 3 with "Node 3 Unified Prompt" to Grok Code Fast 1
- [ ] Wait 18 minutes for results
- [ ] Save 3 YAML files: node1-tier1.yaml, node2-tier1.yaml, node3-tier1.yaml

### Analysis

- [ ] Compare Tier 0 vs Tier 1 findings (same modules)
- [ ] Calculate quality delta per node
- [ ] Identify findings unique to each tier
- [ ] Assess convergence (both found same critical issues?)
- [ ] Calculate ROI per node

---

## Ready?

This design ensures:
✅ **True comparison:** Same prompts, same files, different models  
✅ **Clear signals:** Can see which tier finds what, on what code  
✅ **Decision-ready:** Know if Tier 1 is worth $0.003/cycle  
✅ **Module distribution:** Balanced 3-node cluster  

Shall I prepare the Gilfoyle prompts (formatted for runSubagent) and execution sequence?
