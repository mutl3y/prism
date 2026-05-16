# Q2 Initiative 2: PolicyManager Extraction & Consolidation

**Timeline**: Weeks 3-4 (May 26 - June 9, 2026)  
**Dependency**: Initiative 1 (DI Container) must be complete  
**Goal**: Consolidate policy ownership from 4 modules into single `PolicyManager`  
**Target**: 8 findings resolved, 0 duplicate validation calls, 1150+ tests passing  

---

## Executive Summary

**Problem**: Policy resolution scattered across 4 modules:
- `scan_request.py`: InitialPolicies construction
- `di.py`: DIContainer policy resolver methods
- `scanner_extract/task_extract_adapters.py`: TaskLineParsingPolicy resolution
- `scanner_plugins/defaults.py`: Plugin factory fallbacks

**Solution**: Centralize all policy resolution → `PolicyManager` class in `scanner_core`

**Impact**: Single source of truth for policy lifecycle, predictable resolution order, eliminates duplicate validation

---

## Week 3: Analysis & Design (May 26 - June 2)

### Task 2.1: Policy Ownership Audit (1 day)
**Owner**: Architecture Lead  
**Deliverables**:
- [ ] Map all policy resolution call sites (4 modules)
  - `scan_request.py`: Lines 45-120 (initial policy construction)
  - `di.py`: 10+ `_get_*_policy()` methods (if any remain post-Initiative 1)
  - `task_extract_adapters.py`: Lines 80-150 (TaskLineParsingPolicy calls)
  - `defaults.py`: Lines 200-300 (plugin factory fallbacks)
- [ ] Document resolution order dependencies
- [ ] Identify duplicate validation logic
- [ ] List all PreparedPolicy* TypedDicts used

**Success Criteria**:
- All call sites mapped
- Dependency graph created
- Duplicate validation identified (estimate 5-10 duplicate checks)

**Output**: `policy-audit-map.md` (reference document)

---

### Task 2.2: Design PolicyManager Interface (1 day)
**Owner**: Type Safety Engineer  
**Deliverables**:
- [ ] Define `PolicyManager` Protocol
  ```python
  class PolicyManager(Protocol):
      def resolve_task_line_parsing_policy(
          self, di: DIContainer
      ) -> PreparedTaskLineParsingPolicy: ...
      
      def resolve_yaml_parsing_policy(
          self, di: DIContainer
      ) -> PreparedYAMLParsingPolicy: ...
      
      def resolve_jinja_analysis_policy(
          self, di: DIContainer
      ) -> PreparedJinjaAnalysisPolicy: ...
      
      def resolve_variable_extractor_policy(
          self, di: DIContainer
      ) -> PreparedVariableExtractorPolicy: ...
  ```
- [ ] Add validation contracts (what each policy must contain)
- [ ] Document resolution strategy (registry-based with fallbacks)
- [ ] Define immutability contracts (all policies frozen/immutable)

**Success Criteria**:
- Protocol complete and documented
- Mypy validates protocol compliance
- All call sites can be expressed via protocol

**Output**: `src/prism/scanner_core/policy_manager.py` (scaffold, 50 lines)

---

### Task 2.3: Identify Integration Points (1 day)
**Owner**: Integration Lead  
**Deliverables**:
- [ ] Document 4 integration points (entry/exit for each module)
- [ ] Create before/after code samples for each
- [ ] Identify temporary aliases needed for backward compatibility
- [ ] Plan rollout sequence (which module to refactor first)

**Success Criteria**:
- Integration plan signed off
- Rollout sequence clear
- No surprises during implementation

**Output**: `integration-plan.md` (implementation guide)

---

### Task 2.4: Create Test Infrastructure (2 days)
**Owner**: Test Engineer  
**Parallel with 2.1-2.3**  
**Deliverables**:
- [ ] Create `test_policy_manager.py` with fixtures
  - Mock DIContainer
  - Mock PluginRegistry
  - Sample policies for all 4 types
- [ ] Create integration test templates
- [ ] Setup parity tests (validate old vs new resolution gives same result)

**Success Criteria**:
- Test fixtures work
- 20+ test cases stubbed out
- Integration tests ready for week 2

**Output**: `test_policy_manager.py` (test scaffold, 150+ lines)

---

## Week 4: Implementation & Integration (June 2-9)

### Task 2.5: Implement PolicyManager Core (2 days)
**Owner**: Refactoring Engineer  
**Deliverables**:
- [ ] Copy all policy resolution logic from 4 modules into `PolicyManager`
- [ ] Implement registry-based resolution (check registry first, fallback to DIContainer)
- [ ] Add caching for resolved policies (prevent repeated resolution)
- [ ] Implement validation (ensure all policy contracts satisfied)
- [ ] Add logging for policy resolution (diagnostic capability)

**Code Pattern**:
```python
class PolicyManager:
    def __init__(self, registry: PluginRegistry, di: DIContainer):
        self._registry = registry
        self._di = di
        self._policy_cache = {}
    
    def resolve_task_line_parsing_policy(
        self, di: DIContainer
    ) -> PreparedTaskLineParsingPolicy:
        cache_key = "task_line_parsing"
        if cache_key in self._policy_cache:
            return self._policy_cache[cache_key]
        
        # Try registry first
        impl = self._registry.get("task_line_parsing_policy")
        if impl:
            policy = impl(di)
        else:
            # Fallback to DIContainer
            policy = di.resolve_task_line_parsing_policy()
        
        # Validate
        self._validate_policy(policy)
        self._policy_cache[cache_key] = policy
        return policy
```

**Success Criteria**:
- All 4 policy types resolvable
- Caching working
- 80%+ unit test coverage
- Validation catches invalid policies

