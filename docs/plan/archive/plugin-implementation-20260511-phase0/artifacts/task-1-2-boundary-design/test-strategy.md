# DIContainer Decomposition: Test Strategy

## Overview

This document defines the comprehensive testing approach to validate the DIContainer extraction across all three phases:
1. **Phase 1**: Extract PluginResolver (unit tests + integration)
2. **Phase 2**: Extract ServiceLocator (unit tests + integration + cache coordination)
3. **Phase 3**: Refactor DIContainer to facade (full integration + backward compat)

All tests ensure backward compatibility and maintain 100% code coverage across all three classes.

---

## Test Categories by Phase

### Phase 1: PluginResolver Tests

| Test Type | Coverage | Count | Success Criteria |
| --- | --- | --- | --- |
| Unit | PluginResolver class in isolation | 15+ | All tests pass, ≥90% coverage |
| Integration | PluginResolver + DIContainer delegation | 10+ | Delegation works, mocks/overrides transparent |
| Backward Compat | DIContainer API unchanged | 5+ | All factory methods callable, same signatures |

#### Phase 1 Unit Tests: `tests/test_plugin_resolver.py`

```python
# Test registry-driven plugin resolution
def test_factory_variable_discovery_plugin_resolves_via_registry():
    """Test that variable_discovery_plugin resolves from registry."""
    di = DIContainer(
        role_path="test",
        scan_options={...},
        registry=mock_registry,
        platform_key="ansible",
    )
    plugin = di._plugin_resolver.factory_variable_discovery_plugin()
    assert plugin is not None
    assert isinstance(plugin, VariableDiscoveryPlugin)

def test_factory_feature_detection_plugin_resolves_via_registry():
    """Test that feature_detection_plugin resolves from registry."""
    # Similar structure

def test_factory_variable_discovery_plugin_raises_on_missing_registry():
    """Test that resolution fails if registry is None."""
    di = DIContainer(..., registry=None)
    with pytest.raises(ValueError, match="No plugin registry"):
        di._plugin_resolver.factory_variable_discovery_plugin()

def test_factory_variable_discovery_plugin_raises_on_unregistered():
    """Test that resolution fails if plugin not registered for platform_key."""
    registry = MockRegistry()  # No plugins registered
    di = DIContainer(..., registry=registry, platform_key="ansible")
    with pytest.raises(ValueError, match="No variable_discovery plugin"):
        di._plugin_resolver.factory_variable_discovery_plugin()

def test_resolve_platform_key_priority_explicit():
    """Test platform key resolution priority: explicit > policy > platform > registry default."""
    scan_options = {"scan_pipeline_plugin": "kubernetes"}
    key = di._plugin_resolver._resolve_platform_key()
    assert key == "kubernetes"

def test_resolve_platform_key_priority_policy():
    """Test platform key resolution: policy_context selection."""
    scan_options = {
        "policy_context": {"selection": {"plugin": "terraform"}},
    }
    key = di._plugin_resolver._resolve_platform_key()
    assert key == "terraform"

def test_resolve_platform_key_priority_platform():
    """Test platform key resolution: platform fallback."""
    scan_options = {"platform": "docker"}
    key = di._plugin_resolver._resolve_platform_key()
    assert key == "docker"

def test_resolve_platform_key_priority_registry_default():
    """Test platform key resolution: registry default fallback."""
    registry = MockRegistry(default_platform="aws")
    di = DIContainer(..., registry=registry, scan_options={})
    key = di._plugin_resolver._resolve_platform_key()
    assert key == "aws"

def test_factory_comment_driven_doc_plugin_returns_none():
    """Test that optional plugin factory returns None."""
    di = DIContainer(...)
    result = di._plugin_resolver.factory_comment_driven_doc_plugin()
    assert result is None

def test_factory_task_annotation_policy_plugin_returns_none():
    """Test that optional plugin factory returns None."""
    # Similar

def test_factory_*_policy_plugin_returns_none():
    """Test all optional plugin factories return None."""
    # Similar for 8 policy/optional plugins

def test_factory_audit_plugin_returns_none():
    """Test that audit plugin returns None."""
    di = DIContainer(...)
    result = di._plugin_resolver.factory_audit_plugin()
    assert result is None

def test_get_registry_returns_registry_if_present():
    """Test _get_registry returns registry."""
    registry = MockRegistry()
    di = DIContainer(..., registry=registry)
    assert di._plugin_resolver._get_registry() is registry

def test_get_registry_raises_if_none():
    """Test _get_registry raises if registry is None."""
    di = DIContainer(..., registry=None)
    with pytest.raises(ValueError, match="No plugin registry"):
        di._plugin_resolver._get_registry()
```

