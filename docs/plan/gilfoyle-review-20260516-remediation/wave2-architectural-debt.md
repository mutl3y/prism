# Wave 2: Architectural Debt Cleanup

**Wave ID:** wave_2
**Priority:** MEDIUM
**Findings:** FIND-01, FIND-03, FIND-04, FIND-06, FIND-08, FIND-10, FIND-11
**Estimated Effort:** 16h total

---

## Overview

Wave 2 addresses 7 medium-severity findings that represent accumulated architectural debt. These are not runtime blockers but contribute to long-term maintenance burden and cognitive overhead.

---

## FIND-01: Empty Subclass Facades in `api.py`

### Problem

Three empty subclasses (`DIContainer`, `FeatureDetector`, `ScannerContext`) in `api.py` provide no overrides but exist "for public facade overrides." This is pure indirection.

### Remediation

**Option A (Recommended):** Remove the subclasses entirely, expose base classes directly from `scanner_core`.

**Changes:**
1. Delete the three empty class definitions from `api.py`
2. Update `_resolve_run_scan_runtime_classes()` to return base classes directly
3. Update any imports that reference `api.DIContainer` to use `scanner_core.DIContainer`

**Risk:** Low — no behavioral change, only import path simplification.

**Test:** Verify `from prism.api import DIContainer` still works (re-export from scanner_core).

---

## FIND-03: Hand-Rolled Deep Clone

### Problem

`_clone_container_structure()` in `di.py` reimplements `copy.deepcopy()` for 5 container types without handling custom objects, circular references, or other edge cases.

### Remediation

**Replace with `copy.deepcopy()`:**

```python
import copy

def clone_scan_options(scan_options: Mapping[str, object]) -> ScanOptionsDict:
    """Return a container-only snapshot of scan options for runtime consumers."""
    # Use deepcopy for correctness; profile later if hot path
    return copy.deepcopy(dict(scan_options))  # type: ignore[return-value]
```

**Rationale:**
- `deepcopy` handles all edge cases correctly
- If performance becomes an issue, profile first, then optimize
- Current implementation is fragile and incomplete

**Test:** Add test case with nested custom objects to verify deepcopy behavior matches expected.

---

## FIND-04: Repeated `require_prepared_policy` Call Sites

### Problem

`require_prepared_policy(di, "policy_name", "policy_name")` is called from every function in 4 modules with redundant arguments. The third argument duplicates the second.

### Remediation

**Consolidate to single-argument form:**

1. Refactor `require_prepared_policy` signature:
   ```python
   def require_prepared_policy(di: object | None, policy_name: str) -> Any:
       # Internal lookup uses policy_name for both registry key and attr
   ```

2. Update all 20+ call sites across:
   - `task_line_parsing.py`
   - `task_annotation_parsing.py`
   - `task_file_traversal.py`
   - `yaml_parsing.py`

3. Add helper functions per module for domain-specific access:
   ```python
   def _task_line_policy(di: object | None) -> PreparedTaskLineParsingPolicy:
       return cast(PreparedTaskLineParsingPolicy, require_prepared_policy(di, "task_line_parsing"))
   ```

**Test:** All existing tests pass; no new tests needed (refactor preserves behavior).

---

## FIND-06: Hardcoded `IGNORED_IDENTIFIERS`

### Problem

60+ entry hardcoded frozenset in `ansible/variable_discovery.py` with no categorization or extension mechanism.

### Remediation

**Extract to data file:**

1. Create `src/prism/scanner_plugins/ansible/ignored_identifiers.yaml`:
   ```yaml
   ignored_identifiers:
     - name: "absent"
       category: "jinja_builtin"
       reason: "Jinja2 built-in test"
     - name: "ansible_facts"
       category: "ansible_special"
       reason: "Ansible magic variable"
     # ... all 60 entries with categories
   ```

2. Load at module init:
   ```python
   def _load_ignored_identifiers() -> frozenset[str]:
       data = yaml.safe_load(Path(__file__).parent / "ignored_identifiers.yaml")
       return frozenset(entry["name"] for entry in data["ignored_identifiers"])
   ```

3. Support platform-specific overrides via plugin registry

**Test:** Verify loaded set matches hardcoded set exactly.

---

## FIND-08: Overly Permissive Type Alias

### Problem

`RepoScanPayload = RunScanOutputPayload | dict[str, Any] | str` admits untyped data.

### Remediation

**Narrow the union:**

```python
RepoScanPayload: TypeAlias = RunScanOutputPayload | dict[str, Any]
```

**Rationale:**
- Remove `str` case — scan payloads should never be raw strings
- If string payloads are needed, wrap in a TypedDict with `raw_content: str`
- Update `repo_services.py` to validate/convert string inputs at ingress

**Test:** Search for call sites passing `str` to `RepoScanPayload`, ensure conversion happens before type boundary.

---

## FIND-10: Runtime Protocol Validation

### Problem

`_validate_process_scan_pipeline_plugin_signature()` validates Protocol contracts at runtime, duplicating mypy's job.

### Remediation

**Remove runtime validation, rely on static checking:**

1. Delete `_validate_process_scan_pipeline_plugin_signature()` function
2. Add mypy strictness note to module docstring:
   ```python
   # Protocol compliance is enforced by mypy at type-check time.
   # Runtime duck-typing is intentional for plugin extensibility.
   ```
3. If runtime safety is required, use `typing.runtime_checkable` Protocol with `isinstance()` checks (cheaper than signature inspection)

**Test:** Run mypy with `--strict` on orchestrator.py to verify Protocol usage is sound.

---

## FIND-11: Test Coverage Gaps

### Problem

Missing tests for critical paths identified in review.

### Remediation

**Add 4 new test files:**

1. `test_task_line_parsing_concurrency.py`:
   - Test proxy behavior under 10 concurrent threads
   - Verify no race conditions on cache access

2. `test_scanner_context_error_boundaries.py`:
   - Test malformed scan options (missing keys, wrong types)
   - Verify PrismRuntimeError wrapping

3. `test_execution_request_builder_edge_cases.py`:
   - Test platform key resolution with all fallback paths
   - Test policy bundle missing scenarios

4. `test_output_orchestrator_malformed_payloads.py`:
   - Test RunScanOutputPayload with missing fields
   - Verify graceful degradation

**Test:** All new tests pass; coverage delta measured with `pytest --cov`.

---

## Wave 2 Execution Order

**Recommended sequence (dependencies):**

1. FIND-04 (repeated call sites) — affects FIND-02 fix in Wave 1
2. FIND-03 (deep clone) — independent
3. FIND-01 (empty facades) — independent
4. FIND-06 (ignored identifiers) — independent
5. FIND-08 (type alias) — independent
6. FIND-10 (runtime validation) — independent
7. FIND-11 (test gaps) — run last to validate all fixes

**Parallelization:** All except FIND-04 can run in parallel (disjoint file sets).

---

## Validation Gate

```bash
pytest -q src/prism
python3 -m mypy src/prism
python3 -m ruff check src/prism
python3 -m black --check src/prism
```

**Success Criteria:**
- 0 new test failures
- 0 new mypy errors
- ruff clean
- black clean

---

## Artifacts

- `wave2-find01-facade-removal.md`
- `wave2-find03-deepclone-replacement.md`
- `wave2-find04-policy-consolidation.md`
- `wave2-find06-ignored-identifiers-data.md`
- `wave2-find08-type-alias-narrowing.md`
- `wave2-find10-protocol-validation.md`
- `wave2-find11-test-coverage-report.md`
- `wave2-validation-report.yaml`
