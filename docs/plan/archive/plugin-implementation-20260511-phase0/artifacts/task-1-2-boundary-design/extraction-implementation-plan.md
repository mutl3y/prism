# DIContainer Extraction Implementation Plan

## Executive Summary

This document provides the step-by-step refactoring guide for decomposing `DIContainer` into three classes:
1. **PluginResolver** (Phase 1) - Registry-driven plugin resolution
2. **ServiceLocator** (Phase 2) - Service factory orchestration
3. **DIContainer** (Phase 3) - Refactored to thin facade

The extraction follows a low-risk → medium-risk sequence with backward compatibility guaranteed throughout.

**Timeline**: Phase 1 (May 14-15), Phase 2 (May 15-16), Phase 3 (May 16-17)

---

## Phase 1: Extract PluginResolver (May 14-15)

### Overview

PluginResolver encapsulates all plugin resolution logic:
- 10 plugin factory methods
- 2 private helper methods (`_get_registry()`, `_resolve_platform_key()`)
- Registry lookups, platform-key resolution, optional plugin returns

**Risk Level**: LOW (stateless, no caching, no circular imports)

### Implementation Steps

#### Step 1.1: Create PluginResolver Class

**File**: Create `src/prism/scanner_core/plugin_resolver.py`

```python
"""Plugin resolution layer for DIContainer decomposition."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_plugins.interfaces import (
        CommentDrivenDocumentationPlugin,
        FeatureDetectionPlugin,
        JinjaAnalysisPolicyPlugin,
        VariableDiscoveryPlugin,
        YAMLParsingPolicyPlugin,
    )
    from prism.scanner_data.contracts_request import (
        PreparedTaskAnnotationPolicy,
        PreparedTaskLineParsingPolicy,
        PreparedTaskTraversalPolicy,
        PreparedVariableExtractorPolicy,
    )
    from prism.scanner_plugins.registry import PluginRegistry


class PluginResolver:
    """Resolve plugins from registry or DI wiring (via delegated overrides).
    
    PluginResolver is stateless and delegates mock/override decision-making
    back to DIContainer. All plugin factory methods:
    - Check for mocks in DIContainer._mocks first
    - Check for overrides in DIContainer._factory_overrides second
    - Execute resolver logic (registry lookup, optional returns) third
    
    This pattern keeps orchestration centralized in DIContainer while moving
    the resolver implementation logic into a dedicated class.
    """

    def __init__(self, di: "DIContainer") -> None:
        """Initialize resolver with reference to container.
        
        Args:
            di: DIContainer reference for accessing mocks, overrides, registry, platform_key
        """
        self._di = di

    def _get_registry(self) -> "PluginRegistry":
        """Return the injected plugin registry or raise."""
        if self._di.plugin_registry is None:
            raise ValueError("No plugin registry provided to DIContainer")
        return self._di.plugin_registry

    def _resolve_platform_key(self) -> str:
        """Return pre-resolved platform key or delegate to module-level resolver."""
        from prism.scanner_core.di import resolve_platform_key
        
        if self._di.platform_key is not None:
            return self._di.platform_key
        return resolve_platform_key(self._di.scan_options, self._di.plugin_registry)

    def factory_variable_discovery_plugin(self) -> "VariableDiscoveryPlugin":
        """Resolve variable-discovery plugin via registry; fail-closed if unregistered.
        
        Mock and override checks happen in DIContainer; this method executes
        resolver logic only.
        """
        from prism.scanner_core.di import _construct_runtime_plugin
        
        platform_key = self._resolve_platform_key()
        registry = self._get_registry()
        plugin_cls = registry.get_variable_discovery_plugin(platform_key)
        if plugin_cls is None:
            raise ValueError(
                f"No variable_discovery plugin registered under '{platform_key}'. "
                "Ensure scanner_plugins bootstrap has run."
            )
        return _construct_runtime_plugin(
            plugin_cls,
            plugin_kind="variable_discovery",
            platform_key=platform_key,
            di=self._di,
        )

    def factory_feature_detection_plugin(self) -> "FeatureDetectionPlugin":
        """Resolve feature-detection plugin via registry; fail-closed if unregistered.
        
        Mock and override checks happen in DIContainer; this method executes
        resolver logic only.
        """
        from prism.scanner_core.di import _construct_runtime_plugin
        
        platform_key = self._resolve_platform_key()
        registry = self._get_registry()
        plugin_cls = registry.get_feature_detection_plugin(platform_key)
        if plugin_cls is None:
            raise ValueError(
                f"No feature_detection plugin registered under '{platform_key}'. "
                "Ensure scanner_plugins bootstrap has run."
            )
        return _construct_runtime_plugin(
            plugin_cls,
            plugin_kind="feature_detection",
            platform_key=platform_key,
            di=self._di,
        )

    def factory_comment_driven_doc_plugin(
        self,
    ) -> "CommentDrivenDocumentationPlugin | None":
        """Resolve optional comment-driven documentation plugin from DI wiring.
        
        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_task_annotation_policy_plugin(
        self,
    ) -> "PreparedTaskAnnotationPolicy | None":
        """Resolve optional task-annotation policy plugin from DI wiring.
        
        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_task_line_parsing_policy_plugin(
        self,
    ) -> "PreparedTaskLineParsingPolicy | None":
        """Resolve optional task-line parsing policy plugin from DI wiring.
        
        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_task_traversal_policy_plugin(
        self,
    ) -> "PreparedTaskTraversalPolicy | None":
        """Resolve optional task-traversal policy plugin from DI wiring.
        
        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_variable_extractor_policy_plugin(
        self,
    ) -> "PreparedVariableExtractorPolicy | None":
        """Resolve optional variable-extractor policy plugin from DI wiring.
        
        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_yaml_parsing_policy_plugin(self) -> "YAMLParsingPolicyPlugin | None":
        """Resolve optional YAML parsing policy plugin from DI wiring.
        
        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_jinja_analysis_policy_plugin(self) -> "JinjaAnalysisPolicyPlugin | None":
        """Resolve optional Jinja analysis policy plugin from DI wiring.
        
        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_audit_plugin(self) -> "VariableDiscoveryPlugin | None":
        """Return the injected audit plugin, or None if audit is not configured (opt-in).
        
        Mock and override checks happen in DIContainer.
        """
        return None
```

