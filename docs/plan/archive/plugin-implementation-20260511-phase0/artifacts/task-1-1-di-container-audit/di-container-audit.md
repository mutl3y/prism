# DI Container Analysis Report (Task 1.1)

**Scout**: DIArchitecture  
**Date**: May 9, 2026  
**File**: src/prism/scanner_core/di.py  
**Current Size**: 821 lines  
**Methods Classified**: 23 public methods + 6 internal helpers

---

## Executive Summary

The DIContainer is a 821-line god object managing four distinct responsibilities:
1. **Service Location** — creating/caching services (event bus, scanner context, variable discovery, etc.)
2. **Plugin Resolution** — resolving plugins from registry by platform key
3. **Factory Coordination** — orchestrating factory creation with overrides and mocking
4. **Configuration State** — managing scan options, cache, mocks, and testing seams

**Key Finding**: Responsibilities are already separated by method naming and contract boundaries, but all code lives in one class. The codebase is extraction-ready with clear ownership boundaries.

---

## Method Classification (23 Public Methods)

### Category A: SERVICE_LOCATION (Getters & Properties)

Provide read-only access to container state and metadata. **These stay in DIContainer** as they define the public interface.

| Method | Description | Lines | Notes |
|--------|-------------|-------|-------|
| `scan_options` (property) | Return snapshot of scan options dict | 3 | Thread-safe, cloned |
| `plugin_registry` (property) | Return injected registry or None | 2 | Immutable reference |
| `scanner_context_wiring` (property) | Return wiring dict for context setup | 2 | Immutable reference |
| `factory_overrides` (property) | Return dict of factory overrides | 2 | Immutable reference |
| `platform_key` (property) | Return pre-resolved platform key | 2 | Immutable reference |
| `inherit_default_event_listeners` (property) | Return listener inheritance flag | 2 | Immutable reference |

**Total**: 6 properties providing read-only access to container internals. **All stay in DIContainer** to maintain public interface contract.

---

### Category B: FACTORY_ORCHESTRATION (Core Service Creation)

Create/retrieve cached service instances. These are **candidates for ServiceLocator** but may need split:

| Method | Description | Lines | Dependencies | Escalation |
|--------|-------------|-------|--------------|------------|
| `factory_event_bus()` | Create/return EventBus instance | 4 | `_event_bus` (init-time) | None — simple return |
| `factory_scanner_context()` | Create ScannerContext with wiring | 20 | `_scanner_context_wiring`, scan_options, role_path | None — straightforward |
| `factory_variable_discovery()` | Create/cache VariableDiscovery | 20 | `_create_variable_discovery()`, factory override, mock support | Deferred import (circular dep) |
| `factory_feature_detector()` | Create/cache FeatureDetector | 20 | `_create_feature_detector()`, factory override, mock support | Deferred import (circular dep) |
| `factory_variable_row_builder()` | Create/cache VariableRowBuilder | 6 | Direct import (safe) | None — simple |
| `factory_blocker_fact_builder()` | Return blocker-fact builder | 10 | Optional `_blocker_fact_builder_fn`, fallback import | None — simple dispatch |

**Total**: 6 methods for core service creation.

**ServiceLocator Will Need**:
- Access to cache (shared, keyed by service name)
- Access to factory overrides (read-only)
- Access to mocks (for testing support)
- Thread-safe cache locking via `_cache_lock`

**Risk**: Variable discovery and feature detector have deferred imports to break circular dependencies. ServiceLocator must preserve this pattern.

---

### Category C: PLUGIN_RESOLUTION (Registry-Driven Plugin Loading)

Resolve plugins via PluginRegistry, handle platform-key selection. **Candidates for PluginResolver**:

