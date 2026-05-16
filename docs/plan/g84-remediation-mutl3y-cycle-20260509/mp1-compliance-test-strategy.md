# MP1 Compliance Test Strategy

**Date:** 2026-05-09  
**Phase:** Q3 Implementation (Tier 0 Scout Design)  
**Purpose:** Define test cases to validate marker-prefix MP1 contract enforcement  
**Status:** ✅ AUDIT FINDINGS CLEAN (0 violations)

---

## Executive Summary

MP1 (Marker-Prefix) enforcement validates that marker-prefix is **ingress-owned, immutable, and flows through canonical path only**. This strategy defines 5 test suites + 12+ test cases to ensure compliance across all scanner layers.

| Test Suite | File | Status | Coverage |
|-----------|------|--------|----------|
| **MP1 Boundary** | `test_mp1_enforcement.py` | PLANNED | Consumer functions, bundle mutation, API boundary |
| **MP1 Violation Detection** | `test_mp1_violation_detection.py` | PLANNED | Import audits, hardcoding detection, plugin isolation |
| **MP1 Integration** | `test_mp1_integration.py` | PLANNED | End-to-end scanner execution with MP1 validation |
| **MP1 Plugin Isolation** | `test_mp1_plugin_isolation.py` | PLANNED | Plugin behavior under MP1 constraints |
| **MP1 Regression** | `test_mp1_regression.py` | PLANNED | Scanner behavior unchanged after MP1 enforcement |

---

## Test Suite 1: MP1 Boundary Tests

**File:** `src/prism/tests/test_mp1_enforcement.py`  
**Purpose:** Validate core MP1 contract: ingress ownership, immutability, canonical flow

### Test 1.1: Marker-Prefix Sourcing from Bundle

**Test ID:** `test_marker_prefix_sourcing_from_bundle`

**Scenario:** Task extraction receives marker-prefix from prepared_policy_bundle only

**Setup:**
```python
def test_marker_prefix_sourcing_from_bundle():
    """
    OBJECTIVE: Verify marker-prefix always comes from bundle, never computed.
    
    GIVEN: ExecutionRequest with marker-prefix in scan_options
    WHEN: bundle_resolver projects marker-prefix to PreparedPolicyBundle
    THEN: task_extract_adapters receives marker-prefix from bundle parameter
    AND:  No internal computation of marker-prefix occurs
    """
```

**Test Steps:**
1. Create scan_options with `comment_doc_marker_prefix = "test_prefix"`
2. Call `ensure_prepared_policy_bundle(scan_options=scan_options, di=di)`
3. Extract bundle from scan_options
4. Assert `bundle.get("comment_doc_marker_prefix") == "test_prefix"`
5. Call `extract_task_annotations(marker_prefix=bundle["comment_doc_marker_prefix"], ...)`
6. Assert task extraction used the projected marker-prefix
7. Verify no hardcoded marker-prefix in any extraction function

**Assertions:**
```python
assert bundle.get("comment_doc_marker_prefix") == "test_prefix"
assert marker_prefix_in_use == "test_prefix"
assert not any_computed_marker_prefix()  # No internal computation
```

**Coverage:**
- `scanner_plugins/bundle_resolver.ensure_prepared_policy_bundle()`
- `scanner_core/task_extract_adapters._extract_task_annotations_for_file()`
- `scanner_core/task_extract_adapters._collect_task_handler_catalog()`

---

### Test 1.2: Marker-Prefix Fallback Hierarchy

**Test ID:** `test_marker_prefix_fallback_hierarchy`

**Scenario:** Marker-prefix sources from scan_options → policy_context → DEFAULT

**Setup:**
```python
def test_marker_prefix_fallback_hierarchy():
    """
    OBJECTIVE: Validate marker-prefix resolution follows canonical fallback order.
    
    PRIORITY:
    1. scan_options["comment_doc_marker_prefix"] (ingress top-level)
    2. policy_context["comment_doc"]["marker"]["prefix"] (nested fallback)
    3. DEFAULT_DOC_MARKER_PREFIX (default to "prism")
    """
```