**What This Achieves**:
- PluginResolver is created as a separate class
- All 10 plugin factory methods are moved (with delegation stubs for optional ones)
- Helper methods `_get_registry()` and `_resolve_platform_key()` are extracted
- Stubs for optional plugin factories return None (mock/override logic stays in DIContainer)

#### Step 1.2: Add PluginResolver Instantiation to DIContainer.__init__()

**File**: `src/prism/scanner_core/di.py`

Add after `self._event_bus = EventBus(...)`:

```python
self._plugin_resolver: PluginResolver | None = None  # Lazy-initialized
```

#### Step 1.3: Update DIContainer Factory Methods to Delegate to PluginResolver

For each of 10 plugin factory methods in DIContainer, update to:

**Template**:
```python
def factory_<plugin_type>_plugin(self) -> <ReturnType>:
    """Resolve <plugin_type> plugin via registry."""
    # Mock check
    if "<plugin_type>_plugin" in self._mocks:
        return self._mocks["<plugin_type>_plugin"]

    # Override check
    override_result = self._call_factory_override("<plugin_type>_plugin_factory")
    if override_result is not None:
        return cast(<ReturnType>, override_result)

    # Delegate to resolver
    if self._plugin_resolver is None:
        from prism.scanner_core.plugin_resolver import PluginResolver
        self._plugin_resolver = PluginResolver(self)
    return self._plugin_resolver.factory_<plugin_type>_plugin()
```

**Example for variable_discovery_plugin**:
```python
def factory_variable_discovery_plugin(self) -> VariableDiscoveryPlugin:
    """Resolve variable-discovery plugin via registry; fail-closed if unregistered."""
    if "variable_discovery_plugin" in self._mocks:
        return self._mocks["variable_discovery_plugin"]

    override_result = self._call_factory_override("variable_discovery_plugin_factory")
    if override_result is not None:
        return cast("VariableDiscoveryPlugin", override_result)

    if self._plugin_resolver is None:
        from prism.scanner_core.plugin_resolver import PluginResolver
        self._plugin_resolver = PluginResolver(self)
    return self._plugin_resolver.factory_variable_discovery_plugin()
```

