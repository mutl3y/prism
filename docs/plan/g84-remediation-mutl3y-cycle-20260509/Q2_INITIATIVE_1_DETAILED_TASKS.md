# Q2 Initiative 1: DI Container God-Object Decomposition
## Detailed Task Breakdown

**Timeline**: Weeks 1-2 (May 12-26, 2026)
**Goal**: Decompose 1000+ line DIContainer into PluginResolver + ServiceLocator + slim DIContainer
**Target**: 17 findings resolved, <300 lines in DIContainer, 1150+ tests passing

---

## Week 1: Foundation & Design (May 12-18)

### Task 1.1: Design Review & Scope Definition (1 day)
**Owner**: Lead Architect
**Deliverables**:
- [ ] Review existing DIContainer (1000+ lines)
- [ ] Identify all 17 factory methods
- [ ] Map dependencies between factories
- [ ] Document call sites (scanner_core, scanner_extract, scanner_plugins)
- [ ] Create architecture sketch (DIContainer → PluginResolver + ServiceLocator)

**Success Criteria**:
- Scope document signed off
- Call site map completed
- No unknowns remain

---

### Task 1.2: Create PluginResolver Interface & Protocol (2 days)
**Owner**: Type Safety Engineer
**Deliverables**:
- [ ] Define `PluginResolutionProtocol` (TypedDict/Protocol)
  - `resolve_plugin(protocol_type: str, key: str) -> Plugin`
  - `list_plugins(protocol_type: str) -> List[str]`
  - `register_plugin(protocol_type: str, key: str, impl: Type)`
- [ ] Create `src/prism/scanner_core/plugin_resolver.py` (scaffold)
- [ ] Add type annotations to all methods
- [ ] Document resolution strategy (registry-based, DI-backed)

**Success Criteria**:
- Interface frozen and documented
- Mypy passes (strict mode)
- Call sites identified

**Estimated Output**: `plugin_resolver.py` (100+ lines), `protocols.py` updates

---

### Task 1.3: Extract PluginResolver Implementation (2 days)
**Owner**: Refactoring Engineer
**Input**: 17 `_get_*_plugin()` methods from DIContainer
**Deliverables**:
- [ ] Extract all plugin factory methods to `PluginResolver`
- [ ] Implement registry-based lookup
- [ ] Add caching for resolved plugins
- [ ] Add validation (protocol matching, impl validation)
- [ ] Unit tests for PluginResolver (80%+ coverage)

**Code Pattern**:
```python
# Before (di.py):
def _get_task_annotation_plugin(self):
    return self._task_annotation_plugin

# After (plugin_resolver.py):
def resolve_plugin(self, protocol_type: str, key: str):
    return self._registry.get(f"{protocol_type}:{key}")
```

**Success Criteria**:
- All 8-12 plugin methods extracted
- Registry operational
- 80%+ unit test coverage
- Zero behavioral changes

**Estimated Output**: `plugin_resolver.py` (300+ lines), `test_plugin_resolver.py` (250+ lines)

---

### Task 1.4: Create ServiceLocator Interface & Protocol (1 day)
**Owner**: Type Safety Engineer
**Deliverables**:
- [ ] Define `ServiceLocationProtocol` (TypedDict/Protocol)
  - `get_service(service_type: Type[T]) -> T`
  - `register_service(service_type: Type, factory: Callable)`
- [ ] Create `src/prism/scanner_core/service_locator.py` (scaffold)
- [ ] Add type annotations
- [ ] Document service resolution strategy

**Success Criteria**:
- Interface frozen
- Mypy strict mode passing
- Call sites identified

**Estimated Output**: `service_locator.py` (100+ lines), protocol definitions

---

## Week 2: Implementation & Integration (May 19-26)

### Task 2.1: Extract ServiceLocator Implementation (2 days)
**Owner**: Refactoring Engineer
**Input**: 17 `factory_*()` methods from DIContainer
**Deliverables**:
- [ ] Extract all factory methods to `ServiceLocator`
- [ ] Implement config-driven service registration
- [ ] Support service composition (nested factories)
- [ ] Add factory validation
- [ ] Unit tests for ServiceLocator (80%+ coverage)

**Code Pattern**:
```python
# Before (di.py):
def factory_scanner_context(self, ...):
    return ScannerContext(...)

# After (service_locator.py):
def register_service(self, service_type, factory):
    self._factories[service_type] = factory

def get_service(self, service_type):
    return self._factories[service_type]()
```

**Success Criteria**:
- All 5-7 factory methods extracted
- Composition working (factories can depend on other services)
- 80%+ unit test coverage
- Zero behavioral changes

**Estimated Output**: `service_locator.py` (300+ lines), `test_service_locator.py` (250+ lines)

---

### Task 2.2: Slim DIContainer & Create Facade (2 days)
**Owner**: Integration Engineer
**Deliverables**:
- [ ] Remove all extracted methods from DIContainer
- [ ] Keep only orchestration logic (composition, lifecycle)
- [ ] Create facade methods for backward compatibility
- [ ] Integration tests (DIContainer + PluginResolver + ServiceLocator)
- [ ] Verify all call sites work

