# Wave 3 Node 1 Prompt: DI & Context Layer Analysis

**Target Modules:** `src/prism/scanner_core/di.py`, `src/prism/scanner_core/di_helpers.py`, `src/prism/scanner_core/scanner_context.py`

**Total Lines:** 950 lines (320 + 180 + 450)

**Your Task:** Perform a comprehensive code review of these three modules, focusing on the dependency injection container, helper utilities, and scanner context lifecycle management. Identify issues that could impact testability, maintainability, and runtime behavior.

---

## Analysis Focus Areas

### 1. Type Safety & Erasure Patterns
- Identify `cast()` usage and Protocol enforcement gaps
- Look for type holes where `Any` is used instead of concrete types
- Flag situations where TypedDict identity is lost through conversions
- Check DI factory return types and consumer type assertions

### 2. DI Container Architecture
- Assess god-object antipattern (is the DI container doing too much?)
- Evaluate coupling between modules through DI
- Check for circular dependency workarounds or lazy imports
- Identify missing dependency injection points (hardcoded instantiation)

### 3. Policy Flow & Ownership
- Trace where policies are set vs where they're read
- Identify split ownership (multiple places enforcing policy)
- Flag late-binding or fallback resolution paths
- Check for policy normalization duplicates across modules

### 4. Error Handling Contracts
- Identify silent failures (catch Exception: pass patterns)
- Check exception chaining and diagnostic information
- Look for fail-open vs fail-closed patterns
- Assess error recovery strategy consistency

### 5. Testability & Mocking Complexity
- Evaluate testability impact of current DI design
- Identify module dependencies that make testing harder
- Check for test-specific workarounds or backdoors
- Assess whether mocking the DI container requires complex setup

### 6. Lazy Imports & Circular Dependencies
- Find lazy import workarounds (try/except ImportError patterns)
- Identify circular import risks
- Check load-order dependencies
- Assess whether lazy imports mask design issues

---

## Required Output Format

Return your findings in the following YAML structure. **Any response that does not start with `model_used:` will be rejected.**

```yaml
model_used: [exact model name you are using]
findings:
  - id: GILF-NODE1-[NN]
    severity: CRITICAL|HIGH|MEDIUM|LOW
    category: type-safety|ownership|error-handling|testability|architecture|performance
    location: "[file.py:line-line or file.py:function_name]"
    issue: "[concise issue title, 1-2 sentences]"
    root_cause: "[why this exists, what design choice led here]"
    impact: "[what breaks or degrades: test time, runtime behavior, maintenance burden, etc.]"
    confidence: [1-100 — how confident are you in this finding?]
    fix_suggestion: "[concrete, actionable fix with estimated effort and impact]"
```

### Important Constraints

- **Severity Calibration:** CRITICAL = production runtime failure or data loss risk. HIGH = significant design debt or test pain. MEDIUM = maintainability burden. LOW = style/consistency.
- **No restatements:** Only report findings, not what the code already says. Focus on WHY and IMPACT.
- **Concreteness:** Every finding must be traceable to specific code locations, not vague impressions.
- **Depth over breadth:** Deep analysis of fewer critical issues beats surface-level sweeps.

---

## Context: Prism Scanner Architecture

**Scope:** The Prism codebase performs static analysis of Ansible roles/playbooks. These modules are the core dependency injection and request lifecycle management layer.

**Known Issues (for reference only, not to bias your review):**
- Wave 1 identified type erasure with `cast(dict[str, Any], ...)` patterns
- Marker-prefix ownership splits between `task_extract_adapters` and `scan_request`
- Lazy import workarounds for circular dependencies

**DO NOT let prior findings bias your analysis.** Find what YOU see in the code.

---

## Deliverable

Provide your findings in the YAML format above. Aim for 5-12 quality findings (prefer depth over volume). If you find fewer high-confidence issues, report them; don't pad with low-confidence items.
