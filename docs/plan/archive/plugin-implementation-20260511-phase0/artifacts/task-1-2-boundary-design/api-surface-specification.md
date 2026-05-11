# DIContainer Decomposition: Public API Surface Specification

## Overview

This document defines the final public API surface for all three classes after extraction:
1. **DIContainer** - Facade coordinating mock/override checks and delegation
2. **PluginResolver** - Plugin resolution via registry or DI wiring
3. **ServiceLocator** - Service factory orchestration

All type signatures, return types, and docstrings are precise to enable exact builder implementation.

---

## 1. DIContainer (Facade & Orchestrator)

### Class Signature

```python
class DIContainer:
    """Lightweight DI container for scanner orchestrators.
    
    DIContainer orchestrates three responsibilities:
    1. State management: scan_options, registry, platform_key, overrides, mocks
    2. Mock/override orchestration: checks mocks first, then overrides, then delegates
    3. Delegation: sends actual factory logic to ServiceLocator and PluginResolver
    
    All factory_*() methods maintain their original signatures and return types.
    Public API is 100% backward compatible.
    """
```

### Public Methods

#### Constructor

```python
def __init__(
    self,
    role_path: str,
    scan_options: ScanOptionsDict,
    *,
    registry: PluginRegistry | None = None,
    platform_key: str | None = None,
    scanner_context_wiring: dict[str, object] | None = None,
    factory_overrides: dict[str, "DIFactoryOverride"] | None = None,
    event_listeners: list[EventListener] | None = None,
    inherit_default_event_listeners: bool = False,
    cache_backend: ScanCacheBackend | None = None,
    blocker_fact_builder_fn: "BlockerFactBuilder | None" = None,
) -> None:
    """Initialize container with role path and scan options.
    
    Args:
        role_path: Identifier for this container instance (e.g., "scanner_root")
        scan_options: ScanOptionsDict with scan configuration
        registry: PluginRegistry for plugin resolution (optional)
        platform_key: Pre-resolved platform key (optional, overrides registry default)
        scanner_context_wiring: Dict with scanner_context_cls and prepare_scan_context_fn (optional)
        factory_overrides: Dict[str, DIFactoryOverride] for factory injection (optional)
        event_listeners: List of EventListener instances (optional)
        inherit_default_event_listeners: If True, capture ambient default listeners (default: False)
        cache_backend: ScanCacheBackend for runtime caching (optional)
        blocker_fact_builder_fn: BlockerFactBuilder callable (optional)
    
    Raises:
        ValueError: If role_path is empty or scan_options is None
    """
```

#### Properties (Read-Only)

```python
@property
def scan_options(self) -> ScanOptionsDict:
    """Return thread-safe snapshot of scan options.
    
    Returns:
        ScanOptionsDict: Cloned copy of current scan options
    """

@property
def plugin_registry(self) -> PluginRegistry | None:
    """Return the injected plugin registry.
    
    Returns:
        PluginRegistry | None: Registry if provided, else None
    """

@property
def scanner_context_wiring(self) -> dict[str, object]:
    """Return scanner context wiring configuration.
    
    Returns:
        dict[str, object]: Wiring dict (empty if none provided)
    """

@property
def factory_overrides(self) -> dict[str, "DIFactoryOverride"]:
    """Return factory override callables.
    
    Returns:
        dict[str, DIFactoryOverride]: Override dict (empty if none provided)
    """

@property
def platform_key(self) -> str | None:
    """Return pre-resolved platform key.
    
    Returns:
        str | None: Platform key if set, else None
    """

@property
def inherit_default_event_listeners(self) -> bool:
    """Return flag indicating ambient listener inheritance.
    
    Returns:
        bool: True if ambient listeners were captured, else False
    """
```

#### State Management