**Total Phase 1 Unit Tests**: ~15 tests, 100% coverage of PluginResolver

#### Phase 1 Integration Tests: Extend `tests/test_di_container.py`

```python
def test_di_factory_variable_discovery_plugin_delegates():
    """Test that DIContainer.factory_variable_discovery_plugin() delegates to resolver."""
    registry = MockRegistry(ansible_vd_plugin=MockPlugin)
    di = DIContainer(..., registry=registry, platform_key="ansible")
    plugin = di.factory_variable_discovery_plugin()
    assert plugin is not None
    # Verify it went through the resolver

def test_di_factory_feature_detection_plugin_delegates():
    """Test that DIContainer.factory_feature_detection_plugin() delegates."""
    # Similar

def test_di_inject_mock_plugin_works():
    """Test that inject_mock works for plugin factories."""
    mock_plugin = MockVariableDiscoveryPlugin()
    di = DIContainer(...)
    di.inject_mock("variable_discovery_plugin", mock_plugin)
    assert di.factory_variable_discovery_plugin() is mock_plugin

def test_di_factory_overrides_plugin_works():
    """Test that factory_overrides work for plugin factories."""
    def override_fn(di, role_path, scan_options):
        return MockVariableDiscoveryPlugin()
    
    di = DIContainer(
        ...,
        factory_overrides={"variable_discovery_plugin_factory": override_fn},
    )
    plugin = di.factory_variable_discovery_plugin()
    assert isinstance(plugin, MockVariableDiscoveryPlugin)

def test_di_plugin_mock_takes_priority_over_override():
    """Test that inject_mock is checked before overrides."""
    mock_plugin = MockVariableDiscoveryPlugin()
    def override_fn(di, role_path, scan_options):
        return OtherMockPlugin()
    
    di = DIContainer(
        ...,
        factory_overrides={"variable_discovery_plugin_factory": override_fn},
    )
    di.inject_mock("variable_discovery_plugin", mock_plugin)
    # Mock should be returned, not override
    assert di.factory_variable_discovery_plugin() is mock_plugin
```

**Total Phase 1 Integration Tests**: ~10 tests

#### Phase 1 Backward Compatibility Tests

```python
def test_factory_variable_discovery_plugin_signature_unchanged():
    """Test that factory method signature is unchanged."""
    di = DIContainer(...)
    # Should have no required positional args
    inspect.signature(di.factory_variable_discovery_plugin)
    # Verify it's callable with no args

def test_factory_plugin_return_types_unchanged():
    """Test that return types are correct."""
    di = DIContainer(..., registry=..., platform_key="ansible")
    result = di.factory_variable_discovery_plugin()
    assert isinstance(result, VariableDiscoveryPlugin)

def test_factory_optional_plugin_return_none():
    """Test that optional plugins return None as before."""
    di = DIContainer(...)
    result = di.factory_comment_driven_doc_plugin()
    assert result is None
```

---

### Phase 2: ServiceLocator Tests

| Test Type | Coverage | Count | Success Criteria |
| --- | --- | --- | --- |
| Unit | ServiceLocator class in isolation | 20+ | All tests pass, ≥95% coverage |
| Cache Coordination | Cache + invalidation + thread safety | 10+ | Cache cleared on replace_scan_options() |
| Deferred Imports | No circular import errors | 5+ | All imports work, no deadlocks |
| Integration | ServiceLocator + DIContainer + mocks/overrides | 15+ | All combinations work |
| Backward Compat | DIContainer API unchanged | 5+ | All factory methods callable, same signatures |

#### Phase 2 Unit Tests: `tests/test_service_locator.py`