Apply this pattern to all 10 plugin factory methods:
- `factory_variable_discovery_plugin()`
- `factory_feature_detection_plugin()`
- `factory_comment_driven_doc_plugin()`
- `factory_task_annotation_policy_plugin()`
- `factory_task_line_parsing_policy_plugin()`
- `factory_task_traversal_policy_plugin()`
- `factory_variable_extractor_policy_plugin()`
- `factory_yaml_parsing_policy_plugin()`
- `factory_jinja_analysis_policy_plugin()`
- `factory_audit_plugin()`

#### Step 1.4: Remove Plugin Helper Methods from DIContainer

Delete from DIContainer:
- `_get_registry()` (now in PluginResolver)
- `_resolve_platform_key()` (now in PluginResolver)

#### Step 1.5: Testing Strategy for Phase 1

**Unit Tests**: Create `tests/test_plugin_resolver.py`
- Test each plugin factory method independently
- Test mock injection (mocks checked by DIContainer, then delegated)
- Test override injection
- Test registry lookup failure handling
- Test optional plugin returns (None)

**Integration Tests**: Extend `tests/test_di_container.py`
- Verify plugin factory methods still work through DIContainer
- Verify mock injection still works (DIContainer checks first)
- Verify override injection still works
- Verify backward compatibility (no API changes)

**Validation**:
```bash
pytest tests/test_plugin_resolver.py -v
pytest tests/test_di_container.py::test_factory_variable_discovery_plugin -v
pytest tests/test_di_container.py::test_factory_feature_detection_plugin -v
# ... etc for all plugin factories
```

---

## Phase 2: Extract ServiceLocator (May 15-16)

### Overview

ServiceLocator encapsulates service factory methods:
- 6 service factory methods
- Caching and override support
- Deferred import handling for circular dependency breaking

**Risk Level**: MEDIUM (caching coordination, deferred imports, mock/override)

### Implementation Steps

#### Step 2.1: Create ServiceLocator Class

**File**: Create `src/prism/scanner_core/service_locator.py`