```python
def replace_scan_options(self, scan_options: ScanOptionsDict) -> None:
    """Replace scan options and invalidate dependent cache entries.
    
    This method atomically updates the internal scan_options and clears
    any cached values that depend on scan_options (variable_discovery, feature_detector).
    
    Args:
        scan_options: New ScanOptionsDict
    
    Thread-safe: Protected by internal lock
    """

def _snapshot_scan_options(self) -> ScanOptionsDict:
    """Return a thread-safe snapshot of scan options (internal use).
    
    Returns:
        ScanOptionsDict: Cloned copy suitable for passing to factories
    
    Note: This is an internal method. Public API consumers should use scan_options property.
    """

def _invalidate_scan_option_dependent_cache_locked(self) -> None:
    """Clear cache entries dependent on scan_options (internal use).
    
    Clears:
    - "feature_detector"
    - "variable_discovery"
    
    Note: This is an internal method. Must be called under self._cache_lock.
    """
```

#### Mock Injection (Test Seams)

```python
def inject_mock(self, name: str, mock: Any) -> None:
    """Inject a mock for testing. Name must match a factory key.
    
    Supported mock names:
    - "event_bus"
    - "scanner_context"
    - "variable_discovery"
    - "feature_detector"
    - "variable_row_builder"
    - "blocker_fact_builder"
    - "variable_discovery_plugin"
    - "feature_detection_plugin"
    - "comment_driven_doc_plugin"
    - "task_annotation_policy_plugin"
    - "task_line_parsing_policy_plugin"
    - "task_traversal_policy_plugin"
    - "variable_extractor_policy_plugin"
    - "yaml_parsing_policy_plugin"
    - "jinja_analysis_policy_plugin"
    - "audit_plugin"
    
    Args:
        name: Factory key to mock (e.g., "variable_discovery")
        mock: Mock object to inject
    
    Behavior: Subsequent calls to factory_<name>() will return this mock
    """

def clear_mocks(self) -> None:
    """Clear all injected mocks."""
```

#### Cache Management

```python
def clear_cache(self) -> None:
    """Clear all cached service and plugin instances.
    
    Clears:
    - "variable_discovery"
    - "feature_detector"
    - "variable_row_builder"
    - "blocker_fact_builder"
    - Any other cached values
    
    Thread-safe: Protected by internal lock
    """
```

#### Override Orchestration (Internal Use)

```python
def _call_factory_override(self, name: str) -> object | None:
    """Invoke a factory override by name if present (internal use).
    
    Args:
        name: Override name (e.g., "variable_discovery_factory")
    
    Returns:
        object | None: Override result if present, else None
    
    Raises:
        PrismRuntimeError: If override callable raises exception
    
    Note: This is an internal method. Public API consumers use factory_overrides parameter.
    """
```

#### Service Factory Methods (Delegates to ServiceLocator)

```python
def factory_event_bus(self) -> EventBus:
    """Return the per-container EventBus.
    
    Returns:
        EventBus: Event bus instance
    
    Notes:
    - EventBus is created once in __init__()
    - Mockable via inject_mock("event_bus", mock)
    - Overridable via factory_overrides["event_bus_factory"]
    """

def factory_scanner_context(self) -> ScannerContext:
    """Create ScannerContext with runtime seam wiring.
    
    Returns:
        ScannerContext: Newly constructed context instance
    
    Raises:
        RuntimeError: If scanner_context_wiring not configured
    
    Notes:
    - Fresh instance created each time (not cached)
    - Requires scanner_context_wiring["scanner_context_cls"] and ["prepare_scan_context_fn"]
    - Mockable via inject_mock("scanner_context", mock)
    - Overridable via factory_overrides["scanner_context_factory"]
    """

def factory_variable_discovery(self) -> VariableDiscovery:
    """Create or return cached VariableDiscovery.
    
    Returns:
        VariableDiscovery: Variable discovery instance
    
    Notes:
    - Cached after first call
    - Cache cleared by replace_scan_options()
    - Import is deferred to break circular dependency
    - Mockable via inject_mock("variable_discovery", mock)
    - Overridable via factory_overrides["variable_discovery_factory"]
    """

def factory_feature_detector(self) -> FeatureDetector:
    """Create or return cached FeatureDetector.
    
    Returns:
        FeatureDetector: Feature detector instance
    
    Notes:
    - Cached after first call
    - Cache cleared by replace_scan_options()
    - Import is deferred to break circular dependency
    - Mockable via inject_mock("feature_detector", mock)
    - Overridable via factory_overrides["feature_detector_factory"]
    """

def factory_variable_row_builder(self) -> VariableRowBuilder:
    """Create or return cached VariableRowBuilder.
    
    Returns:
        VariableRowBuilder: Row builder instance
    
    Notes:
    - Cached after first call
    - Lightweight stateless builder
    - Mockable via inject_mock("variable_row_builder", mock)
    - Overridable via factory_overrides["variable_row_builder_factory"]
    """

def factory_blocker_fact_builder(self) -> BlockerFactBuilder:
    """Return the blocker-fact builder callable.
    
    Returns:
        BlockerFactBuilder: Blocker fact builder callable
    
    Notes:
    - Cached after first call
    - Owned by scanner_plugins layer
    - Falls back to resolve_blocker_fact_builder() if not injected
    - Mockable via inject_mock("blocker_fact_builder", mock)
    - Overridable via factory_overrides["blocker_fact_builder_factory"]
    """
```