**Test Cases:**
| Priority | Source | scan_options Value | Expected Bundle Value |
|----------|--------|-------------------|----------------------|
| P1 | Top-level | `"custom_prefix"` | `"custom_prefix"` |
| P2 | Nested | `None` → policy_context | `nested_value` |
| P3 | Default | `None` → no nested | `"prism"` |

**Assertions:**
```python
# Priority 1: Top-level scan_options wins
scan_options["comment_doc_marker_prefix"] = "top_level"
scan_options["policy_context"] = {"comment_doc": {"marker": {"prefix": "nested"}}}
bundle = ensure_prepared_policy_bundle(scan_options=scan_options, di=di)
assert bundle["comment_doc_marker_prefix"] == "top_level"

# Priority 2: Nested fallback
scan_options["comment_doc_marker_prefix"] = None
bundle = ensure_prepared_policy_bundle(scan_options=scan_options, di=di)
assert bundle["comment_doc_marker_prefix"] == "nested"

# Priority 3: Default
scan_options["policy_context"] = {}
bundle = ensure_prepared_policy_bundle(scan_options=scan_options, di=di)
assert bundle["comment_doc_marker_prefix"] == "prism"
```

**Coverage:**
- `scanner_plugins/bundle_resolver.ensure_prepared_policy_bundle()` (lines 142-157)

---

### Test 1.3: Marker-Prefix Immutability After Projection

**Test ID:** `test_marker_prefix_immutability_after_projection`

**Scenario:** Bundle['comment_doc_marker_prefix'] unchanged after task extraction

**Setup:**
```python
def test_marker_prefix_immutability_after_projection():
    """
    OBJECTIVE: Verify marker-prefix is read-only after bundle creation.
    
    GIVEN: Prepared bundle with comment_doc_marker_prefix = "test"
    WHEN: Execute task extraction and feature detection
    THEN: bundle['comment_doc_marker_prefix'] remains "test"
    AND:  No code path modifies bundle['comment_doc_marker_prefix']
    """
```

**Test Steps:**
1. Create bundle with marker-prefix = "original"
2. Store original_value = bundle["comment_doc_marker_prefix"]
3. Execute feature detection: `detect_features(bundle=bundle, ...)`
4. Execute task extraction: `extract_annotations(bundle=bundle, ...)`
5. Execute catalog collection: `collect_catalog(bundle=bundle, ...)`
6. Assert bundle["comment_doc_marker_prefix"] == original_value
7. Assert no mutations detected in bundle

**Assertions:**
```python
original_prefix = bundle["comment_doc_marker_prefix"]
# ... execute scanner_core functions ...
assert bundle["comment_doc_marker_prefix"] == original_prefix
assert id(bundle["comment_doc_marker_prefix"]) == id(original_prefix)  # Same object
```

**Coverage:**
- All consumer functions: task_extract_adapters.py, feature_detector.py
- Plugin execution paths: ansible/feature_detection.py, ansible/task_line_parsing.py

---

### Test 1.4: Consumer Functions Require Marker-Prefix Parameter

**Test ID:** `test_consumer_functions_require_marker_prefix_parameter`

**Scenario:** All consumers accept marker-prefix as explicit function parameter

**Setup:**
```python
def test_consumer_functions_require_marker_prefix_parameter():
    """
    OBJECTIVE: Verify marker-prefix passed as explicit parameter, not implicit.
    
    GIVEN: Consumer function signature
    THEN: marker_prefix parameter present and required (not optional with default)
    """
```

**Test Cases:**
| Function | Signature | Marker-Prefix Source |
|----------|-----------|---------------------|
| `_extract_task_annotations_for_file()` | `marker_prefix: str = "prism"` | Bundle |
| `_collect_task_handler_catalog()` | `marker_prefix: str = "prism"` | Bundle |
| `AnsibleFeatureDetectionPlugin.detect()` | Via `bundle` parameter | Bundle |

