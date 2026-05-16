# Q3 Initiative 6: Type Safety Expansion Roadmap

**Date**: May 9, 2026  
**Scout**: Scout-Q3Init6TypeSafety  
**Recommended Strategy**: Option B (Targeted High-Value)  
**Estimated Timeline**: 2-3 weeks (1 sprint) 

---

## Executive Recommendation

**PROCEED WITH OPTION B** (Targeted High-Value approach)

**Why B?**
- ✅ 75-80% error reduction (80 → 15-20 errors) with 40% less effort than Option A
- ✅ Covers high-frequency production code paths (extraction layer, feature detection)
- ✅ Establishes type safety foundation for platform expansion (K8s, Terraform)
- ✅ Defers test layer to Q3b (separate initiative with its own justification)
- ✅ Highest ROI: ~$10-12k for 90%+ production code type safety

---

## Phased Implementation Plan

### Phase 0: Pre-Implementation (Days 1-2)

**Objective**: Resolve critical blockers before coding begins.

#### Task 0.1: DI Type Erasure Architecture Review
- **Owner**: Architect (research)
- **Time**: 1 day
- **Input**: Examine DIContainer protocol vs. factory implementations
- **Decision Gate**: Which typing pattern?
  - **Option A**: Overloads (recommended) — `factory_task_line_policy() -> PreparedTaskLineParsingPolicy`
  - **Option B**: TypeVar generics — `factory[T](policy_type: type[T]) -> T`
  - **Option C**: Accept cast() at callsites — Lower effort, lower safety
- **Output**: ADR documenting choice + implementation spec
- **Recommendation**: Overloads (explicit, no runtime overhead, highest type safety)

#### Task 0.2: API/CLI Signature Audit
- **Owner**: Code review (research)
- **Time**: 0.5 day
- **Input**: Compare `write_role_scan_output()` signature in api.py with calls in cli.py
- **Decision Gate**: Which direction to align?
  - API signature should match call pattern, OR
  - Call sites should match API contract
- **Output**: Alignment decision + prioritized fixes
- **Recommendation**: Match intent (audit code comments to determine source-of-truth)

#### Task 0.3: Finalize Q3b Decision (Test Layer Strategy)
- **Owner**: PM + team discussion
- **Time**: 0.5 day
- **Input**: Current proposal (defer test typing to Q3b)
- **Decision Gate**: Agree to deferred-layer strategy?
- **Output**: Formal Q3b initiative placeholder (separate plan)
- **Recommendation**: YES — Tests are CI-validated; Mypy is secondary

**Phase 0 Gate**: All 3 decision gates resolved. DI approach documented. API audit complete.

---

### Phase 1: DI Type Erasure Fix (Days 3-4)

**Objective**: Unblock downstream module typing by fixing DI container return types.

**Scope**:
- `src/prism/scanner_core/di.py` — Factory methods
- `src/prism/scanner_core/di_helpers.py` — Helper functions

**Key Deliverables**:

1. **Overload Signature Set** (if Option A chosen)
   ```python
   # Before
   def factory_task_line_policy(di: DIContainer) -> object: ...

   # After (with overloads)
   @overload
   def factory_task_line_policy(di: DIContainer) -> PreparedTaskLineParsingPolicy: ...
   @overload
   def factory_task_line_policy(di: DIContainer) -> None: ...
   def factory_task_line_policy(di: DIContainer) -> PreparedTaskLineParsingPolicy | None: ...
   ```

2. **Full Method Typing**:
   - `factory_task_line_policy()`
   - `factory_annotation_policy()`
   - `factory_traversal_policy()`
   - `factory_variable_extractor_policy()`
   - `factory_yaml_parsing_policy()`
   - `factory_jinja_analysis_policy()`
   - DI helper methods (8+ total)

3. **Type Imports** (add to TYPE_CHECKING block):
   ```python
   if TYPE_CHECKING:
       from prism.scanner_data.contracts_request import (
           PreparedTaskLineParsingPolicy,
           PreparedTaskAnnotationPolicy,
           # ... 4 more
       )
   ```

**Impact**:
- ✅ Fixes ~35 "object" has no attribute errors across downstream modules
- ✅ Unblocks Phases 2a, 2b, 3
- ✅ Enables mypy to narrow types in consumer modules

**Tests**:
- New test: `test_di_factory_return_types.py` (verify overload narrowing)
- Run: `pytest src/prism/tests/test_di_*.py` (DI test suite)
- Mypy: `mypy src/prism/scanner_core/di*.py` (self-validation)

**Estimated Time**: 1 day
**Mypy Impact**: 80 → 45 errors (44% reduction, Phase 1 complete)

---

### Phase 2a: Extraction Layer Typing (Days 5-7)