**Output**: `policy_manager.py` (implementation, 300+ lines), unit tests (250+ lines)

---

### Task 2.6: Refactor scan_request.py (1 day)
**Owner**: Integration Engineer  
**Deliverables**:
- [ ] Remove policy construction from `scan_request.py`
- [ ] Create delegation to `PolicyManager`
- [ ] Add parity tests (verify old and new give same results)
- [ ] Keep backward compatibility layer if needed

**Before/After**:
```python
# Before (scan_request.py):
def build_run_scan_options_canonical(...):
    # 50+ lines of policy construction
    task_line_policy = load_task_line_parsing_policy(di)
    yaml_policy = load_yaml_parsing_policy(di)
    # ... etc

# After (scan_request.py):
def build_run_scan_options_canonical(...):
    policy_manager = di.get_service(PolicyManager)
    task_line_policy = policy_manager.resolve_task_line_parsing_policy(di)
    yaml_policy = policy_manager.resolve_yaml_parsing_policy(di)
    # ... etc
```

**Success Criteria**:
- `scan_request.py` code reduced by 30%
- All 20+ parity tests pass
- No behavior changes

**Output**: Updated `scan_request.py`, parity test suite

---

### Task 2.7: Refactor task_extract_adapters.py (1 day)
**Owner**: Integration Engineer  
**Deliverables**:
- [ ] Remove `resolve_*_policy()` calls from `task_extract_adapters.py`
- [ ] Replace with PolicyManager delegation
- [ ] Add parity tests
- [ ] Verify integration with task extraction

**Success Criteria**:
- Policy resolution centralized
- 15+ parity tests pass
- Zero behavior changes

---

### Task 2.8: Refactor scanner_plugins/defaults.py (1 day)
**Owner**: Integration Engineer  
**Deliverables**:
- [ ] Move plugin factory fallback logic to PolicyManager
- [ ] Maintain plugin resolution order
- [ ] Add parity tests

**Success Criteria**:
- Plugin resolution consistent
- 10+ parity tests pass
- Zero behavior changes

---

### Task 2.9: Full Integration Testing & Validation (1 day)
**Owner**: QA Engineer  
**Deliverables**:
- [ ] Run full pytest: `pytest -v` (target 1150+ passing)
- [ ] Run mypy: `mypy src/prism/scanner_core/` (0 new errors)
- [ ] Run ruff + black (clean)
- [ ] Verify all policy types resolvable end-to-end
- [ ] Performance check (policy resolution latency)

**Success Criteria**:
- 1150+ tests passing (no regressions)
- Mypy clean
- Policy resolution latency < 5ms
- All 8 findings verified resolved

**Output**: Test report, performance baseline

---

### Task 2.10: Documentation & Handoff (0.5 days)
**Owner**: Technical Writer  
**Deliverables**:
- [ ] Update architecture docs (PolicyManager ownership)
- [ ] Create policy resolution guide (how to add new policy types)
- [ ] Document policy validation contracts
- [ ] Update DIContainer docs (post-Initiative 1)

**Output**: Architecture documentation updates

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Duplicate validation creates inconsistencies | Medium | High | Parity test suite, centralized validation |
| Policy resolution order regression | Low | High | Extensive integration tests |
| Cache invalidation issues | Low | Medium | Clear cache semantics, unit tests |
| Backward compatibility breaks | Low | High | Compatibility layer, gradual rollout |

---

## Validation Checkpoints

**Checkpoint 1 (Day 2)**: PolicyManager protocol approved, audit complete  
**Checkpoint 2 (Day 5)**: PolicyManager implementation done, 80%+ unit tests  
**Checkpoint 3 (Day 8)**: All 4 modules refactored, parity tests passing  
**Checkpoint 4 (Day 10)**: Full pytest suite green, mypy clean, ready for closure  

---

## Success Metrics

- ✅ 8 findings resolved
- ✅ Duplicate validation calls eliminated (0 remaining)
- ✅ 1150+ tests passing (no regressions)
- ✅ Mypy: 0 new errors
- ✅ Ruff: Clean
- ✅ 80%+ unit test coverage for PolicyManager
- ✅ Zero behavior changes
- ✅ Performance: policy resolution latency < 5ms

---

## Estimated Effort

- **Audit & Analysis**: 4 days (parallel with Init 1)
- **Implementation**: 5 days
- **Integration**: 3 days
- **Testing**: 2 days
- **Documentation**: 1 day
- **Total**: 10 days (fits in 2 weeks)

---

## Estimated Cost (Tier 2)

- Policy consolidation: 5 days × Tier 2 = $0.040
- Integration: 2 days × Tier 1 = $0.005
- **Total**: $0.045 (within budget)

---

## Dependencies

**Blocked by**: Initiative 1 (DI Container decomposition)  
**Blocks**: Initiative 3 (Marker-Prefix Boundary)  
**Enables**: Initiative 5 (Layer Boundaries)

---

## Deliverables Checklist

- [ ] `policy_manager.py` (300+ lines, 80%+ tested)
- [ ] `test_policy_manager.py` (250+ lines)
- [ ] Refactored `scan_request.py`
- [ ] Refactored `task_extract_adapters.py`
- [ ] Refactored `scanner_plugins/defaults.py`
- [ ] Parity test suite (50+ tests)
- [ ] Integration test suite (30+ tests)
- [ ] Architecture documentation updated
- [ ] All 1150+ pytest tests passing
- [ ] Mypy clean, Ruff clean, Black formatted
- [ ] 8 findings verified resolved

---

**Status**: ✅ READY FOR EXECUTION (after Initiative 1 complete)  
**Start Date**: May 26, 2026  
**End Date**: June 9, 2026
