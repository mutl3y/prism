# Q3 Initiative 5 — Layer Boundary Remediation Roadmap

**Status**: ✅ PROPOSED (Audit Phase Complete — Ready for Implementation Planning)  
**Objective**: Close 5 accidental layer violations + establish permanent enforcement  
**Timeline**: Q3 Initiative 5-6 (8-10 weeks projected)  
**Model**: Follow Q2 wave closure pattern (seam-first, strict validation gates)

---

## 1. Violation Remediation Priority Matrix

### High Severity (Blocking Testability, Deployability)

| Violation | Layer Path | Files | Lines | Effort | Risk | Dependency | Window |
|-----------|-----------|-------|-------|--------|------|-----------|--------|
| **LB-1002** | L3→L1 | 1 | 30+ | 8-12h | HIGH | Q2 I3 DI patterns | Week 3-4 |
| **LB-1001** | L1→L4 | 4 | 8 | 2-3h | LOW | Q2 I2 API patterns | Week 1-2 |

### Medium Severity (Affecting Maintenance)

| Violation | Type | Files | Lines | Effort | Risk | Window |
|-----------|------|-------|-------|--------|------|--------|
| Future L1→L4 imports | Prevention | - | - | 1-2h | LOW | Week 1 (enforce) |
| Future L3→L1 imports | Prevention | - | - | 1-2h | LOW | Week 1 (enforce) |

### Low Severity (Already Correct or Intentional)

- ✅ L0→L6 TYPE_CHECKING import (runtime safe)
- ✅ L5→L3 plugin_seams.py (intentional facade)
- ✅ L4→L0 downward imports (correct layer flow)
- ✅ L7 facade skip-layer imports (API facade allowed)

---

## 2. Phased Remediation Plan

### Phase 0: Foundation (Week 1)

**Goal**: Establish enforcement, document violations, baseline tests

#### Task 0.1: Create Boundary Tests (Day 1)
- **File**: `src/prism/tests/test_layer_boundaries.py`
- **Effort**: 2 hours
- **Deliverable**: 4 test cases
  - `test_layer_boundary_l1_extract_no_io_imports()` (should FAIL initially)
  - `test_layer_boundary_l3_plugins_no_extract_internals()` (should FAIL initially)
  - `test_layer_boundary_l0_core_no_upward_imports()` (should PASS)
  - `test_circular_dependencies_none()` (should PASS)
- **Validation**: Run tests, confirm initial failures match violations found

#### Task 0.2: Add Ruff Configuration (Day 2)
- **Files**: `pyproject.toml`, new custom rule stubs
- **Effort**: 1 hour
- **Deliverable**: Ruff config with layer boundary rules (disabled by default for CI)
- **Validation**: `ruff check src/prism --select LB` reports 2 violations

#### Task 0.3: Document Current State (Day 3-4)
- **Files**:
  - `docs/plan/q3-init5-layer-dependency-audit.md` ✅ Complete (this document)
  - `docs/plan/q3-init5-boundary-enforcement-rules.yaml` ✅ Complete (this document)
  - `src/prism/LAYER_BOUNDARIES.md` (new, quick reference for developers)
- **Effort**: 1 hour
- **Deliverable**: 3 documents (planning, enforcement rules, developer guide)

#### Task 0.4: Create Remediation Epic in GitHub (Day 5)
- **Issue**: "Q3 Initiative 5: Layer Boundary Remediation"
- **Effort**: 30 minutes
- **Deliverable**: Epic with 2 child issues (LB-1001 + LB-1002)
- **Links**: Reference audit + enforcement rules

**Phase 0 Status Gate**: ✅ PASS
- All tests written (failing for violations, passing for correct layers)
- Ruff rules configured
- Documentation complete
- GitHub issues created
- Ready for Phase 1 implementation

---

### Phase 1: Violation Closure (Weeks 2-3)

**Goal**: Close 2 violations, pass all tests, zero CI failures

#### Wave 1.1: Close LB-1001 (L1→L4 Extract imports I/O) — Week 2

**Violation**: 4 extract files import YAML loader from scanner_io  
**Target**: Move YAML utilities to scanner_data layer  
**Effort**: 2-3 hours  
**Risk**: LOW (pure utility move)