| Method | Description | Lines | Registry? | Platform Key? | Override? | Mock? |
|--------|-------------|-------|-----------|---------------|-----------|-------|
| `factory_variable_discovery_plugin()` | Resolve VariableDiscoveryPlugin | 18 | ✅ | ✅ | ✅ | ✅ |
| `factory_feature_detection_plugin()` | Resolve FeatureDetectionPlugin | 18 | ✅ | ✅ | ✅ | ✅ |
| `factory_comment_driven_doc_plugin()` | Resolve optional CommentDrivenDoc plugin | 9 | ❌ | ❌ | ✅ | ✅ |
| `factory_task_annotation_policy_plugin()` | Resolve optional TaskAnnotation policy | 9 | ❌ | ❌ | ✅ | ✅ |
| `factory_task_line_parsing_policy_plugin()` | Resolve optional TaskLineParsing policy | 9 | ❌ | ❌ | ✅ | ✅ |
| `factory_task_traversal_policy_plugin()` | Resolve optional TaskTraversal policy | 9 | ❌ | ❌ | ✅ | ✅ |
| `factory_variable_extractor_policy_plugin()` | Resolve optional VariableExtractor policy | 9 | ❌ | ❌ | ✅ | ✅ |
| `factory_yaml_parsing_policy_plugin()` | Resolve optional YAML policy | 9 | ❌ | ❌ | ✅ | ✅ |
| `factory_jinja_analysis_policy_plugin()` | Resolve optional Jinja policy | 9 | ❌ | ❌ | ✅ | ✅ |
| `factory_audit_plugin()` | Return optional audit plugin | 8 | ❌ | ❌ | ✅ | ✅ |

**Total**: 10 methods for plugin resolution.

**Pattern Observation**:
- 2 plugins use full registry resolution (`variable_discovery`, `feature_detection`)
- 8 plugins are optional (no registry) — these are wiring/override/mock only
- ALL support override + mocking pattern

**PluginResolver Will Need**:
- Access to registry (read-only)
- Access to mocks (for testing)
- Access to factory overrides (read-only)
- `_resolve_platform_key()` helper (for registry lookups)

---

### Category D: DI_BINDING (Configuration & State Management)

Configure container state, manage overrides, testing support. **These stay in DIContainer** as they're configuration management:

| Method | Description | Lines | Responsibility |
|--------|-------------|-------|-----------------|
| `replace_scan_options()` | Replace scan options & invalidate cache | 5 | Update state + cache coordination |
| `inject_mock()` | Inject mock for testing | 2 | Test seam support |
| `clear_mocks()` | Clear all mocks | 2 | Test cleanup |
| `clear_cache()` | Clear cached instances | 5 | Cache management |
| `_call_factory_override()` | Invoke factory override (internal) | 17 | Override orchestration |

**Total**: 5 methods for binding/configuration.

**These Stay in DIContainer** because they manage cross-cutting concerns (cache coordination, override orchestration).

---

### Category E: INTERNAL HELPERS (Private Methods)

Support methods used by public API. Will stay in DIContainer or be extracted with delegating public methods:

| Method | Description | Visibility | Candidates |
|--------|-------------|------------|-----------|
| `_snapshot_scan_options()` | Clone options for thread safety | Private | ServiceLocator (if needed by both) |
| `_invalidate_scan_option_dependent_cache_locked()` | Invalidate cache after options change | Private | DIContainer (coordination) |
| `_get_registry()` | Return registry or raise | Private | PluginResolver (extract) |
| `_resolve_platform_key()` | Resolve platform key from options/registry | Private | PluginResolver (extract) |

---

## Cross-Method Dependencies (Extraction Risk Assessment)

### Service Factory Dependencies

```
factory_variable_discovery()
  └─> _create_variable_discovery() [module-level helper]
       └─> Import VariableDiscovery (deferred)

factory_feature_detector()
  └─> _create_feature_detector() [module-level helper]
       └─> Import FeatureDetector (deferred)

factory_blocker_fact_builder()
  └─> _blocker_fact_builder_fn OR import resolve_blocker_fact_builder()
```

**Risk**: Deferred imports must remain intact. These are breaking circular dependencies between di.py and scanner_extract.

### Plugin Resolution Dependencies

```
factory_variable_discovery_plugin()
  └─> _resolve_platform_key()
  └─> _get_registry()
  └─> registry.get_variable_discovery_plugin(platform_key)
  └─> _construct_runtime_plugin() [module-level, see below]

factory_feature_detection_plugin()
  └─> Same as above
```

**Risk**: Plugin resolution depends on both platform key and registry access. Both must stay accessible.

### Shared State Patterns

```
All factory_*() methods
  ├─> Check mocks dict (_mocks[name])
  ├─> Check factory overrides (_call_factory_override(name))
  ├─> Check cache (_cache[key]) if applicable
  └─> Create/return instance

All plugin factories
  ├─> Check mocks (_mocks[name])
  ├─> Check overrides (_call_factory_override(name))
  └─> Resolve from registry OR return None
```

