# Wave 3: Tier 1 Comparable Cluster (Matching Wave 2 Scope)

**Objective:** Test same 3-node cluster with Tier 1 models to establish cost-benefit  
**Hypothesis:** Tier 1 delivers 90-92/100 quality on identical 8-module scope, justifies $0.003/review cost  
**Timeline:** ~30 minutes (parallel execution)  
**Cost:** ~$0.003/review (vs $0 Wave 2)

---

## Scope: Matching Wave 2 Exactly

| Metric | Wave 2 (Free) | Wave 3 (Tier 1) | Status |
|--------|---------------|-----------------|--------|
| **Nodes** | 3 (1, 2, 3B) | 3 (1, 2, 3B) | ✓ Same |
| **Modules** | 8 | 8 | ✓ Same |
| **Lines of Code** | 2,230 | 2,230 | ✓ Same |
| **Cost** | $0 | $0.003 | New tier |
| **Expected Quality** | 88.3/100 | 90-92/100 | +1.7-3.7 pts |
| **Expected Findings** | 38 | 45-52 | +7-14 (same scope) |

---

## The 3 Nodes: Tier 1 vs Wave 2 Models

### Node 1: Claude Haiku 4.5 (Architecture & DI)
**Replaces:** GPT-4o (Wave 2 Node 1)  
**Modules:** di.py (320L), scanner_context.py (450L), di_helpers.py (180L) = 950 lines  
**Wave 2 Result:** 5 findings, 88/100 quality  
**Expected:** 8-12 findings, 90-92/100 quality (Tier 1 improves on same scope)

### Node 2: Grok Code Fast 1 (Concurrency)
**Replaces:** GPT-4.1 (Wave 2 Node 2)  
**Modules:** variable_discovery.py (280L), feature_detector.py (320L) = 600 lines  
**Wave 2 Result:** 11 findings, 89/100 quality, TOCTOU CRITICAL found  
**Expected:** 12-16 findings, 91-93/100 quality (match or exceed Wave 2 on same scope)

### Node 3B: Grok Code Fast 1 (Cache & Performance)
**Replaces:** Raptor mini (Wave 2 Node 3B)  
**Modules:** scan_cache.py (160L), events.py (140L), scan_request.py (380L) = 680 lines  
**Wave 2 Result:** 12 findings, 87/100 quality, cache collision CRITICAL found  
**Expected:** 14-18 findings, 89-91/100 quality (improve on same scope)

---

## Execution: Parallel (30 minutes total)

```
t=0:00  Launch all 3 nodes simultaneously
        Node 1: runSubagent(..., "Claude Haiku 4.5 (copilot)", NODE1_PROMPT)
        Node 2: runSubagent(..., "Grok Code Fast 1 (copilot)", NODE2_PROMPT)
        Node 3B: runSubagent(..., "Grok Code Fast 1 (copilot)", NODE3B_PROMPT)

t=0:18  All 3 results available

t=0:30  Analysis complete
        Compare quality/findings to Wave 2
        Validate decision gates
        Calculate cost-benefit ratio
```

---

## Expected Results (Matched Scope)

### Quality Progression
```
Wave 1 (all models): 81/100 average
Wave 1 Tier 1 Haiku: 88/100
Wave 2 (free cluster): 88.3/100
Wave 3 (Tier 1 cluster): 90-92/100 (expected, same 3 nodes)
```

### Finding Count (Same 8 Modules)
```
Wave 2 (free): 38 findings
Wave 3 (Tier 1): 45-52 findings (expected)
Improvement: +7-14 findings from better analysis depth
```

### Cost-Benefit
```
Wave 2 (free): $0/cycle, 38 findings = $0.00/finding
Wave 3 (Tier 1): $0.003/cycle, 45-52 findings = $0.00006/finding
Annual (52 cycles): $0 vs $0.16, negligible cost for quality boost
```

---

## Decision Thresholds (After Wave 3)