##### Task 1.1.1: Create YAML utilities in scanner_data (Day 1)
- **File**: `src/prism/scanner_data/yaml_utils.py` (new)
- **Content**:
  - `load_yaml_file()` (moved from scanner_io/loader.py)
  - `parse_yaml_candidate()` (moved from scanner_io/loader.py)
  - `_ordered_parallel_map()` (moved from scanner_io/loader.py)
- **Effort**: 1 hour
- **Validation**: Functions identical to originals, no behavior change

##### Task 1.1.2: Update extract imports (Day 1)
- **Files**:
  - `scanner_extract/variable_extractor.py` (line 17)
  - `scanner_extract/discovery.py` (lines 11-13)
  - `scanner_extract/dataload.py` (line 8)
  - `scanner_extract/task_file_traversal.py` (line 15)
- **Change**: `from prism.scanner_io.loader import ...` → `from prism.scanner_data.yaml_utils import ...`
- **Effort**: 30 minutes
- **Validation**: Tests pass, no behavior change

##### Task 1.1.3: Update scanner_io imports (Day 2)
- **File**: `src/prism/scanner_io/loader.py`
- **Change**: Import from `scanner_data.yaml_utils` instead of defining locally
- **Effort**: 15 minutes
- **Validation**: Tests pass, scanner_io behavior unchanged

##### Task 1.1.4: Validate + Test (Day 2)
- **Steps**:
  - Run test: `test_layer_boundary_l1_extract_no_io_imports()` → ✅ PASS
  - Run full test suite: `pytest src/prism/tests/ -q` → ✅ GREEN
  - Run lint: `ruff check src/prism --select LB` → 1 violation remaining (LB-1002)
- **Effort**: 1 hour
- **Validation**: LB-1001 closed, tests passing

**Wave 1.1 Closure Criteria**: ✅ ALL GREEN
- Test passes
- No new warnings in lint
- Extract layer no longer depends on I/O
- Existing tests unchanged

---

#### Wave 1.2: Close LB-1002 (L3→L1 Ansible plugin imports Extract) — Weeks 2-3

**Violation**: Ansible plugin imports 30+ extract utilities directly  
**Target**: Refactor plugin to use DI/Core APIs (follow MP1 pattern)  
**Effort**: 8-12 hours  
**Risk**: HIGH (behavior change potential)  
**Strategy**: Plugin facade adapter pattern

##### Task 1.2.1: Design Plugin Adapter Layer (Day 1)
- **Files**: `src/prism/scanner_plugins/interfaces.py` (update)
- **Content**:
  - Define plugin interface for Ansible extraction
  - Extract public contracts from extract utilities
  - Document which Core/DI APIs replace each extract import
- **Effort**: 2 hours
- **Deliverable**: Interface specification (1-2 pages)
- **Example interface**:
  ```python
  class AnsibleExtractorPlugin(Protocol):
      """Plugin interface for Ansible extraction (replaces direct extract imports)."""
      def collect_task_files(self, di: DIContainer, role_path: str) -> list[str]: ...
      def parse_task_file(self, path: str) -> TaskData: ...
      def extract_variables(self, di: DIContainer, tasks: list[TaskData]) -> VariableMap: ...
      # ... other methods
  ```

##### Task 1.2.2: Create Adapter Seam (Day 2)
- **Files**: `src/prism/scanner_plugins/ansible/adapters.py` (new)
- **Content**:
  - Single file that wraps all extract imports
  - Centralizes all L3→L1 violation imports in one place
  - Provides DI-friendly API to Ansible plugin
- **Effort**: 3 hours
- **Validation**: All extract imports moved to adapters.py
- **Example**:
  ```python
  # adapters.py: SINGLE PLACE where ansible plugin imports extract
  from prism.scanner_extract.task_file_traversal import collect_task_files
  from prism.scanner_extract.task_annotation_parsing import parse_annotation
  # ... other imports
  
  def collect_ansible_tasks(di: DIContainer, role_path: str) -> list[str]:
      """Adapter: collect_task_files with DI support."""
      return collect_task_files(role_path)  # Internal detail
  ```