#### Plugin Factory Methods (Delegates to PluginResolver)

```python
def factory_variable_discovery_plugin(self) -> VariableDiscoveryPlugin:
    """Resolve variable-discovery plugin via registry.
    
    Returns:
        VariableDiscoveryPlugin: Plugin instance
    
    Raises:
        ValueError: If no plugin registered for platform_key
    
    Notes:
    - Resolves via registry with platform_key
    - Fail-closed: raises ValueError if unregistered
    - Mockable via inject_mock("variable_discovery_plugin", mock)
    - Overridable via factory_overrides["variable_discovery_plugin_factory"]
    """

def factory_feature_detection_plugin(self) -> FeatureDetectionPlugin:
    """Resolve feature-detection plugin via registry.
    
    Returns:
        FeatureDetectionPlugin: Plugin instance
    
    Raises:
        ValueError: If no plugin registered for platform_key
    
    Notes:
    - Resolves via registry with platform_key
    - Fail-closed: raises ValueError if unregistered
    - Mockable via inject_mock("feature_detection_plugin", mock)
    - Overridable via factory_overrides["feature_detection_plugin_factory"]
    """

def factory_comment_driven_doc_plugin(self) -> CommentDrivenDocumentationPlugin | None:
    """Resolve optional comment-driven documentation plugin.
    
    Returns:
        CommentDrivenDocumentationPlugin | None: Plugin if wired, else None
    
    Notes:
    - Optional: returns None if not injected
    - Mockable via inject_mock("comment_driven_doc_plugin", mock)
    - Overridable via factory_overrides["comment_driven_doc_plugin_factory"]
    """

def factory_task_annotation_policy_plugin(self) -> PreparedTaskAnnotationPolicy | None:
    """Resolve optional task-annotation policy plugin.
    
    Returns:
        PreparedTaskAnnotationPolicy | None: Plugin if wired, else None
    
    Notes:
    - Optional: returns None if not injected
    - Mockable via inject_mock("task_annotation_policy_plugin", mock)
    - Overridable via factory_overrides["task_annotation_policy_plugin_factory"]
    """

def factory_task_line_parsing_policy_plugin(self) -> PreparedTaskLineParsingPolicy | None:
    """Resolve optional task-line parsing policy plugin.
    
    Returns:
        PreparedTaskLineParsingPolicy | None: Plugin if wired, else None
    
    Notes:
    - Optional: returns None if not injected
    - Mockable via inject_mock("task_line_parsing_policy_plugin", mock)
    - Overridable via factory_overrides["task_line_parsing_policy_plugin_factory"]
    """

def factory_task_traversal_policy_plugin(self) -> PreparedTaskTraversalPolicy | None:
    """Resolve optional task-traversal policy plugin.
    
    Returns:
        PreparedTaskTraversalPolicy | None: Plugin if wired, else None
    
    Notes:
    - Optional: returns None if not injected
    - Mockable via inject_mock("task_traversal_policy_plugin", mock)
    - Overridable via factory_overrides["task_traversal_policy_plugin_factory"]
    """

def factory_variable_extractor_policy_plugin(self) -> PreparedVariableExtractorPolicy | None:
    """Resolve optional variable-extractor policy plugin.
    
    Returns:
        PreparedVariableExtractorPolicy | None: Plugin if wired, else None
    
    Notes:
    - Optional: returns None if not injected
    - Mockable via inject_mock("variable_extractor_policy_plugin", mock)
    - Overridable via factory_overrides["variable_extractor_policy_plugin_factory"]
    """

def factory_yaml_parsing_policy_plugin(self) -> YAMLParsingPolicyPlugin | None:
    """Resolve optional YAML parsing policy plugin.
    
    Returns:
        YAMLParsingPolicyPlugin | None: Plugin if wired, else None
    
    Notes:
    - Optional: returns None if not injected
    - Mockable via inject_mock("yaml_parsing_policy_plugin", mock)
    - Overridable via factory_overrides["yaml_parsing_policy_plugin_factory"]
    """

def factory_jinja_analysis_policy_plugin(self) -> JinjaAnalysisPolicyPlugin | None:
    """Resolve optional Jinja analysis policy plugin.
    
    Returns:
        JinjaAnalysisPolicyPlugin | None: Plugin if wired, else None
    
    Notes:
    - Optional: returns None if not injected
    - Mockable via inject_mock("jinja_analysis_policy_plugin", mock)
    - Overridable via factory_overrides["jinja_analysis_policy_plugin_factory"]
    """

def factory_audit_plugin(self) -> Any | None:
    """Return the injected audit plugin, or None if audit not configured.
    
    Returns:
        Any | None: Audit plugin if injected, else None
    
    Notes:
    - Optional: audit is opt-in
    - Mockable via inject_mock("audit_plugin", mock)
    - Overridable via factory_overrides["audit_plugin_factory"]
    """
```