**Objective**: Add return type annotations to high-frequency extraction modules.

**Scope**: 4 files, ~40 functions
- `src/prism/scanner_extract/task_line_parsing.py`
- `src/prism/scanner_extract/task_file_traversal.py`
- `src/prism/scanner_extract/task_catalog_assembly.py`
- `src/prism/scanner_extract/task_annotation_parsing.py`

**Pattern** (for each module):

1. **Add Function Return Types**:
   ```python
   # Before
   def parse_task_line(line):
       ...

   # After
   def parse_task_line(line: str) -> TaskLineContext | None:
       ...
   ```

2. **Import Policy Contracts**:
   ```python
   from prism.scanner_data.contracts_request import (
       PreparedTaskLineParsingPolicy,
       PreparedMarkerPrefixPolicy,
       TaskCatalogEntry,
   )
   ```

3. **Add TYPE_CHECKING Imports** (for circular dependency avoidance):
   ```python
   if TYPE_CHECKING:
       from prism.scanner_core.di_helpers import DIContainer
   ```

4. **Verify Existing Arg Typing**: These modules already have ~90% arg typing; focus on missing return types.

**Key Functions** (high-frequency, must be complete):
- `task_line_parsing.parse_task_line_policy()`
- `task_file_traversal.expand_include_target_candidates()`
- `task_catalog_assembly.build_task_catalog()`
- `task_annotation_parsing.parse_task_annotations()`

**Impact**:
- ✅ Eliminates 9 mypy errors in extraction layer
- ✅ Enables feature_detection (Phase 2b) to receive properly-typed policies
- ✅ High-frequency call paths now type-safe

**Tests**:
- Existing: `src/prism/tests/test_task_line_parsing.py` (run as-is)
- Existing: `src/prism/tests/test_task_file_traversal.py` (run as-is)
- Mypy: `mypy src/prism/scanner_extract/*.py`

**Estimated Time**: 1.5 days
**Mypy Impact**: 45 → 30 errors (33% reduction, Phase 2a complete)

---

### Phase 2b: Feature Detection + Plugin Suite (Days 8-10)

**Objective**: Complete typing for feature detection and Ansible plugin implementations.

**Scope**: 5 files, ~80 functions
- `src/prism/scanner_plugins/ansible/feature_detection.py` (12 errors)
- `src/prism/scanner_plugins/ansible/variable_discovery.py`
- `src/prism/scanner_plugins/ansible/variable_extractor.py`
- `src/prism/scanner_plugins/ansible/default_policies.py`
- `src/prism/scanner_plugins/marker_prefix_policy.py`

**Typing Pattern**:

1. **Fix Feature Detection (12 errors)**: Most critical module here
   ```python
   # Errors to fix:
   # - "object" has no attribute "iter_role_include_targets"
   # - Argument to function has incompatible type (DI type erasure blocker)
   
   # Solution: Now that Phase 1 fixed DI, feature_detection can safely narrow
   def analyze_task_catalog(self, role_path: str, options: ScanOptionsDict) -> TaskCatalog:
       # Can now call di.factory_* safely, get typed returns
   ```

2. **Variable Discovery Plugin** (87% coverage → 100%)
   ```python
   # Add missing 3 return types (~15% gap)
   def discover_static_variables(...) -> tuple[VariableRow, ...]:
       ...
   def discover_referenced_variables(...) -> frozenset[str]:
       ...
   def resolve_unresolved_variables(...) -> dict[str, str]:
       ...
   ```

3. **Default Policies** (90% coverage → 100%)
   ```python
   # Add missing ~2 return types
   def build_default_task_line_policy() -> PreparedTaskLineParsingPolicy:
       ...
   def build_default_annotation_policy() -> PreparedTaskAnnotationPolicy:
       ...
   ```

4. **Marker Prefix Policy** (75% coverage → 100%)
   ```python
   # Fix existing incompatible return (Q2 Initiative 3 had typing issue)
   def enforce_marker_prefix_available(bundle: PreparedPolicyBundle) -> str:
       # Now accepts proper type, not `Any`
       ...
   ```

**Impact**:
- ✅ Eliminates 12 errors in feature_detection (biggest error source)
- ✅ Completes plugin suite typing (establishment for K8s/Terraform expansion)
- ✅ Consumer of DI factories now fully typed

**Tests**:
- Existing: `src/prism/tests/test_comment_doc_plugin_resolution.py`
- Existing: `src/prism/tests/test_scanner_parity.py`
- Mypy: `mypy src/prism/scanner_plugins/ansible/*.py`

**Estimated Time**: 1.5 days
**Mypy Impact**: 30 → 10 errors (67% reduction, Phase 2b complete)

---

### Phase 3: API/CLI Alignment (Days 11)

**Objective**: Fix remaining API layer type mismatches.