```python
# Test EventBus factory
def test_factory_event_bus_returns_event_bus():
    """Test that EventBus factory returns the container's event bus."""
    di = DIContainer(...)
    locator = ServiceLocator(di)
    bus = locator.factory_event_bus()
    assert bus is di._event_bus

# Test ScannerContext factory
def test_factory_scanner_context_creates_fresh_instance():
    """Test that ScannerContext factory creates fresh instance each time."""
    di = DIContainer(..., scanner_context_wiring={...})
    locator = ServiceLocator(di)
    ctx1 = locator.factory_scanner_context()
    ctx2 = locator.factory_scanner_context()
    assert ctx1 is not ctx2

def test_factory_scanner_context_raises_if_wiring_missing():
    """Test that ScannerContext factory raises if wiring not configured."""
    di = DIContainer(..., scanner_context_wiring=None)
    locator = ServiceLocator(di)
    with pytest.raises(RuntimeError, match="scanner_context_wiring"):
        locator.factory_scanner_context()

def test_factory_scanner_context_passes_scan_options():
    """Test that ScannerContext receives scan_options in constructor."""
    scan_options = {"platform": "ansible", ...}
    di = DIContainer(..., scan_options=scan_options, scanner_context_wiring={...})
    locator = ServiceLocator(di)
    ctx = locator.factory_scanner_context()
    # Verify scan_options were passed to ScannerContext

# Test VariableDiscovery factory (cached)
def test_factory_variable_discovery_caches():
    """Test that VariableDiscovery is cached after first call."""
    di = DIContainer(...)
    locator = ServiceLocator(di)
    vd1 = locator.factory_variable_discovery()
    vd2 = locator.factory_variable_discovery()
    assert vd1 is vd2  # Same cached instance

def test_factory_variable_discovery_deferred_import_works():
    """Test that deferred import doesn't cause circular import."""
    # Import order shouldn't cause errors
    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.service_locator import ServiceLocator
    # Verify no import errors

# Test FeatureDetector factory (cached)
def test_factory_feature_detector_caches():
    """Test that FeatureDetector is cached after first call."""
    di = DIContainer(...)
    locator = ServiceLocator(di)
    fd1 = locator.factory_feature_detector()
    fd2 = locator.factory_feature_detector()
    assert fd1 is fd2  # Same cached instance

def test_factory_feature_detector_deferred_import_works():
    """Test that deferred import doesn't cause circular import."""
    # Similar to variable_discovery

# Test VariableRowBuilder factory (cached)
def test_factory_variable_row_builder_caches():
    """Test that VariableRowBuilder is cached."""
    di = DIContainer(...)
    locator = ServiceLocator(di)
    vrb1 = locator.factory_variable_row_builder()
    vrb2 = locator.factory_variable_row_builder()
    assert vrb1 is vrb2  # Same cached instance

# Test BlockerFactBuilder factory (cached)
def test_factory_blocker_fact_builder_returns_callable():
    """Test that BlockerFactBuilder factory returns callable."""
    di = DIContainer(...)
    locator = ServiceLocator(di)
    fn = locator.factory_blocker_fact_builder()
    assert callable(fn)

def test_factory_blocker_fact_builder_caches():
    """Test that BlockerFactBuilder is cached."""
    di = DIContainer(...)
    locator = ServiceLocator(di)
    fn1 = locator.factory_blocker_fact_builder()
    fn2 = locator.factory_blocker_fact_builder()
    assert fn1 is fn2  # Same cached instance

def test_factory_blocker_fact_builder_uses_injected_fn():
    """Test that injected blocker_fact_builder_fn is used."""
    injected_fn = lambda: "blocker"
    di = DIContainer(..., blocker_fact_builder_fn=injected_fn)
    locator = ServiceLocator(di)
    fn = locator.factory_blocker_fact_builder()
    assert fn is injected_fn

def test_factory_blocker_fact_builder_falls_back_to_plugin_layer():
    """Test that default resolve_blocker_fact_builder() is used if not injected."""
    di = DIContainer(..., blocker_fact_builder_fn=None)
    locator = ServiceLocator(di)
    fn = locator.factory_blocker_fact_builder()
    assert callable(fn)
```