**Assertions:**
```python
# Extract functions have marker_prefix parameter
assert "marker_prefix" in inspect.signature(_extract_task_annotations_for_file).parameters
assert "marker_prefix" in inspect.signature(_collect_task_handler_catalog).parameters

# Parameter has default = "prism" (fallback) but sourced from bundle
param = inspect.signature(_extract_task_annotations_for_file).parameters["marker_prefix"]
assert param.default == "prism"
```

**Coverage:**
- `scanner_core/task_extract_adapters.py` (all consumer functions)

---

### Test 1.5: Marker-Prefix Validation at Entry

**Test ID:** `test_marker_prefix_validation_at_entry`

**Scenario:** Consumers validate marker-prefix is non-empty string before use

**Setup:**
```python
def test_marker_prefix_validation_at_entry():
    """
    OBJECTIVE: Verify marker-prefix validated at function entry.
    
    GIVEN: Consumer function called with invalid marker-prefix
    THEN: Raises ValueError with clear message
    """
```

**Test Cases:**
| Input | Expected Behavior |
|-------|-------------------|
| `marker_prefix = ""` | ValueError |
| `marker_prefix = None` | ValueError |
| `marker_prefix = 123` | ValueError (not string) |
| `marker_prefix = "valid"` | Accepted |

**Assertions:**
```python
with pytest.raises(ValueError, match="marker_prefix must be a non-empty string"):
    _extract_task_annotations_for_file(marker_prefix="", ...)

with pytest.raises(ValueError, match="marker_prefix must be a non-empty string"):
    _collect_task_handler_catalog(marker_prefix=None, ...)

# Valid cases should not raise
_extract_task_annotations_for_file(marker_prefix="valid", ...)  # No error
```

**Coverage:**
- `scanner_core/task_extract_adapters.py` (lines 33-36, 62-64)

---

## Test Suite 2: MP1 Violation Detection Tests

**File:** `src/prism/tests/test_mp1_violation_detection.py`  
**Purpose:** Verify violation detection mechanisms work correctly

### Test 2.1: Detect Forbidden Marker Import in Scanner-Core

**Test ID:** `test_detect_marker_import_in_scanner_core`

**Scenario:** Linter detects scanner_core importing scanner_config.marker

**Setup:**
```python
def test_detect_marker_import_in_scanner_core():
    """
    OBJECTIVE: Verify import audit catches forbidden marker imports.
    
    VIOLATION: scanner_core module imports from scanner_config.marker
    DETECTOR: ruff linter + custom rule
    """
```

**Test Steps:**
1. Run import audit: `grep -r "from prism.scanner_config.marker import" src/prism/scanner_core/`
2. Filter out exception allowlist (policy_registry.py, di.py)
3. Assert results is empty (0 violations)
4. Inject violation: Create test file with forbidden import
5. Run audit again
6. Assert violation detected

**Assertions:**
```python
# Current state: 0 violations
results = run_import_audit("src/prism/scanner_core/", pattern="from prism.scanner_config.marker")
assert len(results) == 0, f"Found {len(results)} forbidden imports"

# Injected violation: 1 violation
inject_test_violation("src/prism/scanner_core/test_violator.py", forbidden_import)
results = run_import_audit(...)
assert len(results) == 1, "Import audit failed to detect violation"
```

**Coverage:**
- All scanner_core modules (EXCEPT allowed: policy_registry.py, di.py)

---

### Test 2.2: Detect Bundle Mutation Outside Resolver

**Test ID:** `test_detect_bundle_mutation_outside_resolver`

**Scenario:** AST linter detects bundle['comment_doc_marker_prefix'] assignment outside bundle_resolver

**Setup:**
```python
def test_detect_bundle_mutation_outside_resolver():
    """
    OBJECTIVE: Verify mutation audit catches bundle modifications.
    
    VIOLATION: Code outside bundle_resolver modifying bundle['comment_doc_marker_prefix']
    DETECTOR: AST-based linter
    """
```

**Test Steps:**
1. Parse all Python files in src/prism/
2. Find assignments to `bundle['comment_doc_marker_prefix']`
3. Filter out bundle_resolver.py
4. Assert no violations found
5. Inject violation in test module
6. Verify detection