### Q1: Does Tier 1 improve quality on identical scope?
- **Target:** ≥90/100 (vs Wave 2's 88.3)
- **Expected:** YES, +1.7-3.7 points
- **Decision:** If YES → Tier 1 justified for accuracy-critical work

### Q2: Does Tier 1 find more issues in same scope?
- **Target:** ≥45 findings (vs Wave 2's 38)
- **Expected:** YES, 45-52 findings
- **Decision:** If YES → Better depth analysis, worth $0.003/cycle

### Q3: Does Tier 1 find same critical issues?
- **Target:** Both TOCTOU and cache collision found
- **Expected:** YES (both models should find these)
- **Decision:** If YES → Architecture is sound, issue severity is real

### Q4: Cost-benefit justified?
- **Target:** Cost <$0.0001/finding
- **Expected:** YES (~$0.00006/finding)
- **Decision:** If YES → Tier 1 cost is negligible vs improvement

---

## Node Prompts

### Node 1: Claude Haiku 4.5 (Architecture & DI)

```
## Wave 3 Comparison: Architecture & DI Review (Tier 1)

You are a Tier 1 architecture expert. Wave 2 Node 1 (GPT-4o) found 5 findings with 88/100 quality on these modules.
Can Tier 1 Haiku match or exceed this on the identical scope?

### Target Modules (950 lines total)
- di.py (320 lines)
- scanner_context.py (450 lines)
- di_helpers.py (180 lines)

### Analysis Points
1. DI God-Object Risks: Coupling, cascading failures, refactoring strategy
2. Type Erasure Justification: Why cast(Any)? How to eliminate safely?
3. TOCTOU Race in Lazy Imports: Multi-threaded failure scenarios
4. Ownership Boundaries: Who should own marker-prefix, prepared-policy, validation?
5. Policy Context Flow: Entry→scanner_context→scan_request→?
6. Type Contract Enforcement: Runtime checks vs trust-based?

### Success Criteria
✓ All 3 modules analyzed in depth
✓ 3+ ownership issues with exact locations
✓ TOCTOU scenarios explained (failure + recovery)
✓ Type erasure justified or flagged
✓ Policy flow mapped
✓ Concrete refactoring suggestions
✓ Target: 8-12 findings (vs Wave 2's 5)
✓ Quality target: 90-92/100

### Output Format
YAML with id, severity, category, location, issue, root_cause, impact, confidence

### Comparison Context
Wave 2 Node 1 (GPT-4o): 5 findings, 88/100
Wave 3 Node 1 (Haiku): Target 8-12 findings, 90-92/100
Can Tier 1 beat free tier on same scope? YES (expected)
```

### Node 2: Grok Code Fast 1 (Concurrency)

```
## Wave 3 Comparison: Concurrency Review (Tier 1)

You are a Tier 1 concurrency expert. Wave 2 Node 2 (GPT-4.1) found 11 findings with 89/100 quality, including TOCTOU CRITICAL (95% confidence).
Can Tier 1 Grok match or exceed this on the identical scope?

### Target Modules (600 lines total)
- variable_discovery.py (280 lines)
- feature_detector.py (320 lines)

### Analysis Points
1. TOCTOU Race in Policy Bundle: Thread A checks, B modifies, A acts on stale. Fix?
2. Feature Cache Race: Check-then-use pattern. Data corruption risk?
3. Event Bus Lazy Init: Not thread-safe. Multiple instances = lost/duplicated events?
4. Cache-Key Collision: Mutable objects in keys. Demonstrate concrete collision.
5. Copy Semantics: Shallow vs deep. What breaks in threaded context?

### Success Criteria
✓ Both modules analyzed in depth
✓ TOCTOU failure scenario + fix strategy
✓ Cache race fix with performance impact analysis
✓ Event bus issue with data loss assessment
✓ Cache-key collision with concrete example
✓ Copy semantics fix proposed
✓ Target: 12-16 findings (vs Wave 2's 11)
✓ Quality target: 91-93/100
✓ TOCTOU must be found and characterized

### Output Format
YAML with id, severity, category, location, issue, root_cause, impact, confidence

### Comparison Context
Wave 2 Node 2 (GPT-4.1): 11 findings, 89/100, TOCTOU found
Wave 3 Node 2 (Grok): Target 12-16 findings, 91-93/100, TOCTOU confirmation
Can Tier 1 find same critical + add depth? YES (expected)
```

### Node 3B: Grok Code Fast 1 (Cache & Performance)

```
## Wave 3 Comparison: Cache & Performance Review (Tier 1)

You are a Tier 1 performance expert. Wave 2 Node 3B (Raptor mini) found 12 findings with 87/100 quality, including 2 CRITICAL cache issues.
Can Tier 1 Grok match or exceed this on the identical scope?

### Target Modules (680 lines total)
- scan_cache.py (160 lines)
- events.py (140 lines)
- scan_request.py (380 lines) [partial]

### Analysis Points
1. Cache TTL Gap: Missing or insufficient timeouts. Stale data risk?
2. Opaque Type Collision: Type erasure causing collisions. How to fix?
3. Dict Stringification: String keys from dict values = collision vector?
4. Shallow Copy Corruption: What state is shared unintentionally?
5. Performance Footguns: Set canonicalization, path hash recompute inefficiencies?
6. Exception Swallowing: Silent failures. Data loss risk?

### Success Criteria
✓ All 3 modules analyzed in depth
✓ 2+ CRITICAL issues identified and characterized
✓ Cache safety fixes with performance trade-offs
✓ Type erasure issues traced to source
✓ Exception handling gaps mapped
✓ Performance optimization opportunities identified
✓ Target: 14-18 findings (vs Wave 2's 12)
✓ Quality target: 89-91/100
✓ CRITICAL findings must be found

### Output Format
YAML with id, severity, category, location, issue, root_cause, impact, confidence

### Comparison Context
Wave 2 Node 3B (Raptor mini): 12 findings, 87/100, 2 CRITICAL
Wave 3 Node 3B (Grok): Target 14-18 findings, 89-91/100, CRITICAL confirmation
Can Tier 1 find same critical + add depth? YES (expected)
```

---

## Comparable Cluster Validation

✓ Same 3 nodes
✓ Same 8 modules
✓ Same 2,230 lines of code
✓ Same module targets (di.py, scanner_context.py, etc.)
✓ Same critical issue hunts (TOCTOU, cache collisions)
✓ Different models (Tier 1 vs free tier)
✓ Results directly comparable

---

## Ready to Launch?

This is Wave 3: Direct Tier 1 comparison on Wave 2's exact executed scope.

**Execution steps:**
1. Copy all 3 node prompts above
2. Launch in parallel (1 minute to queue all 3)
3. Wait 18 minutes for results
4. Merge YAML files (12 minutes)
5. Compare to Wave 2 (will have direct before/after)

**Timeline:** 30 minutes total

**Cost:** $0.003/cycle (negligible vs improvement)

**Value:** Know for sure whether Tier 1 improves on identical scope

Proceed? 🚀