---

## 2. PluginResolver (Plugin Resolution)

### Class Signature

```python
class PluginResolver:
    """Resolve plugins from registry or DI wiring.
    
    PluginResolver encapsulates all plugin resolution logic:
    - Registry-driven plugins: variable_discovery, feature_detection
    - Optional plugins: policy plugins, comment doc, audit
    
    PluginResolver is stateless and delegates mock/override checks to DIContainer.
    All factory methods receive mock/override check results before execution.
    """

    def __init__(self, di: DIContainer) -> None:
        """Initialize with DIContainer reference.
        
        Args:
            di: DIContainer for accessing mocks, overrides, registry, platform_key
        """
```

### Public Methods

```python
def factory_variable_discovery_plugin(self) -> VariableDiscoveryPlugin:
    """Resolve variable-discovery plugin via registry.
    
    Resolution steps:
    1. DIContainer checks mocks (inject_mock)
    2. DIContainer checks overrides (factory_overrides)
    3. PluginResolver (this method) executes resolution:
       a. Resolve platform_key (_resolve_platform_key)
       b. Get registry (_get_registry)
       c. Look up plugin class: registry.get_variable_discovery_plugin(platform_key)
       d. Construct plugin: _construct_runtime_plugin(plugin_cls, di=self._di)
    
    Returns:
        VariableDiscoveryPlugin: Resolved plugin instance
    
    Raises:
        ValueError: If no plugin registered for platform_key
        PrismRuntimeError: If plugin shape invalid (missing di= parameter)
    """

def factory_feature_detection_plugin(self) -> FeatureDetectionPlugin:
    """Resolve feature-detection plugin via registry.
    
    Resolution steps:
    1. DIContainer checks mocks (inject_mock)
    2. DIContainer checks overrides (factory_overrides)
    3. PluginResolver (this method) executes resolution:
       a. Resolve platform_key (_resolve_platform_key)
       b. Get registry (_get_registry)
       c. Look up plugin class: registry.get_feature_detection_plugin(platform_key)
       d. Construct plugin: _construct_runtime_plugin(plugin_cls, di=self._di)
    
    Returns:
        FeatureDetectionPlugin: Resolved plugin instance
    
    Raises:
        ValueError: If no plugin registered for platform_key
        PrismRuntimeError: If plugin shape invalid (missing di= parameter)
    """

def factory_comment_driven_doc_plugin(self) -> CommentDrivenDocumentationPlugin | None:
    """Resolve optional comment-driven documentation plugin.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (wiring happens via mock/override injection)
    """

def factory_task_annotation_policy_plugin(self) -> PreparedTaskAnnotationPolicy | None:
    """Resolve optional task-annotation policy plugin.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (wiring happens via mock/override injection)
    """

def factory_task_line_parsing_policy_plugin(self) -> PreparedTaskLineParsingPolicy | None:
    """Resolve optional task-line parsing policy plugin.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (wiring happens via mock/override injection)
    """

def factory_task_traversal_policy_plugin(self) -> PreparedTaskTraversalPolicy | None:
    """Resolve optional task-traversal policy plugin.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (wiring happens via mock/override injection)
    """

def factory_variable_extractor_policy_plugin(self) -> PreparedVariableExtractorPolicy | None:
    """Resolve optional variable-extractor policy plugin.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (wiring happens via mock/override injection)
    """

def factory_yaml_parsing_policy_plugin(self) -> YAMLParsingPolicyPlugin | None:
    """Resolve optional YAML parsing policy plugin.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (wiring happens via mock/override injection)
    """

def factory_jinja_analysis_policy_plugin(self) -> JinjaAnalysisPolicyPlugin | None:
    """Resolve optional Jinja analysis policy plugin.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (wiring happens via mock/override injection)
    """

def factory_audit_plugin(self) -> Any | None:
    """Return the injected audit plugin, or None if audit not configured.
    
    Returns None (mock/override checks happen in DIContainer).
    
    Returns:
        None: Always returns None (audit is opt-in)
    """
```