**Assertions:**
```python
# Current state: 0 violations
violations = detect_bundle_mutations("src/prism/", exclude=["bundle_resolver.py"])
assert len(violations) == 0, f"Found {len(violations)} bundle mutations"

# Injected violation
inject_test_violation("src/prism/scanner_core/test_violator.py", 
                      'bundle["comment_doc_marker_prefix"] = "bad"')
violations = detect_bundle_mutations(...)
assert len(violations) == 1, "Mutation audit failed to detect violation"
```

**Coverage:**
- All Python files in src/prism/ (EXCEPT bundle_resolver.py)

---

### Test 2.3: Detect Hardcoded Marker-Prefix Assumptions

**Test ID:** `test_detect_hardcoded_marker_assumptions`

**Scenario:** Pattern detector finds hardcoded marker-prefix values

**Setup:**
```python
def test_detect_hardcoded_marker_assumptions():
    """
    OBJECTIVE: Verify hardcoding audit catches assumptions.
    
    VIOLATION: Code like marker_prefix = "prism" (not DEFAULT_DOC_MARKER_PREFIX)
    DETECTOR: grep pattern + context analysis
    """
```

**Test Cases:**
| Code | Status |
|------|--------|
| `marker_prefix = "prism"` | ❌ VIOLATION (hardcoded) |
| `marker_prefix = DEFAULT_DOC_MARKER_PREFIX` | ✅ OK (uses constant) |
| `prefix = "prism"  # test:` | ✅ OK (test fixture) |

**Assertions:**
```python
violations = detect_hardcoded_marker("src/prism/scanner_core/")
assert len(violations) == 0, f"Found {len(violations)} hardcoded markers"

# Check allowed pattern
assert is_allowed_pattern('marker_prefix = DEFAULT_DOC_MARKER_PREFIX')
assert not is_allowed_pattern('marker_prefix = "prism"')
```

**Coverage:**
- All scanner_core and scanner_extract modules

---

## Test Suite 3: MP1 Integration Tests

**File:** `src/prism/tests/test_mp1_integration.py`  
**Purpose:** End-to-end scanner execution with MP1 validation

### Test 3.1: End-to-End Execution with Custom Marker-Prefix

**Test ID:** `test_e2e_custom_marker_prefix`

**Scenario:** Full scan execution with non-default marker-prefix flows correctly

**Setup:**
```python
def test_e2e_custom_marker_prefix(tmp_path, di_container):
    """
    OBJECTIVE: Verify MP1 compliance across full scan pipeline.
    
    GIVEN: Custom marker-prefix = "myprefix"
    WHEN: Execute full scan (API → extraction → plugins → output)
    THEN: All consumers use "myprefix" throughout
    AND:  Marker-prefix unchanged after scan
    """
```

**Test Steps:**
1. Create test README with markers: `@myprefix_task`, `@myprefix_handler`
2. Create scan_options with `comment_doc_marker_prefix = "myprefix"`
3. Execute non_collection.execute_scan(scan_options, ...)
4. Verify task extraction found @myprefix_task markers
5. Assert marker-prefix unchanged in output metadata
6. Verify feature detection used "myprefix"

**Assertions:**
```python
# Setup
scan_options = {"comment_doc_marker_prefix": "myprefix"}
test_file = tmp_path / "test.yml"
test_file.write_text("# @myprefix_task\n- name: sample\n")

# Execute
result = execute_scan(scan_options=scan_options, di=di_container)

# Verify
assert len(result.tasks) > 0
assert all(t.marker_prefix == "myprefix" for t in result.tasks)
assert scan_options["prepared_policy_bundle"]["comment_doc_marker_prefix"] == "myprefix"
```

**Coverage:**
- Full pipeline: api_layer → scanner_core → scanner_plugins → output

---

### Test 3.2: Batch Consistency with Multiple Marker-Prefixes

**Test ID:** `test_batch_consistency_multiple_marker_prefixes`

**Scenario:** Collection API maintains marker-prefix consistency across batch