**Key Finding**: Both ServiceLocator and PluginResolver will need:
- Mocks dict (for testing)
- Factory overrides dict (for customization)
- Option to use cache (ServiceLocator uses it; PluginResolver may not need it)

---

## Shared State & Coordination Points

### State Required by Both PluginResolver and ServiceLocator

| State | Type | Mutable? | Thread-Safe? | Usage |
|-------|------|---------|--------------|-------|
| `_registry` | PluginRegistry \| None | No | N/A | Both (registry lookups) |
| `_platform_key` | str \| None | No | N/A | Both (platform resolution) |
| `_scan_options` | ScanOptionsDict | Via replace_options | Yes (via lock) | Both (snapshot calls) |
| `_role_path` | str | No | N/A | Both (context creation) |
| `_mocks` | dict[str, Any] | Yes | **NO** (injection only) | Both (mock support) |
| `_factory_overrides` | dict[str, DIFactoryOverride] | No | N/A | Both (override checking) |
| `_cache_lock` | RLock | No | N/A | Cache coordination |

**Critical Finding**: `_mocks` dict is **not thread-safe**. Current code assumes single-threaded test setup. This must be preserved in extraction.

### Coordination Between Services

**Cache Invalidation Flow**:
```
replace_scan_options()
  └─> _invalidate_scan_option_dependent_cache_locked()
       ├─> Remove "variable_discovery" from cache
       └─> Remove "feature_detector" from cache
```

Both ServiceLocator and PluginResolver will need to respect this invalidation boundary. Services that depend on `scan_options` cannot be cached independently.

---

## Module-Level Helpers (Will Stay at Module Level)

These are not methods but module-level functions that support DI composition:

| Function | Lines | Current Users | Purpose |
|----------|-------|----------------|---------|
| `_clone_container_structure()` | 10 | `clone_scan_options()` | Deep-clone container structures |
| `clone_scan_options()` | 8 | Snapshot code | Create thread-safe scan_options snapshot |
| `resolve_platform_key()` | 19 | `_resolve_platform_key()` method | Resolve platform key from options/registry/default |
| `_construct_runtime_plugin()` | 25 | All plugin factories | Validate plugin shape & call constructor |
| `_create_variable_discovery()` | 6 | `factory_variable_discovery()` | Deferred import wrapper |
| `_create_feature_detector()` | 6 | `factory_feature_detector()` | Deferred import wrapper |

**These must remain at module level** because they're imported by other modules (e.g., `resolve_platform_key` is used by name in task imports).

---

## Extraction Boundaries (Proposed)

### DIContainer (Coordinator/Facade)

**Stays**: Configuration, state management, public interface

```python
class DIContainer:
    # Constructor (unchanged)
    def __init__(self, ...)
    
    # PUBLIC INTERFACE: Getters (unchanged)
    @property
    def scan_options(self) -> ScanOptionsDict
    @property
    def plugin_registry(self) -> PluginRegistry | None
    @property
    def scanner_context_wiring(self) -> dict[str, object]
    @property
    def factory_overrides(self) -> dict[str, DIFactoryOverride]
    @property
    def platform_key(self) -> str | None
    @property
    def inherit_default_event_listeners(self) -> bool
    
    # STATE MANAGEMENT (unchanged)
    def replace_scan_options(self, scan_options: ScanOptionsDict) -> None
    def inject_mock(self, name: str, mock: Any) -> None
    def clear_mocks(self) -> None
    def clear_cache(self) -> None
    
    # INTERNAL HELPERS (unchanged)
    def _snapshot_scan_options(self) -> ScanOptionsDict
    def _invalidate_scan_option_dependent_cache_locked(self) -> None
    def _call_factory_override(self, name: str) -> object | None
    
    # SERVICE FACTORIES: Delegate to ServiceLocator
    def factory_event_bus(self) -> EventBus
    def factory_scanner_context(self) -> ScannerContext
    def factory_variable_discovery(self) -> VariableDiscovery
    def factory_feature_detector(self) -> FeatureDetector
    def factory_variable_row_builder(self) -> VariableRowBuilder
    def factory_blocker_fact_builder(self) -> BlockerFactBuilder
    
    # PLUGIN FACTORIES: Delegate to PluginResolver
    def factory_variable_discovery_plugin(self) -> VariableDiscoveryPlugin
    def factory_feature_detection_plugin(self) -> FeatureDetectionPlugin
    def factory_comment_driven_doc_plugin(self) -> CommentDrivenDocumentationPlugin | None
    # ... all other plugin factories
```