```python
"""Service factory layer for DIContainer decomposition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_core.variable_discovery import VariableDiscovery
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_data.builders import VariableRowBuilder
    from prism.scanner_core.protocols_runtime import BlockerFactBuilder


class ServiceLocator:
    """Service factory orchestration for scanner components.
    
    ServiceLocator creates or caches service instances like EventBus, ScannerContext,
    VariableDiscovery, and FeatureDetector. It delegates mock and override checks
    to DIContainer, then executes the factory logic.
    
    All cached values are protected by DIContainer._cache_lock for thread safety.
    """

    def __init__(self, di: "DIContainer") -> None:
        """Initialize service locator with reference to container.
        
        Args:
            di: DIContainer reference for accessing mocks, overrides, caching
        """
        self._di = di

    def factory_event_bus(self) -> Any:
        """Return the per-container EventBus.
        
        EventBus is created once in DIContainer.__init__() and stored there.
        This method is kept for API consistency but simply delegates.
        """
        return self._di._event_bus

    def factory_scanner_context(self) -> "ScannerContext":
        """Create ScannerContext only when runtime seam wiring is provided.
        
        ScannerContext is constructed fresh each time (no caching).
        Mock and override checks happen in DIContainer.
        """
        scanner_context_cls = self._di.scanner_context_wiring.get("scanner_context_cls")
        prepare_scan_context_fn = self._di.scanner_context_wiring.get(
            "prepare_scan_context_fn"
        )
        if scanner_context_cls is None or prepare_scan_context_fn is None:
            raise RuntimeError(
                "factory_scanner_context is disabled: scanner_context_wiring is "
                "not configured. ScannerContext requires prepare_scan_context_fn "
                "runtime seam injection."
            )

        scanner_context_kwargs: dict[str, Any] = {
            "di": self._di,
            "role_path": self._di._role_path,
            "scan_options": self._di._snapshot_scan_options(),
            "prepare_scan_context_fn": prepare_scan_context_fn,
        }

        scanner_context_factory = cast(
            "Callable[..., ScannerContext]",
            scanner_context_cls,
        )
        return scanner_context_factory(**scanner_context_kwargs)

    def factory_variable_discovery(self) -> "VariableDiscovery":
        """Create or return cached VariableDiscovery.
        
        Note: Import is deferred to break circular dependency.
        VariableDiscovery may import from scanner_extract which imports di_helpers.
        
        Caching is coordinated by DIContainer._cache_lock.
        Mock and override checks happen in DIContainer.
        """
        from prism.scanner_core.di import _create_variable_discovery
        
        key = "variable_discovery"
        with self._di._cache_lock:
            if key not in self._di._cache:
                self._di._cache[key] = _create_variable_discovery(
                    self._di,
                    self._di._role_path,
                    self._di._snapshot_scan_options(),
                )
        return self._di._cache[key]

    def factory_feature_detector(self) -> "FeatureDetector":
        """Create or return cached FeatureDetector.
        
        Note: Import is deferred to break circular dependency.
        FeatureDetector imports collect_task_handler_catalog from scanner_extract.
        
        Caching is coordinated by DIContainer._cache_lock.
        Mock and override checks happen in DIContainer.
        """
        from prism.scanner_core.di import _create_feature_detector
        
        key = "feature_detector"
        with self._di._cache_lock:
            if key not in self._di._cache:
                self._di._cache[key] = _create_feature_detector(
                    self._di,
                    self._di._role_path,
                    self._di._snapshot_scan_options(),
                )
        return self._di._cache[key]

    def factory_variable_row_builder(self) -> "VariableRowBuilder":
        """Create cached VariableRowBuilder for row construction helpers.
        
        VariableRowBuilder is a lightweight stateless builder, cached for reuse.
        Mock and override checks happen in DIContainer.
        """
        from prism.scanner_data.builders import VariableRowBuilder
        
        key = "variable_row_builder"
        with self._di._cache_lock:
            if key not in self._di._cache:
                self._di._cache[key] = VariableRowBuilder()
        return self._di._cache[key]

    def factory_blocker_fact_builder(self) -> "BlockerFactBuilder":
        """Return the blocker-fact builder callable (plugin-layer owned).
        
        Caching is coordinated by DIContainer._cache_lock.
        Mock and override checks happen in DIContainer.
        """
        key = "blocker_fact_builder"
        with self._di._cache_lock:
            if key not in self._di._cache:
                if self._di._blocker_fact_builder_fn is not None:
                    fn = self._di._blocker_fact_builder_fn
                else:
                    from prism.scanner_plugins.defaults import (
                        resolve_blocker_fact_builder,
                    )

                    fn = resolve_blocker_fact_builder()
                self._di._cache[key] = fn
        return self._di._cache[key]
```

**What This Achieves**:
- ServiceLocator is created as a separate class
- All 6 service factory methods are moved
- Caching is preserved and protected by DIContainer._cache_lock
- Deferred imports are preserved exactly
- Delegation back to DIContainer properties/cache via `self._di`

#### Step 2.2: Add ServiceLocator Instantiation to DIContainer.__init__()

**File**: `src/prism/scanner_core/di.py`

Add after plugin resolver initialization:

```python
self._service_locator: ServiceLocator | None = None  # Lazy-initialized
```

#### Step 2.3: Update DIContainer Service Factory Methods to Delegate

For each of 6 service factory methods, update to:

**Template**:
```python
def factory_<service_type>(self) -> <ReturnType>:
    """Create or return <service_type>."""
    # Mock check (if applicable)
    if "<service_type>" in self._mocks:
        return self._mocks["<service_type>"]

    # Override check
    override_result = self._call_factory_override("<service_type>_factory")
    if override_result is not None:
        return cast(<ReturnType>, override_result)

    # Delegate to locator
    if self._service_locator is None:
        from prism.scanner_core.service_locator import ServiceLocator
        self._service_locator = ServiceLocator(self)
    return self._service_locator.factory_<service_type>()
```