**Code Pattern**:
```python
# Before (di.py):
class DIContainer:
    def factory_*(...): ... (many methods)
    def _get_*_plugin(...): ... (many methods)

# After (di.py):
class DIContainer:
    def __init__(self, plugin_resolver, service_locator, config):
        self.plugins = plugin_resolver
        self.services = service_locator

    def factory_scanner_context(self, ...):
        return self.services.get_service(ScannerContext)
```

**Success Criteria**:
- DIContainer < 300 lines (down from 1000+)
- Backward compatibility maintained
- All call sites still work
- Integration tests passing

**Estimated Output**: Slim `di.py` (~200 lines), integration tests

---

### Task 2.3: Full Integration & Testing (2 days)
**Owner**: QA Engineer
**Deliverables**:
- [ ] Run full pytest suite: `pytest -v src/prism/tests/`
- [ ] Verify all 1150+ tests passing
- [ ] Type check: `mypy src/prism/scanner_core/`
- [ ] Lint: `ruff check src/prism/ && black --check src/prism/`
- [ ] Performance benchmarks (verify no regression)
- [ ] Document any behavior changes

**Success Criteria**:
- 1150+ tests passing (no regressions)
- Mypy: 0 new errors
- Ruff: Clean
- Performance: ≤5% slowdown acceptable

**Estimated Output**: Test report, performance baseline

---

### Task 2.4: Documentation & Handoff (1 day)
**Owner**: Technical Writer
**Deliverables**:
- [ ] Update architecture docs (layer boundaries, component design)
- [ ] Document PluginResolver protocols & patterns
- [ ] Document ServiceLocator usage & composition
- [ ] Update DIContainer docstring (new composition approach)
- [ ] Create migration guide for future code (how to add new plugins/services)

**Success Criteria**:
- All public APIs documented
- Design decisions captured
- Team can extend without asking questions

**Estimated Output**: Architecture documentation, migration guide

---

## Parallel Work (Can start immediately)

### Task 1.P1: Prepare Test Infrastructure (1 day)
**Owner**: Test Engineer
**Deliverables**:
- [ ] Create `test_plugin_resolver.py` template
- [ ] Create `test_service_locator.py` template
- [ ] Setup mocking infrastructure
- [ ] Create fixture definitions

---

### Task 1.P2: Update CI/CD for New Modules (1 day)
**Owner**: DevOps Engineer
**Deliverables**:
- [ ] Add new modules to mypy configuration
- [ ] Update import validation in CI
- [ ] Add coverage tracking for new files
- [ ] Setup incremental build caching

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Breaking changes in DIContainer | Medium | High | Backward compatibility layer, extensive testing |
| Performance regression | Low | Medium | Benchmark suite, before/after comparison |
| Type system issues | Low | High | Mypy strict mode, protocol validation |
| Call site integration issues | Medium | High | Call site audit, integration tests |

---

## Validation Checkpoints

**Checkpoint 1 (Day 2)**: PluginResolver design reviewed, protocols approved
**Checkpoint 2 (Day 5)**: PluginResolver implementation done, 80%+ unit tests passing
**Checkpoint 3 (Day 9)**: ServiceLocator implementation done, integration tests passing
**Checkpoint 4 (Day 10)**: Full pytest suite green, mypy clean, ready for production

---

## Success Metrics

- ✅ 17 DI findings resolved
- ✅ DIContainer: <300 lines (from 1000+)
- ✅ 1150+ tests passing (no regressions)
- ✅ Mypy: 0 new errors
- ✅ Ruff: Clean
- ✅ 80%+ unit test coverage for new modules
- ✅ Zero behavioral changes
- ✅ Performance: ≤5% variance acceptable

---

## Estimated Effort

- **Planning**: 1 day
- **PluginResolver**: 4 days
- **ServiceLocator**: 4 days
- **Integration**: 2 days
- **Testing**: 1 day
- **Documentation**: 1 day
- **Parallel work**: 2 days
- **Total**: 10-11 days (fits in 2 weeks with buffer)

---

## Estimated Cost (Tier 2)

- Refactoring work: 4 days × Tier 2 = $0.040
- Type safety: 2 days × Tier 2 = $0.015
- Testing/QA: 2 days × Tier 1 = $0.005
- **Total**: $0.060 (within Initiative 1 budget of $0.080-0.120)

---

## Dependencies

**Blockers**: None (can start immediately)
**Depends on**: None
**Enables**: Initiative 2 (PolicyManager), Initiative 5 (Layer Boundaries)

---

## Deliverables Checklist

- [ ] `plugin_resolver.py` (300+ lines, 80%+ tested)
- [ ] `service_locator.py` (300+ lines, 80%+ tested)
- [ ] Slim `di.py` (~200 lines)
- [ ] `test_plugin_resolver.py` (250+ lines)
- [ ] `test_service_locator.py` (250+ lines)
- [ ] Integration test suite passing
- [ ] Architecture documentation updated
- [ ] Migration guide created
- [ ] All 1150+ pytest tests passing
- [ ] Mypy clean, Ruff clean, Black formatted
- [ ] Performance baseline established

---

**Status**: ✅ READY FOR EXECUTION
**Start Date**: May 12, 2026
**End Date**: May 26, 2026