**Refactored Storage**:
- Compose ServiceLocator in __init__
- Compose PluginResolver in __init__
- Delegate factory_* methods to appropriate delegate

---

### ServiceLocator (New Class)

**Owns**: Service creation, caching, orchestration

```python
class ServiceLocator:
    def __init__(self, di: DIContainer):
        self._di = di
        # Inherit cache/lock from DIContainer
    
    # Core services (moved from DIContainer)
    def factory_event_bus(self) -> EventBus
    def factory_scanner_context(self) -> ScannerContext
    def factory_variable_discovery(self) -> VariableDiscovery
    def factory_feature_detector(self) -> FeatureDetector
    def factory_variable_row_builder(self) -> VariableRowBuilder
    def factory_blocker_fact_builder(self) -> BlockerFactBuilder
```

**Shared Access**:
- Read-only: `_di.plugin_registry`, `_di.factory_overrides`, `_di._mocks`
- Read-only snapshot: `_di.scan_options`
- Cache coordination: `_di._cache_lock`

---

### PluginResolver (New Class)

**Owns**: Plugin resolution, registry access, platform-key handling

```python
class PluginResolver:
    def __init__(self, di: DIContainer):
        self._di = di
    
    # Plugin resolution (moved from DIContainer)
    def factory_variable_discovery_plugin(self) -> VariableDiscoveryPlugin
    def factory_feature_detection_plugin(self) -> FeatureDetectionPlugin
    def factory_comment_driven_doc_plugin(self) -> CommentDrivenDocumentationPlugin | None
    # ... all other plugin factories (10 total)
    
    # Internal helpers (extracted)
    def _get_registry(self) -> PluginRegistry
    def _resolve_platform_key(self) -> str
```

**Shared Access**:
- Read-only: `_di.plugin_registry`, `_di.factory_overrides`, `_di._mocks`
- Read-only snapshot: `_di.scan_options`

---

## Extraction Complexity Assessment

| Aspect | Complexity | Notes |
|--------|-----------|-------|
| Service extraction | **LOW** | Clear boundaries, minimal crosstalk |
| Plugin extraction | **LOW** | Well-defined pattern, minimal shared state |
| Cache management | **MEDIUM** | Both classes may need cache read access; coordination needed |
| Mocks/overrides | **MEDIUM** | Testing seams spread across both; must stay accessible |
| Thread safety | **LOW** | Locking happens in DIContainer; delegates are read-only |
| Deferred imports | **LOW** | Pattern already isolated in module-level helpers |
| Backward compatibility | **MEDIUM** | All public factory methods must remain on DIContainer facade |

---

## Summary of Findings

### ✅ Strengths

1. **Clear responsibility boundaries** — Methods already grouped by purpose (factory, plugin, state)
2. **Minimal cross-method dependencies** — Services and plugins are mostly independent
3. **Testing seams in place** — Override and mock support is consistent across all factories
4. **Thread safety design** — Locking is centralized; easy to maintain after extraction
5. **Module-level helpers isolated** — Deferred imports are already factored out
6. **Extraction-ready code** — No god-object anti-patterns; just needs class-level organization

### ⚠️ Risks

1. **Mocks dict is NOT thread-safe** — Current code assumes test-time single-threaded access; must document in extracted classes
2. **Cache invalidation coupling** — Both ServiceLocator and PluginResolver need to respect scan_options invalidation
3. **Plugin pattern complexity** — 10 different plugin factory signatures; all must be preserved identically
4. **Deferred imports must stay intact** — Circular dependency breaking is fragile; any reorganization could break it

### 📋 Recommended Extraction Sequence

1. **Phase 1**: Extract PluginResolver (lower risk, fewer dependencies)
2. **Phase 2**: Extract ServiceLocator (manages cache coordination)
3. **Phase 3**: Refactor DIContainer to facade pattern + coordinate with both

---

## Metrics

- **Total methods analyzed**: 23 public + 6 internal helpers
- **Methods for ServiceLocator**: 6 core service factories
- **Methods for PluginResolver**: 10 plugin resolution methods
- **Methods staying in DIContainer**: 7 (properties + state management)
- **Module-level helpers**: 6 (unchanged)
- **Estimated new lines** (after extraction):
  - DIContainer: ~150 lines (facade + delegation)
  - ServiceLocator: ~120 lines (service factories)
  - PluginResolver: ~140 lines (plugin factories)