### Private Helper Methods (For Builders Only)

```python
def _get_registry(self) -> PluginRegistry:
    """Return the injected plugin registry or raise.
    
    Returns:
        PluginRegistry: Registry instance
    
    Raises:
        ValueError: If no registry provided to DIContainer
    
    Note: Private method for internal use by plugin factories
    """

def _resolve_platform_key(self) -> str:
    """Return pre-resolved platform key or delegate to module-level resolver.
    
    Resolution priority:
    1. DIContainer.platform_key (if set)
    2. resolve_platform_key(scan_options, registry) (3-way: explicit > policy > registry default)
    
    Returns:
        str: Resolved platform key
    
    Raises:
        ValueError: If no platform key resolvable
    
    Note: Private method for internal use by plugin factories
    """
```

---

## 3. ServiceLocator (Service Factory Orchestration)

### Class Signature

```python
class ServiceLocator:
    """Service factory orchestration for scanner components.
    
    ServiceLocator encapsulates all service factory methods:
    - EventBus: per-container singleton
    - ScannerContext: fresh instance each call
    - VariableDiscovery: cached with scan_options dependency
    - FeatureDetector: cached with scan_options dependency
    - VariableRowBuilder: cached, lightweight stateless builder
    - BlockerFactBuilder: cached, plugin-layer owned callable
    
    ServiceLocator delegates mock/override checks to DIContainer.
    All caching is coordinated by DIContainer._cache_lock for thread safety.
    """

    def __init__(self, di: DIContainer) -> None:
        """Initialize with DIContainer reference.
        
        Args:
            di: DIContainer for accessing mocks, overrides, cache, cache_lock
        """
```

### Public Methods