**Total Phase 2 Unit Tests**: ~20 tests, ≥95% coverage of ServiceLocator

#### Phase 2 Cache Coordination Tests

```python
def test_replace_scan_options_clears_variable_discovery_cache():
    """Test that replace_scan_options clears variable_discovery cache."""
    di = DIContainer(..., scan_options={"platform": "ansible"})
    vd1 = di.factory_variable_discovery()
    
    # Replace scan_options
    di.replace_scan_options({"platform": "kubernetes"})
    
    # Next call should create new instance
    vd2 = di.factory_variable_discovery()
    assert vd1 is not vd2

def test_replace_scan_options_clears_feature_detector_cache():
    """Test that replace_scan_options clears feature_detector cache."""
    di = DIContainer(..., scan_options={"platform": "ansible"})
    fd1 = di.factory_feature_detector()
    
    di.replace_scan_options({"platform": "kubernetes"})
    fd2 = di.factory_feature_detector()
    assert fd1 is not fd2

def test_replace_scan_options_does_not_clear_other_caches():
    """Test that replace_scan_options only clears scan_options-dependent caches."""
    di = DIContainer(...)
    vrb1 = di.factory_variable_row_builder()
    
    di.replace_scan_options({...})
    vrb2 = di.factory_variable_row_builder()
    
    # VariableRowBuilder should still be cached (not dependent on scan_options)
    assert vrb1 is vrb2

def test_clear_cache_clears_all_caches():
    """Test that clear_cache() clears everything."""
    di = DIContainer(...)
    vd1 = di.factory_variable_discovery()
    fd1 = di.factory_feature_detector()
    vrb1 = di.factory_variable_row_builder()
    
    di.clear_cache()
    
    vd2 = di.factory_variable_discovery()
    fd2 = di.factory_feature_detector()
    vrb2 = di.factory_variable_row_builder()
    
    assert vd1 is not vd2
    assert fd1 is not fd2
    assert vrb1 is not vrb2
```

#### Phase 2 Deferred Import Tests

```python
def test_deferred_import_variable_discovery():
    """Test that VariableDiscovery can be imported after ServiceLocator."""
    # This should not raise circular import error
    from prism.scanner_core.service_locator import ServiceLocator
    from prism.scanner_core.variable_discovery import VariableDiscovery
    
    di = DIContainer(...)
    vd = di.factory_variable_discovery()
    assert isinstance(vd, VariableDiscovery)

def test_deferred_import_feature_detector():
    """Test that FeatureDetector can be imported after ServiceLocator."""
    from prism.scanner_core.service_locator import ServiceLocator
    from prism.scanner_core.feature_detector import FeatureDetector
    
    di = DIContainer(...)
    fd = di.factory_feature_detector()
    assert isinstance(fd, FeatureDetector)

def test_no_circular_import_on_first_call():
    """Test that first factory call doesn't cause circular import."""
    di = DIContainer(...)
    # All these should work without circular import errors
    vd = di.factory_variable_discovery()
    fd = di.factory_feature_detector()
    vrb = di.factory_variable_row_builder()
    bfb = di.factory_blocker_fact_builder()
```

#### Phase 2 Integration Tests: Extend `tests/test_di_container.py`

```python
def test_di_factory_variable_discovery_delegates():
    """Test that DIContainer delegates to ServiceLocator."""
    di = DIContainer(...)
    vd = di.factory_variable_discovery()
    assert vd is not None

def test_di_inject_mock_service_works():
    """Test that inject_mock works for service factories."""
    mock_vd = MockVariableDiscovery()
    di = DIContainer(...)
    di.inject_mock("variable_discovery", mock_vd)
    assert di.factory_variable_discovery() is mock_vd

def test_di_factory_overrides_service_works():
    """Test that factory_overrides work for service factories."""
    def override_fn(di, role_path, scan_options):
        return MockVariableDiscovery()
    
    di = DIContainer(
        ...,
        factory_overrides={"variable_discovery_factory": override_fn},
    )
    vd = di.factory_variable_discovery()
    assert isinstance(vd, MockVariableDiscovery)

def test_di_service_mock_takes_priority_over_override():
    """Test that mock is checked before override."""
    mock_vd = MockVariableDiscovery()
    def override_fn(di, role_path, scan_options):
        return OtherMockVariableDiscovery()
    
    di = DIContainer(
        ...,
        factory_overrides={"variable_discovery_factory": override_fn},
    )
    di.inject_mock("variable_discovery", mock_vd)
    assert di.factory_variable_discovery() is mock_vd
```

