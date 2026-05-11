# Q2 Initiative 3: Marker-Prefix Boundary Enforcement (MP1 Complete)

**Timeline**: Weeks 3-4 (May 26 - June 9, 2026)  
**Parallel with**: Initiative 2  
**Dependency**: Initiative 1 (DI Container) + Initiative 2 (PolicyManager)  
**Goal**: Complete MP1 contract - enforce ingress-only marker-prefix ownership  
**Target**: 5 findings resolved, 0 nested policy reads, 1150+ tests passing  

---

## Executive Summary

**Problem**: Marker-prefix resolution scattered across 5 modules, inconsistent ownership
- `scan_request.py`: Default marker-prefix
- `scanner_core/di.py`: DIContainer resolution (post-Init 1: removed)
- `scanner_extract/task_extract_adapters.py`: Dynamic resolution
- `scanner_core/scanner_context.py`: Policy context reads
- `scanner_plugins/ansible/task_keywords.py`: Ansible-specific overrides

**Solution**: Complete MP1 contract - enforce single ownership at ingress (scan_request.py)

**Impact**: 
- Marker-prefix is read-only in scanner_core (no runtime flipping)
- All consumers read from PreparedPolicyBundle only
- Ansible-specific logic encapsulated in plugin layer

---

## Week 3: Analysis & Design (May 26 - June 2)

### Task 3.1: MP1 Contract Audit (1 day)
**Owner**: Architecture Lead  
**Deliverables**:
- [ ] Identify all 5 marker-prefix resolution points
- [ ] Map all consumers (who reads marker-prefix)
- [ ] Document current ownership (scan_request.py is primary, but fallbacks exist)
- [ ] Audit for nested reads (e.g., scanner_context reading policy context reading marker-prefix)

**Success Criteria**:
- All resolution points mapped
- Consumers identified (10+ sites)
- Nested reads documented (estimate 3-5 problematic sites)

**Output**: `mp1-audit.md` (reference document)

---

### Task 3.2: Design MP1 Enforcement Mechanism (1 day)
**Owner**: Type Safety Engineer  
**Deliverables**:
- [ ] Define strict marker-prefix contract
  - Source of truth: `scan_request.build_run_scan_options_canonical()` (projection to PreparedPolicyBundle)
  - All consumers: read from `PreparedPolicyBundle.marker_prefix` only
  - No fallbacks or late resolution
- [ ] Create `MarkerPrefixContract` validation class
- [ ] Add runtime checks (assert marker-prefix present in bundle)
- [ ] Document exceptions (if any)

**Code Pattern**:
```python
# Enforce at bundle construction
def build_prepared_policy_bundle(...) -> PreparedPolicyBundle:
    marker_prefix = scan_request_options.get("comment_doc_marker_prefix", DEFAULT)
    return PreparedPolicyBundle(
        marker_prefix=marker_prefix,  # Fixed at bundle time
        # ... other policies
    )

# Consume from bundle (all sites)
def resolve_marker_prefix(bundle: PreparedPolicyBundle) -> str:
    if not bundle.marker_prefix:
        raise ValueError("MarkerPrefixContract violated: bundle missing marker_prefix")
    return bundle.marker_prefix
```

**Success Criteria**:
- Contract validated at type level
- Runtime checks in place
- All consumers identified

**Output**: `marker_prefix_contract.py` (enforcement module, 100+ lines)

---

### Task 3.3: Identify All Marker-Prefix Consumers (1 day)
**Owner**: Codebase Analyst  
**Deliverables**:
- [ ] Search all modules for `marker_prefix` usage (grep)
- [ ] Categorize consumers:
  - Direct: `"comment_doc_marker_prefix" in options`
  - Indirect: Read from prepared_policy_bundle
  - Problematic: Late resolution or fallbacks
- [ ] Document 10+ consumer sites with line numbers

**Success Criteria**:
- All consumers cataloged
- Problematic sites flagged
- Consumer map created

**Output**: `marker-prefix-consumers.md` (mapping document)

---

### Task 3.4: Create Test Infrastructure (1.5 days)
**Owner**: Test Engineer  
**Parallel with 3.1-3.3**  
**Deliverables**:
- [ ] Create `test_marker_prefix_enforcement.py` with fixtures
  - Test PreparedPolicyBundle with/without marker_prefix
  - Test enforcement errors
  - Test consumer contract validation
- [ ] Create integration tests for MP1 compliance
- [ ] Create regression tests (ensure Ansible overrides still work)

**Success Criteria**:
- Test fixtures ready
- 30+ test cases stubbed
- Integration tests ready

**Output**: `test_marker_prefix_enforcement.py` (test scaffold, 200+ lines)

---

## Week 4: Implementation & Enforcement (June 2-9)

### Task 3.5: Implement MarkerPrefixContract Enforcement (1 day)
**Owner**: Type Safety Engineer  
**Deliverables**:
- [ ] Create `MarkerPrefixContract` validation class
- [ ] Add `@marker_prefix_required` decorator for consumers
- [ ] Implement runtime assertions (fail fast on contract violation)
- [ ] Add logging for contract validation

**Code Pattern**:
```python
class MarkerPrefixContract:
    @staticmethod
    def validate(bundle: PreparedPolicyBundle) -> str:
        if bundle.marker_prefix is None:
            raise PrismRuntimeError(
                code="marker_prefix_contract_violated",
                message="PreparedPolicyBundle missing required marker_prefix"
            )
        return bundle.marker_prefix
```

**Success Criteria**:
- Contract enforced at all consumer sites
- Runtime assertions catch violations
- Zero silent fallbacks

**Output**: Enhanced bundle validation (50+ lines)