##### Task 1.2.3: Refactor Ansible Plugin (Day 2-3)
- **Files**: `src/prism/scanner_plugins/ansible/extract_utils.py` + related
- **Changes**:
  - Replace all `from prism.scanner_extract.X import Y` with `from .adapters import Y`
  - Update 30+ import lines to use adapter layer
  - No logic changes, only import path changes
- **Effort**: 3 hours
- **Validation**: Grep confirms no scanner_extract imports in main Ansible files

##### Task 1.2.4: Test + Validate (Day 4)
- **Tests**:
  - Run Ansible-specific tests: `pytest src/prism/tests/ -k ansible -q` → ✅ GREEN
  - Run layer boundary test: `test_layer_boundary_l3_plugins_no_extract_internals()` → ✅ PASS (except adapters.py exception)
  - Run full suite: `pytest src/prism/tests/ -q` → ✅ GREEN
  - Ruff check: `ruff check src/prism --select LB` → ✅ 0 violations
- **Effort**: 2 hours
- **Validation**: LB-1002 closed, all tests passing

##### Task 1.2.5: Document Exception (Day 4)
- **File**: `src/prism/LAYER_BOUNDARIES.md`
- **Content**: Add exception entry for `scanner_plugins/ansible/adapters.py`
  - Reason: Facade adapter seam (justified exception)
  - Scope: Only adapters.py, no other files
  - Review: Documented and marked for future review
- **Effort**: 15 minutes

**Wave 1.2 Closure Criteria**: ✅ ALL GREEN
- Ansible plugin tests pass
- Layer boundary test passes (with documented exception)
- No L3→L1 direct imports outside adapters.py
- Full test suite green
- Ruff clean

---

### Phase 1 Closure Gate

**Status**: All violations closed, tests passing

```bash
# Phase 1 validation command
pytest src/prism/tests/test_layer_boundaries.py -v && \
  ruff check src/prism --select LB && \
  pytest src/prism/tests/ -q && \
  black --check src/prism && \
  mypy src/prism

# Expected output:
# ✅ test_layer_boundary_l0_core_no_upward_imports PASS
# ✅ test_layer_boundary_l1_extract_no_io_imports PASS
# ✅ test_layer_boundary_l3_plugins_no_extract_internals PASS (exception documented)
# ✅ test_circular_dependencies_none PASS
# ✅ ruff check: 0 violations
# ✅ pytest: all tests pass
# ✅ black: no changes needed
# ✅ mypy: no errors
```

**Phase 1 Artifacts**:
- ✅ `src/prism/tests/test_layer_boundaries.py` (4 tests, all passing)
- ✅ `src/prism/scanner_data/yaml_utils.py` (YAML utilities)
- ✅ `src/prism/scanner_plugins/ansible/adapters.py` (plugin facade)
- ✅ `src/prism/LAYER_BOUNDARIES.md` (developer guide with exceptions)
- ✅ Updated imports in 4 extract files + 1 plugin file

---

### Phase 2: Automation + CI Integration (Weeks 4-5)

**Goal**: Automate enforcement to prevent regression

#### Task 2.1: GitHub Actions Workflow (Day 1)
- **File**: `.github/workflows/layer-boundary-check.yml` (new)
- **Content**:
  - Run boundary tests
  - Run ruff layer checks
  - Detect circular dependencies
  - Block merge on violations
- **Effort**: 1 hour
- **Validation**: Workflow runs on PR, reports violations

#### Task 2.2: Lint Rule Enhancement (Day 2)
- **File**: `pyproject.toml`
- **Changes**: Enable `LB` rules in default lint check
- **Effort**: 30 minutes
- **Validation**: `ruff check src/prism` reports any future violations

#### Task 2.3: Developer Documentation (Day 3)
- **Files**:
  - `src/prism/LAYER_BOUNDARIES.md` (update with CI details)
  - `.github/DEVELOPMENT.md` (update with enforcement info)
  - `docs/CONTRIBUTING.md` (add layer boundary section)
- **Effort**: 1 hour
- **Deliverable**: Clear guidance on layer boundaries for contributors

#### Task 2.4: CI Integration Validation (Day 4)
- **Steps**:
  - Run workflow manually on main branch (should pass)
  - Create test PR that violates boundary, confirm it's blocked
  - Test exception handling (TYPE_CHECKING, facades)
- **Effort**: 2 hours
- **Validation**: CI enforcement working as designed

