# Wave 3 Node 2 Prompt: Extraction & Detection Layer Analysis

**Target Modules:** `src/prism/scanner_core/variable_discovery.py`, `src/prism/scanner_core/feature_detector.py`, `src/prism/scanner_core/task_extract_adapters.py`

**Total Lines:** 890 lines (280 + 320 + 290)

**Your Task:** Perform a comprehensive code review of these three extraction and feature detection modules. Focus on data flow consistency, concurrency safety, caching strategy, and policy application. These modules handle dynamic feature detection and task extraction—correctness is critical.

---

## Analysis Focus Areas

### 1. Concurrency & Thread Safety
- Identify check-then-act (TOCTOU) race conditions
- Look for shared mutable state without proper synchronization
- Check for data races in caching or plugin discovery
- Assess whether concurrent requests can corrupt shared state
- Flag situations where one request's state can affect another's

### 2. Data Flow Consistency
- Trace how data flows through variable discovery → feature detection → task extraction
- Identify where invariants might be violated mid-pipeline
- Check for orphaned data or missing initialization
- Look for data loss or silent default fallbacks

### 3. Caching Strategy & Collision Risk
- Examine cache key construction (is canonicalization sufficient?)
- Identify cache collision risks (different inputs → same key?)
- Check TTL/invalidation strategy (stale data risk?)
- Look for cache poisoning vectors (can untrusted input corrupt cache?)
- Assess whether cache memory is unbounded

### 4. Policy Application & Marker Ownership
- Trace where marker-prefix policy is applied vs read
- Identify split ownership (multiple places normalizing markers)
- Check for policy re-application or duplication
- Look for late-binding policy resolution
- Assess whether policy is enforced or advisory

### 5. Error Handling & Silent Failures
- Find try/except patterns that catch and ignore errors
- Identify situations where exceptions are logged but execution continues
- Check for default-fallback behavior when extraction fails
- Assess whether errors propagate or get masked

### 6. Performance & Scalability
- Identify O(n²) algorithms or inefficient lookups
- Check for unnecessary repeated work (could be cached/memoized)
- Look for hot paths that iterate excessively
- Assess memory usage during feature detection

---

## Required Output Format

Return your findings in the following YAML structure. **Any response that does not start with `model_used:` will be rejected.**

```yaml
model_used: [exact model name you are using]
findings:
  - id: GILF-NODE2-[NN]
    severity: CRITICAL|HIGH|MEDIUM|LOW
    category: concurrency|data-flow|caching|policy|error-handling|performance
    location: "[file.py:line-line or file.py:function_name]"
    issue: "[concise issue title, 1-2 sentences]"
    root_cause: "[why this exists, what design choice led here]"
    impact: "[what breaks or degrades: correctness, performance, maintainability, etc.]"
    confidence: [1-100 — how confident are you in this finding?]
    fix_suggestion: "[concrete, actionable fix with estimated effort and impact]"
```

### Important Constraints

- **Severity Calibration:** CRITICAL = data corruption, lost findings, or incorrect behavior on real code. HIGH = potential race condition or performance cliff. MEDIUM = code quality/maintainability. LOW = style.
- **Concurrency is critical:** Pay extra attention to thread-safety. These modules might be called concurrently.
- **Concrete evidence:** Reference specific line numbers, variable names, and code patterns.
- **No padding:** Report only findings YOU are confident in. Empty list is better than low-confidence guesses.

---

## Context: Prism Scanner Architecture

**Scope:** These modules drive the core scanning loop—variable discovery, feature detection, and task extraction. Correctness and performance here directly impact scanner quality and speed.

**Known Issues (for reference only, not to bias your review):**
- Wave 1 found TOCTOU race in policy resolution (Haiku 4.5 found this, Tier 2 missed it)
- Cache key canonicalization questioned
- Marker-prefix normalization duplicated in multiple places

**DO NOT let prior findings bias your analysis.** Find what YOU see in the code.

---

## Deliverable

Provide your findings in the YAML format above. Aim for 5-12 quality findings. If you find concurrency or data-flow issues, escalate them to CRITICAL even if they're hard to trigger—race conditions are critical by nature.