#### Phase 2 Thread Safety Tests

```python
def test_factory_variable_discovery_thread_safe():
    """Test that concurrent calls to variable_discovery factory are thread-safe."""
    di = DIContainer(...)
    results = []
    
    def call_factory():
        vd = di.factory_variable_discovery()
        results.append(vd)
    
    threads = [threading.Thread(target=call_factory) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # All should be same cached instance
    assert all(r is results[0] for r in results)

def test_replace_scan_options_with_concurrent_factory_calls():
    """Test that replace_scan_options is coordinated with factory calls."""
    di = DIContainer(..., scan_options={"platform": "ansible"})
    
    vd1 = di.factory_variable_discovery()
    
    def replace_and_call():
        di.replace_scan_options({"platform": "kubernetes"})
        vd2 = di.factory_variable_discovery()
        return vd2
    
    thread = threading.Thread(target=replace_and_call)
    thread.start()
    thread.join()
    
    # Should not raise any threading errors
```

#### Phase 2 Backward Compatibility Tests

```python
def test_factory_variable_discovery_signature_unchanged():
    """Test that factory signature is unchanged."""
    di = DIContainer(...)
    # Should be callable with no args
    vd = di.factory_variable_discovery()
    assert vd is not None

def test_factory_feature_detector_signature_unchanged():
    """Test that factory signature is unchanged."""
    di = DIContainer(...)
    fd = di.factory_feature_detector()
    assert fd is not None

def test_factory_variable_row_builder_signature_unchanged():
    """Test that factory signature is unchanged."""
    di = DIContainer(...)
    vrb = di.factory_variable_row_builder()
    assert vrb is not None

def test_factory_blocker_fact_builder_signature_unchanged():
    """Test that factory signature is unchanged."""
    di = DIContainer(...)
    bfb = di.factory_blocker_fact_builder()
    assert callable(bfb)
```

---

### Phase 3: Full Integration Tests

| Test Type | Coverage | Count | Success Criteria |
| --- | --- | --- | --- |
| Full Integration | All factories + mocks/overrides | 20+ | All combinations work |
| Backward Compat | 100% API compatibility | 10+ | No breaking changes |
| Performance | No regression | 5+ | Instantiation < 10ms |
| End-to-End | Real workloads | 5+ | Behavior unchanged |

#### Phase 3 Full Integration Tests

```python
def test_di_full_lifecycle_plugins_and_services():
    """Test full DIContainer lifecycle with all factory methods."""
    di = DIContainer(
        role_path="test",
        scan_options={"platform": "ansible"},
        registry=mock_registry,
        platform_key="ansible",
        scanner_context_wiring={...},
    )
    
    # All service factories should work
    bus = di.factory_event_bus()
    ctx = di.factory_scanner_context()
    vd = di.factory_variable_discovery()
    fd = di.factory_feature_detector()
    vrb = di.factory_variable_row_builder()
    bfb = di.factory_blocker_fact_builder()
    
    assert all([bus, ctx, vd, fd, vrb, bfb])

def test_di_full_lifecycle_with_mocks():
    """Test DIContainer with all factories mocked."""
    mocks = {
        "event_bus": MockEventBus(),
        "scanner_context": MockScannerContext(),
        "variable_discovery": MockVariableDiscovery(),
        "feature_detector": MockFeatureDetector(),
        "variable_row_builder": MockVariableRowBuilder(),
        "blocker_fact_builder": MockBlockerFactBuilder(),
        "variable_discovery_plugin": MockPlugin(),
        "feature_detection_plugin": MockPlugin(),
    }
    
    di = DIContainer(...)
    for name, mock in mocks.items():
        di.inject_mock(name, mock)
    
    # All factories should return mocks
    assert di.factory_event_bus() is mocks["event_bus"]
    assert di.factory_variable_discovery() is mocks["variable_discovery"]
    # ... etc

def test_di_full_lifecycle_with_overrides():
    """Test DIContainer with factory overrides."""
    overrides = {
        "variable_discovery_factory": lambda di, rp, so: MockVariableDiscovery(),
        "feature_detector_factory": lambda di, rp, so: MockFeatureDetector(),
        "variable_discovery_plugin_factory": lambda di, rp, so: MockPlugin(),
    }
    
    di = DIContainer(..., factory_overrides=overrides)
    
    # All overridden factories should return mock instances
    vd = di.factory_variable_discovery()
    assert isinstance(vd, MockVariableDiscovery)
    # ... etc
```