**Scope**: 2 files, ~50 functions
- `src/prism/api.py` (3 errors)
- `src/prism/cli.py` (4 errors)

**Key Errors to Fix**:

1. **api.py:789** — Incompatible return type
   ```python
   # Before
   def write_role_scan_output(...) -> str | None:
       ...
   
   # After (align with contract)
   def write_role_scan_output(...) -> str:
       # Ensure always returns str, never None
   ```

2. **cli.py:376** — Unexpected keyword arguments
   ```python
   # Before
   write_role_scan_output(output_format=fmt, dry_run=True)  # Wrong kwargs
   
   # After (align with api.py signature)
   write_role_scan_output(output=output_dict)  # Correct signature
   ```

3. **Add missing return types** to public API functions:
   ```python
   def scan_role(...) -> ScanResult:
       ...
   def scan_collection(...) -> CollectionResult:
       ...
   ```

**Decision Dependency**: Task 0.2 must resolve which direction (API → CLI or CLI → API)

**Impact**:
- ✅ Eliminates 4 errors in API/CLI layer
- ✅ Clarifies public entry point contracts
- ✅ Enables downstream tooling integration

**Tests**:
- Existing: `src/prism/tests/test_cli_app.py`
- Mypy: `mypy src/prism/api.py src/prism/cli.py`

**Estimated Time**: 0.5 day
**Mypy Impact**: 10 → 5-6 errors (incomplete; test layer remains, per Option B)

---

### Phase 4: Validation & Closure (Days 12-13)

**Objective**: Verify all changes, document learnings, plan Q3b.

#### Task 4.1: Full Mypy Suite Run
```bash
cd /raid5/source/test/prism
python3 -m mypy src/prism 2>&1 | tee mypy-q3-init6-final.txt
```

**Expected Output**: 
- ~5-20 errors (all in test suite; per Option B strategy)
- 0 errors in production code (scanner_*, api, cli, repo_services)
- Baseline for Q3b initiative

#### Task 4.2: Pytest & Lint Validation
```bash
pytest -q src/prism/tests/
ruff check src/prism
black --check src/prism
```

**Gate**: All pass (no new failures introduced by typing)

#### Task 4.3: Create Phase 1 Closure Artifact
- File: `docs/plan/q3-init6-implementation-closure.md`
- Contents: 
  - Errors fixed (80 → 5-20)
  - Files modified (count, LOC)
  - Effort vs. estimate (actual hours)
  - Learnings & patterns (for Q3b)
  - DI architecture decision (documented)

#### Task 4.4: Plan Q3b Initiative
- Create: `docs/plan/q3b-test-suite-typing.md`
- Scope: 35 test file errors
- Strategy: Fixture typing, parametrization type safety
- Timeline: 2-3 weeks (separate)
- Recommendation: Defer (lower ROI than production code)

**Estimated Time**: 1 day
**Closure Gate**: All tests pass, mypy output documented

---

## Timeline Summary