```python
def factory_event_bus(self) -> EventBus:
    """Return the per-container EventBus.
    
    Notes:
    - EventBus created once in DIContainer.__init__()
    - This method delegates to DIContainer._event_bus
    - Mock/override checks happen in DIContainer before delegation
    
    Returns:
        EventBus: Event bus instance
    """

def factory_scanner_context(self) -> ScannerContext:
    """Create ScannerContext with runtime seam wiring.
    
    Fresh instance created each time (no caching).
    Reads scanner_context_wiring from DIContainer for class and prepare function.
    
    Returns:
        ScannerContext: Newly constructed context
    
    Raises:
        RuntimeError: If scanner_context_wiring not configured
    
    Notes:
    - Requires scanner_context_wiring["scanner_context_cls"]
    - Requires scanner_context_wiring["prepare_scan_context_fn"]
    - Mock/override checks happen in DIContainer before delegation
    """

def factory_variable_discovery(self) -> VariableDiscovery:
    """Create or return cached VariableDiscovery.
    
    Caching:
    - First call creates instance via _create_variable_discovery()
    - Subsequent calls return cached instance
    - Cache protected by DIContainer._cache_lock
    - Cache cleared by DIContainer.replace_scan_options()
    
    Deferred Imports:
    - VariableDiscovery imported only when factory invoked
    - Breaks circular dependency with scanner_extract
    
    Returns:
        VariableDiscovery: Cached instance
    
    Notes:
    - Mock/override checks happen in DIContainer before delegation
    - Caching coordinated by DIContainer._cache_lock
    """

def factory_feature_detector(self) -> FeatureDetector:
    """Create or return cached FeatureDetector.
    
    Caching:
    - First call creates instance via _create_feature_detector()
    - Subsequent calls return cached instance
    - Cache protected by DIContainer._cache_lock
    - Cache cleared by DIContainer.replace_scan_options()
    
    Deferred Imports:
    - FeatureDetector imported only when factory invoked
    - Breaks circular dependency with scanner_extract
    
    Returns:
        FeatureDetector: Cached instance
    
    Notes:
    - Mock/override checks happen in DIContainer before delegation
    - Caching coordinated by DIContainer._cache_lock
    """

def factory_variable_row_builder(self) -> VariableRowBuilder:
    """Create or return cached VariableRowBuilder.
    
    Caching:
    - First call creates lightweight builder instance
    - Subsequent calls return cached instance
    - Cache protected by DIContainer._cache_lock
    
    Returns:
        VariableRowBuilder: Cached builder instance
    
    Notes:
    - Mock/override checks happen in DIContainer before delegation
    - Lightweight stateless builder
    - Cached for performance reuse
    """

def factory_blocker_fact_builder(self) -> BlockerFactBuilder:
    """Return the blocker-fact builder callable.
    
    Caching:
    - First call resolves builder (injected or default)
    - Subsequent calls return cached instance
    - Cache protected by DIContainer._cache_lock
    
    Resolution:
    1. If DIContainer._blocker_fact_builder_fn set, use that
    2. Else import resolve_blocker_fact_builder() from scanner_plugins.defaults
    
    Returns:
        BlockerFactBuilder: Blocker fact builder callable
    
    Notes:
    - Mock/override checks happen in DIContainer before delegation
    - Owned by scanner_plugins layer
    - Fallback import guard for plugin layer wiring
    """
```

---

## Module-Level Utilities (Shared Across Classes)

These functions remain at module level in `src/prism/scanner_core/di.py` and are reusable:

```python
def _clone_container_structure(value: object) -> object:
    """Clone container nodes while preserving opaque object identity.
    
    Used by: clone_scan_options()
    """

def clone_scan_options(scan_options: Mapping[str, object]) -> ScanOptionsDict:
    """Return a container-only snapshot of scan options for runtime consumers.
    
    Returns:
        ScanOptionsDict: Cloned copy suitable for passing to factories
    
    Note: Used by DIContainer.scan_options property and factory methods
    """

def resolve_platform_key(
    scan_options: ScanOptionsDict,
    registry: _PlatformKeyRegistry | None = None,
) -> str:
    """Resolve platform key: scan_pipeline_plugin > policy_context > platform > registry default.
    
    Resolution priority:
    1. scan_options["scan_pipeline_plugin"] (explicit override)
    2. scan_options["policy_context"]["selection"]["plugin"] (policy selection)
    3. scan_options["platform"] (platform specification)
    4. registry.get_default_platform_key() (registry default)
    
    Returns:
        str: Resolved platform key
    
    Raises:
        ValueError: If no platform key resolvable
    
    Used by: PluginResolver._resolve_platform_key()
    """

def _construct_runtime_plugin(
    plugin_class: type[Any],
    *,
    plugin_kind: str,
    platform_key: str,
    di: DIContainer,
) -> Any:
    """Construct a registry-returned runtime plugin through the DI seam.
    
    Validates that plugin_class accepts di= parameter, then constructs
    plugin instance with di=di keyword argument.
    
    Args:
        plugin_class: Plugin class to construct
        plugin_kind: Kind name for error reporting (e.g., "variable_discovery")
        platform_key: Platform key for error reporting
        di: DIContainer reference to pass to plugin constructor
    
    Returns:
        Any: Constructed plugin instance
    
    Raises:
        PrismRuntimeError: If plugin shape invalid (missing di= parameter)
    
    Used by: PluginResolver.factory_*_plugin() for registry plugins
    """

def _create_variable_discovery(
    di: DIContainer,
    role_path: str,
    scan_options: ScanOptionsDict,
) -> VariableDiscovery:
    """Import VariableDiscovery only at the DI composition seam.
    
    Deferred import breaks circular dependency:
    - VariableDiscovery may import from scanner_extract
    - scanner_extract may import di_helpers
    - This deferred import seam prevents import-time circularity
    
    Returns:
        VariableDiscovery: Newly constructed instance
    
    Used by: ServiceLocator.factory_variable_discovery()
    """

def _create_feature_detector(
    di: DIContainer,
    role_path: str,
    scan_options: ScanOptionsDict,
) -> FeatureDetector:
    """Import FeatureDetector only at the DI composition seam.
    
    Deferred import breaks circular dependency:
    - FeatureDetector imports from scanner_extract
    - This deferred import seam prevents import-time circularity
    
    Returns:
        FeatureDetector: Newly constructed instance
    
    Used by: ServiceLocator.factory_feature_detector()
    """
```

---

## Type Definitions & Protocols

### From `prism.scanner_core.protocols_runtime`

```python
DIFactoryOverride = Callable[
    [DIContainer, str, ScanOptionsDict],
    object,
]
"""Callable signature for factory overrides.

Args:
    di: DIContainer instance
    role_path: Role path from DIContainer
    scan_options: Snapshot of scan_options at call time

Returns:
    object: Replacement value (type determined by factory kind)
"""

BlockerFactBuilder = Callable[..., Any]
"""Callable signature for blocker fact builders."""
```

### From `prism.scanner_data.contracts_request`

```python
ScanOptionsDict = TypedDict(...)
"""Type-safe dict for scan options."""
```

### From `prism.scanner_plugins.registry`

```python
PluginRegistry = ...
"""Plugin registry interface."""
```

---

## Backward Compatibility Guarantees

### Unchanged Public API

- ✅ All `factory_*()` method names (same)
- ✅ All `factory_*()` signatures (same)
- ✅ All `factory_*()` return types (same)
- ✅ All property names and types (same)
- ✅ `inject_mock()`, `clear_mocks()`, `clear_cache()`, `replace_scan_options()` (same)

### Internal Details (May Change)

- ❌ `_plugin_resolver`, `_service_locator` instance variables (new, internal)
- ❌ Method implementation (now delegates to PluginResolver/ServiceLocator)
- ❌ Plugin/service factory implementation (moved to new classes)

### No Breaking Changes

All existing code using DIContainer works unchanged:

```python
# Old code still works
di = DIContainer(...)
plugin = di.factory_variable_discovery_plugin()
service = di.factory_variable_discovery()
di.inject_mock("variable_discovery", mock_obj)
```

---

## Summary Table

| Responsibility | Class | Public Methods | Status |
| --- | --- | --- | --- |
| State Management | DIContainer | scan_options, plugin_registry, factory_overrides, etc. | Stays |
| Mock Orchestration | DIContainer | inject_mock(), clear_mocks() | Stays |
| Override Orchestration | DIContainer | _call_factory_override() | Stays |
| Service Factories | ServiceLocator | factory_event_bus(), factory_scanner_context(), factory_variable_discovery(), factory_feature_detector(), factory_variable_row_builder(), factory_blocker_fact_builder() | New (Extracted) |
| Plugin Factories | PluginResolver | factory_variable_discovery_plugin(), factory_feature_detection_plugin(), factory_*_policy_plugin(), factory_audit_plugin() | New (Extracted) |
| Delegation | DIContainer | All factory_*() methods | Delegates to ServiceLocator/PluginResolver |