**Setup:**
```python
def test_batch_consistency_multiple_marker_prefixes(tmp_path, di_container):
    """
    OBJECTIVE: Verify marker-prefix consistent across batch requests.
    
    GIVEN: Collection scan with 3 items, each with custom marker-prefix
    THEN: Each item uses its own marker-prefix
    AND:  No cross-contamination between items
    """
```

**Test Steps:**
1. Create collection with 3 items:
   - Item 1: marker-prefix = "prefix1"
   - Item 2: marker-prefix = "prefix2"
   - Item 3: marker-prefix = "prefix3"
2. Execute collection scan
3. Verify Item 1 tasks use prefix1 markers
4. Verify Item 2 tasks use prefix2 markers
5. Verify Item 3 tasks use prefix3 markers

**Assertions:**
```python
for item, expected_prefix in zip(items, ["prefix1", "prefix2", "prefix3"]):
    assert all(t.marker_prefix == expected_prefix for t in item.tasks)
```

**Coverage:**
- `api_layer/collection.py` (collection scan execution)

---

## Test Suite 4: MP1 Plugin Isolation Tests

**File:** `src/prism/tests/test_mp1_plugin_isolation.py`  
**Purpose:** Verify plugins respect MP1 boundaries

### Test 4.1: Plugin Cannot Override Marker-Prefix

**Test ID:** `test_plugin_cannot_override_marker_prefix`

**Scenario:** Plugin receives immutable bundle, cannot modify marker-prefix

**Setup:**
```python
def test_plugin_cannot_override_marker_prefix(di_container):
    """
    OBJECTIVE: Verify plugins cannot override marker-prefix.
    
    GIVEN: Plugin receives prepared_policy_bundle
    WHEN: Plugin attempts bundle["comment_doc_marker_prefix"] = "override"
    THEN: Mutation prevented OR does not affect subsequent consumers
    """
```

**Test Steps:**
1. Create bundle with marker-prefix = "original"
2. Call plugin.detect(bundle=bundle, ...)
3. Inside plugin (mocked), attempt: `bundle["comment_doc_marker_prefix"] = "override"`
4. Assert mutation either:
   - Prevented by deepcopy
   - Does not affect bundle passed to next plugin
5. Verify downstream consumers still use "original"

**Assertions:**
```python
original_prefix = bundle["comment_doc_marker_prefix"]
plugin_result = plugin.detect(bundle=bundle, ...)
# Either mutation prevented or isolated
assert bundle["comment_doc_marker_prefix"] == original_prefix
```

**Coverage:**
- `scanner_plugins/ansible/feature_detection.py`
- `scanner_plugins/ansible/task_line_parsing.py`

---

### Test 4.2: Plugin Must Read Marker-Prefix from Bundle

**Test ID:** `test_plugin_reads_marker_from_bundle`

**Scenario:** Plugin accesses marker-prefix only via bundle, not hardcoded

**Setup:**
```python
def test_plugin_reads_marker_from_bundle(di_container):
    """
    OBJECTIVE: Verify plugin gets marker-prefix from bundle parameter.
    
    GIVEN: Plugin with custom marker-prefix in bundle
    WHEN: Plugin.detect() or Plugin.parse() called
    THEN: Plugin uses bundle marker-prefix, not hardcoded
    """
```

**Test Cases:**
| Plugin | Marker-Prefix in Bundle | Expected Behavior |
|--------|------------------------|-------------------|
| AnsibleFeatureDetectionPlugin | "custom" | Uses "custom" |
| AnsibleTaskLineParsingPlugin | "custom" | Uses "custom" |

**Assertions:**
```python
# Plugin with custom marker-prefix
bundle["comment_doc_marker_prefix"] = "custom_prefix"
result = plugin.detect(bundle=bundle, ...)
# Verify plugin used "custom_prefix" (check output for @custom_prefix markers)
```

**Coverage:**
- All plugin implementations in scanner_plugins/

---

## Test Suite 5: MP1 Regression Tests

**File:** `src/prism/tests/test_mp1_regression.py`  
**Purpose:** Ensure MP1 enforcement doesn't break existing functionality