| Phase | Days | Duration | Owner | Deliverables |
|-------|------|----------|-------|--------------|
| Phase 0: Blockers | 1-2 | 1.5 days | Architect + Code Review | ADR (DI pattern), API audit, Q3b decision |
| Phase 1: DI Fix | 3-4 | 1 day | Type-Safety Specialist | di.py overloads, test_di_factory_return_types.py |
| Phase 2a: Extraction | 5-7 | 1.5 days | Extraction Layer Owner | 4 scanner_extract/* modules typed |
| Phase 2b: Plugins | 8-10 | 1.5 days | Plugin Specialist | feature_detection.py, ansible/* suite |
| Phase 3: API/CLI | 11 | 0.5 day | API Maintainer | api.py, cli.py alignment |
| Phase 4: Closure | 12-13 | 1 day | Scout Lead | Closure artifact, Q3b plan |
| **Total** | 1-13 | **2-3 weeks** | Cross-functional | 90%+ production type safety |

---

## Success Metrics

### Quantitative

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Mypy errors | 80 | 5-20 | <20 (defer rest to Q3b) |
| Production code errors | 45 | 0 | ✅ 0 |
| Test suite errors | 35 | 35 | 0 (Q3b scope) |
| Return type coverage | 65% | 90% | ✅ 90%+ |
| Arg type coverage | 70% | 85% | ✅ 85%+ |
| Files needing work | 16 | 5 | ✅ 5 (test files only) |

### Qualitative

- ✅ DI container type erasure resolved (decision documented)
- ✅ Plugin system ready for K8s/Terraform expansion
- ✅ Extraction layer (high-frequency paths) fully typed
- ✅ API/CLI boundary clarified and type-safe
- ✅ Foundation established for Q3b (test layer)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| DI architecture decision delayed | Phase 0 gate prevents work starting; decision made Days 1-2 |
| API signature conflicts break backward compat | Audit current callers in Phase 0; document breakage if any |
| Test layer remains untyped | Intentional (Option B design); documented in Q3b plan |
| Type narrowing introduces subtle bugs | Run full test suite post-Phase 4; mypy validates before commit |
| Overload syntax unfamiliar to team | Add docstring examples + link to typing docs in ADR |

---

## Resource Requirements

- **Total Effort**: 4-5 person-weeks
- **Sprint Allocation**: 1 sprint (2-3 weeks)
- **Team Composition**:
  - 1x Type-Safety Specialist (Phases 1-2) — 3-4 weeks
  - 1x Architect (Phase 0 DI review) — 1 day
  - 1x Code Reviewer (Phase 0 API audit) — 0.5 day
  - 1x Extraction Layer Owner (Phase 2a) — 1-2 days
  - 1x Plugin Specialist (Phase 2b) — 1-2 days
  - 1x API Maintainer (Phase 3) — 1 day
  - 1x Scout Lead (Phase 4 closure) — 1 day

---

## Next Steps

1. **Approve Strategy**: Confirm Option B is the path forward
2. **Schedule Phase 0**: Days 1-2 next week for blockers resolution
3. **DI Architecture Review**: Schedule 1-day session with architect
4. **Assign Owners**: Identify type-safety specialist for Phases 1-2b
5. **Create Q3b Plan**: Draft separate initiative for test layer (to be scheduled Q3b)
6. **Kick-off Meeting**: All-hands to review timeline, risks, dependencies

---

## Appendices

### A. Error Pattern Reference

**Pattern 1: "object" has no attribute "X"** (35 errors)
- **Root**: DI factories return `object` (Phase 1 fix)
- **Solution**: Add overload signatures
- **Example**: `feature_detection.py:97` receives `object` from DI, can't call methods

**Pattern 2: Missing TypedDict keys** (6 errors)
- **Root**: ScanOptionsDict/PreparedPolicyBundle evolution faster than type definitions
- **Solution**: Audit actual keys, add to TypedDict
- **Example**: test_mp1_compatibility.py missing "task_line_parsing" key

**Pattern 3: Type mismatch (arg, return)** (20 errors)
- **Root**: Function signature doesn't match usage (Phase 3 fix)
- **Solution**: Align API signature or adjust call sites
- **Example**: cli.py:376 passes kwargs that api.py doesn't accept

### B. Reference Implementation (Pattern Code)

```python
# DI Factory Overload Pattern (Phase 1)
from typing import overload, Callable, Any
from prism.scanner_data.contracts_request import PreparedTaskLineParsingPolicy

@overload
def factory_task_line_policy(di: DIContainer) -> PreparedTaskLineParsingPolicy: ...
@overload
def factory_task_line_policy(di: DIContainer) -> None: ...
def factory_task_line_policy(di: DIContainer) -> PreparedTaskLineParsingPolicy | None:
    try:
        return cast(PreparedTaskLineParsingPolicy, di.get("task_line_policy"))
    except KeyError:
        return None
```

```python
# Extraction Layer Return Type Pattern (Phase 2a)
from prism.scanner_data.contracts_request import TaskAnnotation

def parse_task_annotation(line: str) -> TaskAnnotation | None:
    """Parse task annotation from comment line.
    
    Returns:
        TaskAnnotation dict with kind, text, etc. or None if not an annotation.
    """
    if not line.strip().startswith("##"):
        return None
    return {"kind": "comment_doc", "text": line.strip()}
```

```python
# Plugin Protocol Implementation Pattern (Phase 2b)
from prism.scanner_data.contracts_request import VariableRow

class AnsibleVariableDiscoveryPlugin:
    """Ansible plugin implementing VariableDiscoveryPlugin protocol."""
    
    def discover_static_variables(
        self,
        role_path: str,
        options: ScanOptionsDict,
    ) -> tuple[VariableRow, ...]:
        """Discover static variables in role."""
        # Implementation
        return tuple(variables)
```

### C. Q3b Initiative Placeholder (Test Suite Typing)

**Plan ID**: q3-init6b-test-suite-typing  
**Timeline**: 2-3 weeks (after Q3a completion)  
**Scope**: 35 test file mypy errors  
**Strategy**: Fixture typing, parametrization safety, assertion helpers  
**ROI**: Lower than Q3a (secondary validation vs. CI tests)  
**Status**: Scheduled Q3b, pending Q3a closure  

---

## Document Metadata

- **Plan ID**: q3-init6-implementation-roadmap
- **Version**: 1.0
- **Status**: READY FOR APPROVAL
- **Last Updated**: May 9, 2026
- **Next Review**: After Phase 0 blockers resolved