#### Phase 3 Backward Compatibility Tests: Create `tests/test_di_backward_compatibility.py`

```python
def test_di_api_unchanged_all_methods_exist():
    """Test that all public methods still exist on DIContainer."""
    di = DIContainer(...)
    
    # All service factories should exist
    assert hasattr(di, "factory_event_bus")
    assert hasattr(di, "factory_scanner_context")
    assert hasattr(di, "factory_variable_discovery")
    assert hasattr(di, "factory_feature_detector")
    assert hasattr(di, "factory_variable_row_builder")
    assert hasattr(di, "factory_blocker_fact_builder")
    
    # All plugin factories should exist
    assert hasattr(di, "factory_variable_discovery_plugin")
    assert hasattr(di, "factory_feature_detection_plugin")
    assert hasattr(di, "factory_comment_driven_doc_plugin")
    # ... etc for all plugins
    
    # All properties should exist
    assert hasattr(di, "scan_options")
    assert hasattr(di, "plugin_registry")
    assert hasattr(di, "scanner_context_wiring")
    assert hasattr(di, "factory_overrides")
    assert hasattr(di, "platform_key")
    assert hasattr(di, "inherit_default_event_listeners")
    
    # All management methods should exist
    assert hasattr(di, "inject_mock")
    assert hasattr(di, "clear_mocks")
    assert hasattr(di, "clear_cache")
    assert hasattr(di, "replace_scan_options")

def test_di_api_signatures_unchanged():
    """Test that method signatures haven't changed."""
    di = DIContainer(...)
    
    # factory_event_bus() - no args
    assert len(inspect.signature(di.factory_event_bus).parameters) == 0
    
    # factory_scanner_context() - no args
    assert len(inspect.signature(di.factory_scanner_context).parameters) == 0
    
    # inject_mock(name, mock) - 2 args
    sig = inspect.signature(di.inject_mock)
    assert len(sig.parameters) == 2
    
    # clear_mocks() - no args
    assert len(inspect.signature(di.clear_mocks).parameters) == 0
    
    # clear_cache() - no args
    assert len(inspect.signature(di.clear_cache).parameters) == 0
    
    # replace_scan_options(scan_options) - 1 arg
    assert len(inspect.signature(di.replace_scan_options).parameters) == 1

def test_old_code_pattern_still_works():
    """Test that old code patterns still work without changes."""
    # This is how old code uses DIContainer
    di = DIContainer(
        role_path="scanner_root",
        scan_options={"platform": "ansible"},
    )
    
    # Old pattern: call factory directly
    vd = di.factory_variable_discovery()
    assert vd is not None
    
    # Old pattern: mock injection
    mock_vd = MockVariableDiscovery()
    di.inject_mock("variable_discovery", mock_vd)
    assert di.factory_variable_discovery() is mock_vd
    
    # Old pattern: clear and recreate
    di.clear_mocks()
    di.clear_cache()
    vd2 = di.factory_variable_discovery()
    assert vd2 is not mock_vd
```

#### Phase 3 Performance Tests