### Test 5.1: Default Behavior Unchanged

**Test ID:** `test_default_behavior_unchanged`

**Scenario:** Scanner behavior with default marker-prefix ("prism") identical to pre-MP1

**Setup:**
```python
def test_default_behavior_unchanged(tmp_path, di_container):
    """
    OBJECTIVE: Verify no regression in default scanning behavior.
    
    GIVEN: Scan without explicit marker-prefix (uses default "prism")
    THEN: Scanner finds @prism_task, @prism_handler markers (same as before)
    """
```

**Test Steps:**
1. Create test README with default markers (@prism_task, @prism_handler)
2. Execute scan without explicit marker-prefix
3. Assert tasks found = pre-MP1 baseline
4. Assert task counts match baseline

**Assertions:**
```python
baseline_count = 42  # From pre-MP1 tests
result = execute_scan(scan_options={})  # No marker-prefix specified
assert len(result.tasks) == baseline_count
```

**Coverage:**
- Default scanner behavior (no marker-prefix override)

---

### Test 5.2: Existing Tests Still Pass

**Test ID:** `test_existing_test_suite_compatibility`

**Scenario:** All existing pytest suite still passes with MP1 enforcement

**Setup:**
```python
def test_existing_test_suite_compatibility():
    """
    OBJECTIVE: Verify MP1 enforcement is backward-compatible.
    
    GIVEN: Full pytest suite (no MP1-specific tests)
    WHEN: Run pytest with MP1 enforcement active
    THEN: All tests pass, no new failures
    """
```

**Test Steps:**
1. Run full pytest suite: `pytest src/prism/tests/ -v`
2. Count passing tests (should equal baseline)
3. Assert 0 new failures introduced

**Coverage:**
- Full test suite (should not be affected)

---

## Implementation Roadmap

| Phase | Timeline | Activities |
|-------|----------|-----------|
| **Phase 1: Audit** | Week 1 (2026-05-09) | Create test strategy, run baseline audit (should be 0 violations) |
| **Phase 2: Implementation** | Week 2-3 (2026-05-16 to 2026-05-30) | Implement all test suites above |
| **Phase 3: CI Integration** | Week 4 (2026-06-06) | Add tests to CI pipeline, create pre-commit hooks |
| **Phase 4: Enforcement** | Week 5+ (2026-06-13+) | Make MP1 checks fail builds (currently warn) |

---

## Test Execution Command Reference

```bash
# Run all MP1 tests
pytest src/prism/tests/test_mp1_*.py -v

# Run specific test suite
pytest src/prism/tests/test_mp1_enforcement.py -v

# Run with coverage
pytest src/prism/tests/test_mp1_*.py --cov=src/prism/scanner_core \
  --cov=src/prism/scanner_plugins --cov-report=term-missing

# Run violation detection
python scripts/mp1_violation_audit.py

# Run full audit (import + mutation + hardcoding)
python scripts/mp1_full_audit.py
```

---

## Compliance Checklist (Q3 Target)

- [ ] All 12+ test cases implemented
- [ ] All tests passing (100%)
- [ ] Import audit: 0 violations
- [ ] Mutation audit: 0 violations
- [ ] Hardcoding audit: 0 violations
- [ ] End-to-end tests: PASSING
- [ ] Plugin isolation: PASSING
- [ ] Regression tests: PASSING
- [ ] Documentation: COMPLETE
- [ ] CI integration: ACTIVE

---

## References

- **MP1 Contract Definition:** [mp1-enforcement-boundaries.yaml](mp1-enforcement-boundaries.yaml) (Section 1)
- **Related Plans:** NCK1, SCB1, GF2, PAR (see AGENTS.md for closure records)
- **Implementation Files:**
  - `src/prism/scanner_plugins/bundle_resolver.py` (marker-prefix projection)
  - `src/prism/scanner_core/task_extract_adapters.py` (marker-prefix consumers)
  - `src/prism/scanner_core/feature_detector.py` (feature detection)
  - `src/prism/api_layer/non_collection.py` (API boundary)

---
