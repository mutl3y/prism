# Wave 3 Node 3 Prompt: Cache, Events & Requests Layer Analysis

**Target Modules:** `src/prism/scanner_core/scan_cache.py`, `src/prism/scanner_core/events.py`, `src/prism/scanner_core/scan_request.py`

**Total Lines:** 680 lines (160 + 140 + 380)

**Your Task:** Perform a comprehensive code review of the cache, event bus, and request handling layers. Focus on cache safety, event bus reliability, request validation, and copy/mutation semantics. These modules handle critical infrastructure—correctness is essential.

---

## Analysis Focus Areas

### 1. Cache Safety & Correctness
- Examine cache key construction and canonicalization
- Identify collision risks (different inputs → same key?)
- Check cache invalidation strategy (stale data? orphaned entries?)
- Assess whether TTL is enforced uniformly
- Look for cache poisoning vectors (can untrusted input corrupt the cache?)
- Check memory usage and unbounded growth risks

### 2. Event Bus Reliability
- Identify silent event handler failures (exception swallowing)
- Check whether exceptions in handlers block other handlers
- Assess event ordering guarantees
- Look for deadlock risks (handlers waiting on other events?)
- Check whether the event bus can lose events or duplicate them
- Assess monitoring/diagnostics (can you tell if the bus is broken?)

### 3. Request Validation & Contract Enforcement
- Check that all required request fields are validated
- Identify missing or weak validation rules
- Look for late-binding data or lazy resolution
- Assess whether requests can reach scanner_core in an invalid state
- Check for type holes or Any type parameters that bypass validation

### 4. Copy Semantics & Mutation Safety
- Identify shallow vs deep copy issues (are TypedDicts/dataclasses copied correctly?)
- Check for shared mutable state (could modifications affect other requests?)
- Look for implicit aliasing (two references to same object, one modifies)
- Assess whether copies preserve type information (dict() on TypedDict loses identity)
- Check for unintended mutations of input parameters

### 5. Error Handling & Diagnostics
- Find silent failures in request processing
- Identify situations where errors are caught but not logged
- Check for adequate context in error messages (can you debug failures?)
- Assess exception chaining (are root causes preserved?)
- Look for missing validation error messages

### 6. Performance & Resource Usage
- Identify inefficient cache lookups or event dispatch
- Check for unbounded memory growth (queues, caches, collections)
- Look for O(n²) or worse algorithms
- Assess whether event listeners create resource leaks

---

## Required Output Format

Return your findings in the following YAML structure. **Any response that does not start with `model_used:` will be rejected.**

```yaml
model_used: [exact model name you are using]
findings:
  - id: GILF-NODE3-[NN]
    severity: CRITICAL|HIGH|MEDIUM|LOW
    category: cache-safety|event-reliability|validation|copy-semantics|error-handling|performance
    location: "[file.py:line-line or file.py:function_name]"
    issue: "[concise issue title, 1-2 sentences]"
    root_cause: "[why this exists, what design choice led here]"
    impact: "[what breaks or degrades: data loss, silent failures, memory leak, etc.]"
    confidence: [1-100 — how confident are you in this finding?]
    fix_suggestion: "[concrete, actionable fix with estimated effort and impact]"
```

### Important Constraints

- **Severity Calibration:** CRITICAL = data loss, silent failures, or resource leaks. HIGH = validation gap or event delivery issue. MEDIUM = maintainability burden. LOW = style/consistency.
- **Infrastructure is critical:** These modules are used by everything else. Even "small" bugs here cascade. Escalate more aggressively.
- **Copy semantics matter:** TypedDict/dataclass mutations are a common source of subtle bugs. Pay attention.
- **Concrete evidence:** Reference specific line numbers and code patterns.

---

## Context: Prism Scanner Architecture

**Scope:** These are infrastructure modules used by the entire scanner. Cache correctness, event reliability, and request validation are foundation-level concerns.

**Known Issues (for reference only, not to bias your review):**
- Wave 1 identified `dict()` conversion issues with TypedDict (loses type identity)
- Silent exception catching in event bus flagged
- Cache key canonicalization concerns

**DO NOT let prior findings bias your analysis.** Find what YOU see in the code.

---

## Deliverable

Provide your findings in the YAML format above. Aim for 5-12 quality findings. Infrastructure bugs hit hard—if you're uncertain, escalate severity. Better to flag false positives than miss a critical infrastructure failure.