```python
def test_di_instantiation_time_acceptable():
    """Test that DIContainer instantiation is fast."""
    import time
    
    start = time.time()
    di = DIContainer(
        role_path="test",
        scan_options={...},
    )
    elapsed = time.time() - start
    
    # Should be < 10ms
    assert elapsed < 0.01, f"DIContainer instantiation took {elapsed*1000:.2f}ms"

def test_di_factory_call_overhead_minimal():
    """Test that factory delegation overhead is minimal."""
    import time
    
    di = DIContainer(...)
    
    # Warm up
    di.factory_variable_discovery()
    
    # Benchmark cache hit
    start = time.time()
    for _ in range(1000):
        di.factory_variable_discovery()
    elapsed = time.time() - start
    
    # Should be < 0.1ms per call on average
    assert elapsed < 0.1, f"1000 factory calls took {elapsed*1000:.2f}ms"

def test_di_mock_injection_overhead_minimal():
    """Test that mock injection has minimal overhead."""
    import time
    
    di = DIContainer(...)
    mock = MockVariableDiscovery()
    
    di.inject_mock("variable_discovery", mock)
    
    start = time.time()
    for _ in range(1000):
        di.factory_variable_discovery()
    elapsed = time.time() - start
    
    # Should be < 0.1ms per call on average (mock check + return)
    assert elapsed < 0.1, f"1000 mock factory calls took {elapsed*1000:.2f}ms"
```

#### Phase 3 End-to-End Tests

```python
def test_di_with_real_scanner_components():
    """Test DIContainer with real scanner components (integration)."""
    # This test uses real instances from prism.scanner_core
    from prism.scanner_core.events import EventBus
    from prism.scanner_core.variable_discovery import VariableDiscovery
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_plugins.registry import PluginRegistry
    
    registry = PluginRegistry()
    registry.bootstrap_builtin_plugins()
    
    di = DIContainer(
        role_path="e2e_test",
        scan_options={...},
        registry=registry,
        platform_key="ansible",
    )
    
    # All factories should work with real components
    bus = di.factory_event_bus()
    vd = di.factory_variable_discovery()
    fd = di.factory_feature_detector()
    
    assert isinstance(bus, EventBus)
    assert isinstance(vd, VariableDiscovery)
    assert isinstance(fd, FeatureDetector)

def test_di_behavior_unchanged_after_decomposition():
    """Test that DIContainer behavior is identical before/after decomposition."""
    # This test verifies that refactoring didn't change behavior
    
    # Create two containers with identical config
    config = {
        "role_path": "test",
        "scan_options": {"platform": "ansible"},
        "registry": mock_registry,
        "platform_key": "ansible",
    }
    
    di1 = DIContainer(**config)
    di2 = DIContainer(**config)
    
    # Both should produce identical results
    vd1 = di1.factory_variable_discovery()
    vd2 = di2.factory_variable_discovery()
    
    # Same type and structure (not same instance since different containers)
    assert type(vd1) == type(vd2)
    assert vd1.role_path == vd2.role_path
```

---

## Test Organization & Execution

### Test File Structure

```
tests/
  test_plugin_resolver.py          # Phase 1 unit tests
  test_service_locator.py          # Phase 2 unit tests
  test_di_container.py             # Extended Phase 1-2 integration tests
  test_di_backward_compatibility.py # Phase 3 backward compat tests
  test_di_performance.py           # Phase 3 performance tests
  test_di_e2e.py                   # Phase 3 end-to-end tests
```

### Running Tests by Phase

**Phase 1 Validation**:
```bash
pytest tests/test_plugin_resolver.py -v
pytest tests/test_di_container.py::test_di_factory_variable_discovery_plugin_delegates -v
# ... all plugin delegation tests
```

**Phase 2 Validation**:
```bash
pytest tests/test_service_locator.py -v
pytest tests/test_di_container.py -k "factory_variable_discovery or factory_feature_detector" -v
# ... all service delegation tests
```

**Phase 3 Validation**:
```bash
pytest tests/test_di_backward_compatibility.py -v
pytest tests/test_di_performance.py -v
pytest tests/test_di_e2e.py -v
```

**Full Test Suite**:
```bash
pytest tests/ -v --tb=short
pytest tests/ --cov=prism.scanner_core.di --cov=prism.scanner_core.plugin_resolver --cov=prism.scanner_core.service_locator --cov-report=term-missing
```

### Success Criteria by Phase

**Phase 1**:
- ✅ `pytest tests/test_plugin_resolver.py -v` passes
- ✅ `pytest tests/test_di_container.py -k plugin -v` passes
- ✅ Coverage ≥90%