**Example for variable_discovery**:
```python
def factory_variable_discovery(self) -> "VariableDiscovery":
    """Create or return cached VariableDiscovery."""
    if "variable_discovery" in self._mocks:
        return self._mocks["variable_discovery"]

    override_result = self._call_factory_override("variable_discovery_factory")
    if override_result is not None:
        return cast("VariableDiscovery", override_result)

    if self._service_locator is None:
        from prism.scanner_core.service_locator import ServiceLocator
        self._service_locator = ServiceLocator(self)
    return self._service_locator.factory_variable_discovery()
```

Apply this pattern to all 6 service factory methods:
- `factory_event_bus()`
- `factory_scanner_context()`
- `factory_variable_discovery()`
- `factory_feature_detector()`
- `factory_variable_row_builder()`
- `factory_blocker_fact_builder()`

#### Step 2.4: Testing Strategy for Phase 2

**Unit Tests**: Create `tests/test_service_locator.py`
- Test each service factory method independently
- Test caching behavior (second call returns same instance)
- Test cache invalidation (replace_scan_options clears cache)
- Test deferred import handling (no import errors)
- Test mock injection through DIContainer
- Test override injection through DIContainer

**Integration Tests**: Extend `tests/test_di_container.py`
- Verify service factory methods still work through DIContainer
- Verify mock injection works end-to-end
- Verify override injection works end-to-end
- Verify cache coordination between DIContainer and ServiceLocator
- Verify backward compatibility (no API changes)

**Circular Import Test**: 
```bash
python -c "from prism.scanner_core.di import DIContainer; print('OK')"
python -c "from prism.scanner_core.service_locator import ServiceLocator; print('OK')"
```

**Validation**:
```bash
pytest tests/test_service_locator.py -v
pytest tests/test_di_container.py::test_factory_variable_discovery -v
pytest tests/test_di_container.py::test_factory_feature_detector -v
# ... etc for all service factories
```

---

## Phase 3: Refactor DIContainer to Facade (May 16-17)

### Overview

After Phases 1-2, DIContainer becomes a thin orchestration facade:
- Owns all public factory_*() methods (unchanged API)
- Manages state: scan_options, mocks, overrides, caches
- Coordinates mock/override checks before delegation
- Instantiates ServiceLocator and PluginResolver

**Risk Level**: LOW (API unchanged, pure refactoring)

### Implementation Steps

#### Step 3.1: Clean Up DIContainer

**File**: `src/prism/scanner_core/di.py`

Remove from DIContainer (already moved):
- All 10 plugin factory implementations (now delegate to PluginResolver)
- All 6 service factory implementations (now delegate to ServiceLocator)
- `_get_registry()` (moved to PluginResolver)
- `_resolve_platform_key()` (moved to PluginResolver)

Keep in DIContainer:
- `__init__()` - Initialize both delegates, event bus, mocks, cache, overrides
- All properties: `scan_options`, `plugin_registry`, `scanner_context_wiring`, `factory_overrides`, `platform_key`, `inherit_default_event_listeners`
- State management: `replace_scan_options()`, `_snapshot_scan_options()`, `_invalidate_scan_option_dependent_cache_locked()`
- Mock management: `inject_mock()`, `clear_mocks()`
- Cache management: `clear_cache()`
- Override orchestration: `_call_factory_override()`
- All public factory_*() methods (with delegation)

#### Step 3.2: Add Import Statements

**File**: `src/prism/scanner_core/di.py`

Add at top:

```python
from prism.scanner_core.service_locator import ServiceLocator
from prism.scanner_core.plugin_resolver import PluginResolver
```

Or use lazy imports in __init__() to avoid circular dependencies.

#### Step 3.3: Verify No Breaking Changes

**Backward Compatibility Checklist**:
- [ ] All public factory_*() methods still exist on DIContainer
- [ ] All public factory_*() methods have same signatures
- [ ] All public factory_*() methods return same types
- [ ] All properties still accessible
- [ ] inject_mock() still works
- [ ] clear_mocks() still works
- [ ] clear_cache() still works
- [ ] replace_scan_options() still works
- [ ] Caching behavior unchanged
- [ ] Mock injection behavior unchanged
- [ ] Override injection behavior unchanged