---

### Task 3.6: Fix task_extract_adapters.py - Remove Dynamic Resolution (1 day)
**Owner**: Integration Engineer  
**Deliverables**:
- [ ] Remove `resolve_marker_prefix()` calls from task_extract_adapters.py
- [ ] Add bundle parameter (already passed in most cases)
- [ ] Replace dynamic resolution with `MarkerPrefixContract.validate(bundle.marker_prefix)`
- [ ] Add integration tests

**Before/After**:
```python
# Before (task_extract_adapters.py):
def extract_task_annotation(...):
    marker_prefix = resolve_marker_prefix_from_options(options)  # ❌ Dynamic
    # ...

# After (task_extract_adapters.py):
def extract_task_annotation(..., bundle: PreparedPolicyBundle):
    marker_prefix = bundle.marker_prefix  # ✅ From bundle
    # ...
```

**Success Criteria**:
- No dynamic resolution in function body
- Bundle parameter always available
- 15+ integration tests pass

---

### Task 3.7: Fix scanner_context.py - Remove Policy Context Reads (1 day)
**Owner**: Integration Engineer  
**Deliverables**:
- [ ] Remove any nested `prepared_policy_bundle` reads in scanner_context
- [ ] Ensure marker_prefix passed as value, not read dynamically
- [ ] Add integration tests

**Success Criteria**:
- No nested policy reads
- Marker-prefix value is immutable within scanner_context
- 10+ integration tests pass

---

### Task 3.8: Complete Ansible Encapsulation (1 day)
**Owner**: Plugin Specialist  
**Deliverables**:
- [ ] Verify Ansible marker-prefix overrides work through plugin layer only
- [ ] Add tests for Ansible platform-specific marker-prefix handling
- [ ] Ensure no Ansible logic leaks into scanner_core

**Success Criteria**:
- Ansible overrides contained in plugin layer
- No Ansible imports in scanner_core (verify with grep)
- Ansible-specific tests passing

---

### Task 3.9: Full Integration Testing & Compliance Verification (1 day)
**Owner**: QA Engineer  
**Deliverables**:
- [ ] Run full pytest: `pytest -v` (target 1150+ passing)
- [ ] Verify all marker-prefix consumers use bundle only
- [ ] Audit for remaining dynamic resolution (grep for "resolve_marker_prefix")
- [ ] Performance check (no regression)
- [ ] Compliance report (MP1 contract fully enforced)

**Success Criteria**:
- 1150+ tests passing
- Zero dynamic resolution calls
- Zero Ansible logic in scanner_core
- MP1 contract enforced end-to-end

**Output**: MP1 Compliance Report

---

### Task 3.10: Documentation & Handoff (0.5 days)
**Owner**: Technical Writer  
**Deliverables**:
- [ ] Document MP1 contract (marker-prefix ingress-only ownership)
- [ ] Create developer guide (how to handle marker-prefix in plugins)
- [ ] Document Ansible-specific overrides (plugin layer)
- [ ] Update architecture docs

**Output**: MP1 Contract Documentation

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Breaking changes in marker-prefix resolution | Low | High | Extensive integration tests, compliance audit |
| Ansible-specific overrides break | Low | High | Plugin layer tests, isolation checks |
| Dynamic resolution still exists | Medium | High | Grep audit, static analysis |

---

## Validation Checkpoints

**Checkpoint 1 (Day 2)**: MP1 contract defined, audit complete  
**Checkpoint 2 (Day 5)**: All consumers migrated to bundle-only reads  
**Checkpoint 3 (Day 8)**: Integration tests passing, compliance audit done  
**Checkpoint 4 (Day 10)**: Full pytest green, MP1 contract enforced  

---

## Success Metrics

- ✅ 5 findings resolved
- ✅ 0 dynamic marker-prefix resolution remaining
- ✅ 0 nested policy context reads for marker-prefix
- ✅ 1150+ tests passing
- ✅ Mypy: 0 new errors
- ✅ Ruff: Clean
- ✅ Ansible-specific logic fully contained in plugin layer
- ✅ MP1 contract enforced end-to-end

---

## Estimated Effort

- **Audit & Analysis**: 3.5 days (parallel with Init 2)
- **Implementation**: 4 days
- **Testing & Verification**: 2 days
- **Documentation**: 0.5 days
- **Total**: 9 days (fits in 2 weeks, parallel with Init 2)

---

## Estimated Cost (Tier 2)

- Contract enforcement: 3 days × Tier 2 = $0.020
- Integration: 1 day × Tier 1 = $0.002
- **Total**: $0.022 (within budget)

---

## Dependencies

**Blocked by**: Initiative 1 + Initiative 2  
**Parallel with**: Initiative 2  
**Enables**: Q3 Advanced Caching (uses stable marker-prefix)  

---

## Deliverables Checklist

- [ ] `marker_prefix_contract.py` (100+ lines)
- [ ] `test_marker_prefix_enforcement.py` (200+ lines)
- [ ] Updated `task_extract_adapters.py` (removal of dynamic resolution)
- [ ] Updated `scanner_context.py` (removal of nested reads)
- [ ] Ansible plugin layer tests (20+ tests)
- [ ] Integration test suite (30+ tests)
- [ ] MP1 Compliance Report
- [ ] Architecture documentation updated
- [ ] All 1150+ pytest tests passing
- [ ] Mypy clean, Ruff clean
- [ ] 5 findings verified resolved

---

**Status**: ✅ READY FOR EXECUTION (after Initiative 1+2 partially complete)  
**Start Date**: May 26, 2026 (parallel with Init 2)  
**End Date**: June 9, 2026