**Phase 2**:
- ✅ `pytest tests/test_service_locator.py -v` passes
- ✅ `pytest tests/test_di_container.py -k "variable_discovery or feature_detector" -v` passes
- ✅ Coverage ≥95%
- ✅ Cache coordination tests pass
- ✅ Deferred import tests pass

**Phase 3**:
- ✅ `pytest tests/ -v` passes (all tests)
- ✅ Coverage ≥95% (all 3 classes)
- ✅ Backward compatibility tests pass
- ✅ Performance tests pass
- ✅ End-to-end tests pass

---

## Mock Objects for Testing

### Mock Classes

```python
# tests/conftest.py or tests/fixtures.py

class MockEventBus:
    """Mock EventBus for testing."""
    def publish(self, event):
        pass

class MockScannerContext:
    """Mock ScannerContext for testing."""
    pass

class MockVariableDiscovery:
    """Mock VariableDiscovery for testing."""
    def __init__(self, di=None, role_path=None, scan_options=None):
        self.di = di
        self.role_path = role_path
        self.scan_options = scan_options

class MockFeatureDetector:
    """Mock FeatureDetector for testing."""
    def __init__(self, di=None, role_path=None, scan_options=None):
        self.di = di
        self.role_path = role_path
        self.scan_options = scan_options

class MockVariableRowBuilder:
    """Mock VariableRowBuilder for testing."""
    pass

class MockBlockerFactBuilder:
    """Mock BlockerFactBuilder for testing."""
    pass

class MockPlugin:
    """Mock plugin for testing."""
    def __init__(self, di=None, **kwargs):
        self.di = di

class MockRegistry:
    """Mock PluginRegistry for testing."""
    def __init__(self, default_platform="ansible", **plugins):
        self.default_platform = default_platform
        self.plugins = plugins
    
    def get_default_platform_key(self):
        return self.default_platform
    
    def get_variable_discovery_plugin(self, platform_key):
        return self.plugins.get(f"{platform_key}_vd_plugin")
    
    def get_feature_detection_plugin(self, platform_key):
        return self.plugins.get(f"{platform_key}_fd_plugin")
```

---

## Coverage Targets

### Phase 1: PluginResolver

- PluginResolver class: 100%
- factory_*_plugin methods: 100%
- _get_registry(): 100%
- _resolve_platform_key(): 100%
- DIContainer delegation: 100%

**Target**: ≥90% overall

### Phase 2: ServiceLocator

- ServiceLocator class: 100%
- factory_*() service methods: 100%
- Caching logic: 100%
- DIContainer delegation: 100%
- Cache invalidation: 100%

**Target**: ≥95% overall

### Phase 3: DIContainer

- DIContainer facade methods: 100%
- State management: 100%
- Mock/override orchestration: 100%
- All delegation paths: 100%
- Backward compatibility: 100%

**Target**: ≥95% overall

---

## Regression Testing

### Existing Test Suites

Before decomposition, ensure all existing tests pass:

```bash
pytest tests/test_di_container.py -v
pytest tests/ -k "di or factory or container" -v
```

After decomposition, re-run same suites:

```bash
pytest tests/test_di_container.py -v
pytest tests/test_plugin_resolver.py -v
pytest tests/test_service_locator.py -v
pytest tests/ -k "di or factory or container" -v
```

**No new failures allowed**.

---

## Summary

| Phase | Test Files | Test Count | Coverage | Timeline |
| --- | --- | --- | --- | --- |
| 1 | test_plugin_resolver.py | 25+ | ≥90% | May 14-15 |
| 2 | test_service_locator.py | 50+ | ≥95% | May 15-16 |
| 3 | test_di_*.py (all) | 80+ | ≥95% | May 16-17 |
| **Total** | **6 files** | **155+** | **≥95%** | **May 14-17** |

All tests validate:
- ✅ Functional correctness
- ✅ Mock/override injection
- ✅ Caching coordination
- ✅ Cache invalidation
- ✅ Deferred imports
- ✅ Thread safety
- ✅ Backward compatibility
- ✅ Performance
- ✅ No regressions