#### Step 3.4: Testing Strategy for Phase 3

**Unit Tests**: Create or extend `tests/test_di_container_facade.py`
- Verify all public factory methods exist
- Verify all public properties exist
- Verify delegation works end-to-end
- Verify mock injection end-to-end
- Verify override injection end-to-end

**Integration Tests**: Run full test suite
```bash
pytest tests/test_di_container.py -v
pytest tests/test_plugin_resolver.py -v
pytest tests/test_service_locator.py -v
pytest tests/ -k "di or factory" -v
```

**Backward Compatibility Tests**: Create `tests/test_di_backward_compatibility.py`
- Instantiate DIContainer with various configurations
- Call each factory method
- Verify mocks still work
- Verify overrides still work
- Verify caching still works
- Verify no breaking changes

**Performance Sanity Check**:
- DIContainer instantiation time unchanged
- Factory method call time unchanged (lazy delegate instantiation adds minimal overhead)
- Caching behavior unchanged

#### Step 3.5: Code Coverage Targets

After all phases complete:
- PluginResolver: 100% coverage (10 factories + 2 helpers)
- ServiceLocator: 100% coverage (6 factories)
- DIContainer: 100% coverage (facade methods, state management, override orchestration)

**Validation**:
```bash
pytest tests/test_di_container.py tests/test_plugin_resolver.py tests/test_service_locator.py --cov=prism.scanner_core.di --cov=prism.scanner_core.plugin_resolver --cov=prism.scanner_core.service_locator --cov-report=term-missing
```

---

## Backward Compatibility Strategy

### Public API Guarantee

**Unchanged**:
- All `factory_*()` method names
- All `factory_*()` return types
- All property names and types
- `inject_mock()`, `clear_mocks()`, `clear_cache()`, `replace_scan_options()` signatures

**Implementation Details** (internal only):
- Methods now delegate to ServiceLocator/PluginResolver
- Instance variables `_service_locator`, `_plugin_resolver` are internal
- Mock checking still happens in DIContainer before delegation

### No Breaking Changes

1. **Existing code using DIContainer**:
   ```python
   di = DIContainer(...)
   plugin = di.factory_variable_discovery_plugin()  # Still works, same API
   service = di.factory_variable_discovery()         # Still works, same API
   di.inject_mock("variable_discovery", mock_obj)   # Still works
   ```

2. **Test code using mocks**:
   ```python
   di.inject_mock("variable_discovery_plugin", mock_plugin)
   assert di.factory_variable_discovery_plugin() is mock_plugin  # Still works
   ```

3. **Override injection**:
   ```python
   di = DIContainer(..., factory_overrides={"variable_discovery_factory": my_override})
   result = di.factory_variable_discovery()  # Override called before delegation
   ```

### Migration Path for New Code

New code written after Phase 3 can:
- Use `DIContainer` as before (recommended for backward compatibility)
- Optionally use `ServiceLocator` and `PluginResolver` directly if needed (advanced use)

---

## Testing Approach by Phase

### Phase 1 Testing (PluginResolver)

| Test Type | Coverage | Example |
| --- | --- | --- |
| Unit | PluginResolver class in isolation | `test_plugin_resolver_variable_discovery_plugin()` |
| Integration | PluginResolver + DIContainer delegation | `test_di_factory_variable_discovery_plugin_delegates()` |
| Backward Compat | DIContainer API unchanged | `test_factory_variable_discovery_plugin_signature_unchanged()` |
| Mock Injection | Mocks work through DIContainer | `test_inject_mock_plugin_works()` |
| Override Injection | Overrides work through DIContainer | `test_override_plugin_factory_works()` |

### Phase 2 Testing (ServiceLocator)