**Phase 2 Closure Criteria**: ✅ CI AUTOMATED
- Workflow passes on main
- Test violations blocked
- Exceptions properly documented
- CI integration complete

---

### Phase 3: Metrics + Dashboarding (Week 6)

**Goal**: Visibility into layer health, track future violations

#### Task 3.1: Layer Health Metrics
- **Metrics**:
  - Total violations over time (should stay at 0)
  - Exception count + reason tracking
  - Layer coupling metrics (imports per layer)
  - Circular dependency detection runs
- **Effort**: 2 hours
- **Tool**: Custom script + GitHub Actions artifacts

#### Task 3.2: Dashboard (Optional)
- **Visibility**: Metrics visible in GitHub project board
- **Effort**: 1 hour
- **Deliverable**: Link to metrics in DEVELOPMENT.md

---

## 3. Rollback Strategy

### If Phase 1 Closure Fails

**Scenario**: Tests fail after Wave 1.1 or 1.2

**Rollback Steps**:
1. Revert commits from failing wave
2. Analyze test failures (usually import errors or logic bugs)
3. Re-attempt with extended review cycle
4. Add additional test coverage before retry

**Prevention**: 
- All tests pass before merge
- No logic changes (only import paths)
- Run full test suite before attempting next wave

---

## 4. Success Criteria

### Phase 1 Success
- [ ] LB-1001 closed (L1→L4 imports removed)
- [ ] LB-1002 closed (L3→L1 imports contained to seam)
- [ ] All 4 boundary tests passing
- [ ] All extract files pass ruff check
- [ ] Full test suite green (no regressions)
- [ ] Zero new violations introduced

### Phase 2 Success
- [ ] CI workflow created and validated
- [ ] Ruff layer rules enabled
- [ ] Test violations blocked in CI
- [ ] Developer documentation updated
- [ ] No future violations possible (enforced)

### Phase 3 Success
- [ ] Metrics dashboard running
- [ ] Layer health tracked
- [ ] Historical trend visible

---

## 5. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Ansible plugin behavior changes** | MEDIUM | HIGH | Extended Ansible-specific test coverage before merge |
| **Unexpected import dependencies** | LOW | MEDIUM | Full test suite must pass before each commit |
| **CI workflow failures** | MEDIUM | LOW | Validate workflow locally before merging |
| **Developer confusion on layer rules** | MEDIUM | LOW | Comprehensive documentation + examples |

---

## 6. Timeline Summary

```
Week 1 (Phase 0)
  Mon: Write boundary tests
  Tue: Configure ruff rules
  Wed-Thu: Document violations + enforcement rules
  Fri: Create GitHub issues

Week 2 (Phase 1, Wave 1.1)
  Mon-Tue: Move YAML utilities to scanner_data
  Wed: Update extract imports
  Thu: Validate tests, ruff clean

Week 2-3 (Phase 1, Wave 1.2)
  Fri-Mon: Design plugin adapter interface
  Tue-Wed: Implement ansible adapters.py
  Thu-Fri: Refactor ansible plugin, full validation

Week 4 (Phase 2)
  Mon: Implement CI workflow
  Tue: Enable ruff rules
  Wed: Developer documentation
  Thu-Fri: Validate CI enforcement

Week 5-6 (Phase 3)
  Mon-Tue: Metrics implementation (optional)
  Wed: Dashboard setup (optional)
  Thu-Fri: Final validation

Total: ~6 weeks, 50-60 engineering hours
```

---

## 7. Deployment Strategy

### Blue-Green Deployment
1. Merge Phase 1 violations (CI enforces, all tests passing)
2. Deploy to staging → verify layer dependencies clean
3. Deploy to production → layer boundaries now enforced

### Rollback Trigger
- Any CI job fails due to layer violations
- Metrics show increase in violations (should be 0)
- Ansible plugin behavior changes reported

---

## 8. Post-Closure Maintenance

### Quarterly Review
- Verify no new violations introduced
- Review exception list (adapters.py, facades)
- Update metrics, trend analysis

### On-Call Duty
- Engineer on-call: respond to CI layer boundary failures
- Triage: is it a false positive or real violation?
- Remediation: fix violation or update rules

---

*Remediation Roadmap Complete — Ready for Phase 0 Execution*