| Test Type | Coverage | Example |
| --- | --- | --- |
| Unit | ServiceLocator class in isolation | `test_service_locator_variable_discovery_caching()` |
| Integration | ServiceLocator + DIContainer delegation | `test_di_factory_variable_discovery_delegates()` |
| Backward Compat | DIContainer API unchanged | `test_factory_variable_discovery_signature_unchanged()` |
| Cache Coordination | replace_scan_options clears cache | `test_replace_scan_options_clears_service_cache()` |
| Deferred Imports | No circular import errors | `test_deferred_import_no_circular_dep()` |
| Mock Injection | Mocks work through DIContainer | `test_inject_mock_service_works()` |
| Thread Safety | Cache coordination under lock | `test_service_locator_thread_safe_caching()` |

### Phase 3 Testing (Facade)

| Test Type | Coverage | Example |
| --- | --- | --- |
| Full Integration | All factories through DIContainer | `pytest tests/test_di_container.py -v` |
| End-to-End | Mocks, overrides, caching | `test_di_full_lifecycle()` |
| Backward Compat | No breaking changes | `test_di_api_backward_compatible()` |
| Performance | No perf regression | `test_di_instantiation_time_acceptable()` |

---

## Extraction Completion Criteria

### Overall Success Criteria

- [ ] All tests pass: `pytest tests/ -v --tb=short`
- [ ] No new lint errors: `ruff check src/prism/scanner_core/`
- [ ] Type checking clean: `mypy src/prism/scanner_core/di.py`
- [ ] No circular import errors: `python -c "from prism.scanner_core.di import DIContainer"`
- [ ] Backward compatibility verified: old code works unchanged
- [ ] Performance acceptable: no measurable regression
- [ ] Code coverage ≥95% across all three classes

### Phase 1 Success

- [ ] PluginResolver class created and tested
- [ ] All 10 plugin factories delegate correctly
- [ ] Mock injection works for all plugin factories
- [ ] Override injection works for all plugin factories
- [ ] Tests pass: `pytest tests/test_plugin_resolver.py -v`
- [ ] No regressions in DIContainer tests

### Phase 2 Success

- [ ] ServiceLocator class created and tested
- [ ] All 6 service factories delegate correctly
- [ ] Mock injection works for all service factories
- [ ] Caching preserved and coordinated
- [ ] Deferred imports work (no circular deps)
- [ ] Cache invalidation works on replace_scan_options()
- [ ] Tests pass: `pytest tests/test_service_locator.py -v`
- [ ] No regressions in DIContainer tests

### Phase 3 Success

- [ ] DIContainer facade refactoring complete
- [ ] All public methods delegate correctly
- [ ] No breaking API changes
- [ ] Full backward compatibility
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code coverage ≥95%
- [ ] Ready for builder implementation

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Circular imports | MEDIUM | HIGH | Deferred imports in factory methods, TYPE_CHECKING for types |
| Cache coordination failures | LOW | MEDIUM | All caching protected by DIContainer._cache_lock, tests verify invalidation |
| Mock injection breaks | LOW | HIGH | Mock checks in DIContainer before delegation, comprehensive tests |
| Override injection breaks | LOW | HIGH | Override checks in DIContainer before delegation, comprehensive tests |
| API breaking change | LOW | CRITICAL | Comprehensive backward compat tests, no signatures changed |
| Performance regression | LOW | MEDIUM | Lazy delegate instantiation minimal overhead, perf tests included |

---

## Rollback Plan

If critical issues occur:

1. **Phase 1 Rollback**: Delete plugin_resolver.py, revert DIContainer changes to keep plugin methods in place
2. **Phase 2 Rollback**: Delete service_locator.py, revert DIContainer changes to keep service methods in place
3. **Phase 3 Rollback**: Revert DIContainer to single class, keep both delegates disabled

**Time to Rollback**: <15 minutes per phase (all changes isolated)

---

## Summary

- **Phase 1 (May 14-15)**: Extract PluginResolver (low risk, no caching)
- **Phase 2 (May 15-16)**: Extract ServiceLocator (medium risk, caching + deferred imports)
- **Phase 3 (May 16-17)**: Refactor DIContainer to facade (low risk, pure refactoring)
- **Backward Compatibility**: 100% guaranteed throughout
- **Testing**: Comprehensive unit, integration, and backward compat tests at each phase
- **Success Criteria**: All tests pass, no breaking changes, code coverage ≥95%
