# Service Locator Design Rationale (Task 1.3)

**Scout**: ServiceLocatorContract  
**Date**: May 9, 2026  
**Status**: Design Phase Complete

---

## Executive Summary

The **ServiceLocator** class extracts 6 service factory methods from DIContainer, reducing the god-object from 821 lines to ~150 lines. ServiceLocator is responsible for **creating and caching service instances** — EventBus, ScannerContext, VariableDiscovery, FeatureDetector, VariableRowBuilder, and BlockerFactBuilder.

**Key Design Principles:**
1. ServiceLocator is a **separate class** (not utility functions) for extensibility and explicit protocol definition
2. ServiceLocator **delegates state management** to DIContainer (mocks, overrides, caching, locking)
3. ServiceLocator **owns factory logic** (creation, deferred imports, mock/override coordination)
4. Protocol-based design enables future **multi-implementation strategies** without API changes
5. Thread safety is **guaranteed** via DIContainer's RLock coordination

---

## Why ServiceLocator as a Separate Class?

### Option A: Leave in DIContainer (Status Quo)
- ❌ DIContainer becomes 900+ line god object
- ❌ Mixes concerns: state management + service location + plugin resolution
- ❌ Hard to unit-test individual factory paths
- ❌ Unclear responsibility boundaries (which factories depend on what?)

### Option B: Utility Functions at Module Level
```python
def create_event_bus(di: DIContainer) -> EventBus:
    return di._event_bus

def create_scanner_context(di: DIContainer) -> ScannerContext:
    # ...
```
- ✅ Simple extraction
- ❌ No protocol to enforce consistency
- ❌ No natural place for mock/override coordination
- ❌ Not extensible (can't swap implementation strategies)
- ❌ Callers must pass `di` explicitly everywhere

### Option C: ServiceLocator Class ✅ CHOSEN
```python
class ServiceLocator:
    def __init__(self, di: DIContainer):
        self._di = di

    def factory_event_bus(self) -> EventBus:
        return self._di._event_bus
    
    # 5 more factory methods
```
- ✅ Clear responsibility (service location only)
- ✅ Protocol-based interface (testable, extensible)
- ✅ Natural home for mock/override logic
- ✅ Owned by DIContainer (single source of truth)
- ✅ Future implementations can be swapped at DIContainer init time

**Decision**: **ServiceLocator as separate class** provides the right balance of clarity, extensibility, and responsibility separation.

---

## Protocol-Based Design Benefits

### Explicit Contract (`ServiceLocatorProtocol`)
Every factory method signature is defined as a Protocol:
```python
class ServiceLocatorProtocol(Protocol):
    def factory_event_bus(self) -> EventBus: ...
    def factory_variable_discovery(self) -> VariableDiscovery: ...
    # ... 4 more
```

**Benefits**:
1. **Type Safety**: Mypy can verify all callers use the correct method signatures
2. **Documentation**: Each method's return type, exceptions, thread safety, caching semantics are explicit
3. **Extensibility**: New implementations can implement the protocol without modifying DIContainer
4. **Testing**: Mocks can be verified against the protocol
5. **Clarity**: No ambiguity about what ServiceLocator does (creates services, not plugins)

### Separation from PluginResolver
Two separate protocols prevent confusion:
- **ServiceLocatorProtocol**: Creates/caches *services* (EventBus, ScannerContext, VariableDiscovery)
- **PluginResolverProtocol**: Resolves/caches *plugins* (VariableDiscoveryPlugin, FeatureDetectionPlugin)

This prevents future developers from mixing service creation with plugin resolution.

---

## Extensibility Architecture

### Why Future Implementations?

1. **Alternative Cache Strategies**: 
   - Current: Simple dict with RLock
   - Future: LRU cache with TTL, Redis-backed cache, distributed cache

2. **Service Creation Strategies**:
   - Current: Lazy creation on first call
   - Future: Eager creation, service pooling, soft factories

3. **Monitoring/Observability**:
   - Current: Basic creation + caching
   - Future: Emit events on cache hits/misses, track service lifetimes

### Extension Example

```python
# Future: Alternative implementation with monitoring
class ObservableServiceLocator(ServiceLocator):
    def factory_variable_discovery(self) -> VariableDiscovery:
        cache_key = "variable_discovery"
        
        # Record cache access
        if self._is_cached(cache_key):
            self._emitter.emit("cache_hit", service="variable_discovery")
        else:
            self._emitter.emit("cache_miss", service="variable_discovery")
        
        # Delegate to parent factory logic
        return super().factory_variable_discovery()
```

The protocol ensures the alternative implementation has the right signature without modifying DIContainer.

---

## Thread Safety Guarantees

### Mechanism: DIContainer-Owned RLock

All ServiceLocator methods are protected by `DIContainer._cache_lock`:

```python
class ServiceLocator:
    def factory_variable_discovery(self) -> VariableDiscovery:
        key = "variable_discovery"
        
        # Check mocks (unsynchronized — reads are atomic on CPython)
        if key in self._di._mocks:
            return self._di._mocks[key]
        
        # Coordinate with DIContainer's lock
        with self._di._cache_lock:  # ← RLock protects cache access
            if key not in self._di._cache:
                self._di._cache[key] = _create_variable_discovery(...)
        
        return self._di._cache[key]
```

### GIL-Safe Guarantees

1. **Mock Check**: Atomic dict read under CPython GIL (safe without lock)
2. **Cache Check**: Protected by explicit RLock (safe in all Python implementations)
3. **Cache Insertion**: Protected by explicit RLock (atomic operation)
4. **Return**: Returning cached object is safe (reference copy under GIL)

**Result**: Multiple threads can call ServiceLocator methods simultaneously without coordination on the caller side. The container guarantees thread safety.

### Deferred Import Thread Safety

Deferred imports in factory methods are also GIL-safe:
```python
def _create_variable_discovery(...):
    from prism.scanner_core.variable_discovery import VariableDiscovery  # ← Module import
    return VariableDiscovery(...)
```

Python's import system holds the GIL during module import, making this thread-safe. The first call to factory_variable_discovery() will import the module once; subsequent calls will return the cached module from `sys.modules`.

---

## Cache Coordination with DIContainer

### Cache Ownership

DIContainer owns three caches:
1. **Service Cache** (`self._cache`): ServiceLocator stores created services here
2. **Mock Cache** (`self._mocks`): DIContainer stores test mocks here
3. **Backend Cache** (`self.cache_backend`): Optional scan result cache (unrelated)

### Cache Keys (ServiceLocator Services)

| Key | Created By | Cached | Invalidated | Reason |
|-----|-----------|--------|------------|--------|
| `event_bus` | ServiceLocator | ✅ Once | ❌ Never | Singleton, no policy dependency |
| `scanner_context` | ServiceLocator | ✅ Once | ❌ Never | Created at runtime, policy-independent |
| `variable_discovery` | ServiceLocator | ✅ Once | ✅ By replace_scan_options() | Policy-dependent |
| `feature_detector` | ServiceLocator | ✅ Once | ✅ By replace_scan_options() | Policy-dependent |
| `variable_row_builder` | ServiceLocator | ✅ Once | ❌ Never | Stateless utility |
| `blocker_fact_builder` | ServiceLocator | ✅ Once | ❌ Never | Determined at init time |

### Invalidation Trigger: `replace_scan_options()`

```python
class DIContainer:
    def replace_scan_options(self, scan_options: ScanOptionsDict) -> None:
        with self._cache_lock:
            self._scan_options = clone_scan_options(scan_options)
            self._invalidate_scan_option_dependent_cache_locked()
    
    def _invalidate_scan_option_dependent_cache_locked(self) -> None:
        for key in _SCAN_OPTION_DEPENDENT_CACHE_KEYS:
            self._cache.pop(key, None)
```

**Invalidation Set** (`_SCAN_OPTION_DEPENDENT_CACHE_KEYS`):
- `"variable_discovery"` — affected by policy context
- `"feature_detector"` — affected by policy context

**Not Invalidated**:
- `"event_bus"` — singleton, no policy input
- `"scanner_context"` — created at runtime with current options
- `"variable_row_builder"` — stateless utility
- `"blocker_fact_builder"` — determined at init

### Why Not Invalidate Scanner Context?

ScannerContext is created via a **runtime seam** (`prepare_scan_context_fn`) that is injected at DIContainer initialization. This function controls the invalidation boundary:

- If `prepare_scan_context_fn` calls `factory_variable_discovery()`, it gets a fresh instance (variable_discovery is invalidated)
- The ScannerContext itself is not invalidated; instead, it remains valid and the factories it calls are refreshed

This design decouples ScannerContext lifecycle from scan_options changes, putting responsibility for invalidation in the seam injection layer.

---

## Deferred Import Strategy

### Why Deferred Imports?

Two services require deferred imports to break circular dependencies:
1. **VariableDiscovery**: `scanner_core.variable_discovery → scanner_extract → di_helpers → di`
2. **FeatureDetector**: `scanner_core.feature_detector → scanner_extract → di_helpers → di`

### Circular Dependency Pattern

```
di.py
  ├─ (imports at module load)
  └─ factory_variable_discovery()
       ├─ (deferred import at first call)
       └─ scanner_core.variable_discovery
            ├─ (imports at module load)
            └─ scanner_extract
                 ├─ (imports at module load)
                 └─ di_helpers
                      └─ (imports di.py → already loaded ✅)
```

By deferring the import to factory method call time, all modules can load in order without circular import errors.

### Implementation: Module-Level Helpers

Two helper functions handle the deferred imports:

```python
def _create_variable_discovery(di, role_path, scan_options):
    from prism.scanner_core.variable_discovery import VariableDiscovery
    return VariableDiscovery(di=di, role_path=role_path, scan_options=scan_options)

def _create_feature_detector(di, role_path, scan_options):
    from prism.scanner_core.feature_detector import FeatureDetector
    return FeatureDetector(di=di, role_path=role_path, scan_options=scan_options)
```

**Why module-level?** These helpers are used by ServiceLocator and can be reused elsewhere if needed. Placing them at module level makes them discoverable and testable.

### Circular Dependency Prevention

**Rules** (enforced by test guards):
1. ServiceLocator methods MUST NOT import VariableDiscovery or FeatureDetector at module load
2. Deferred imports MUST happen inside factory methods
3. Deferred import helpers MUST be at module level (for reusability)
4. scanner_core/di.py MUST NOT import from scanner_extract at module load

**Verification**:
- Ruff/flake8 will catch direct imports (not in TYPE_CHECKING)
- Test suite will catch import-time circular dependencies (ImportError during test discovery)

---

## Relationship to Other Components

### DIContainer (Parent)

ServiceLocator is **owned by** DIContainer:
- Created during `DIContainer.__init__()`
- Stored in `self._service_locator` (not directly exposed)
- Called via DIContainer's delegation methods:
  ```python
  di.factory_variable_discovery()  # delegates to _service_locator
  ```

### PluginResolver (Sibling)

PluginResolver is also extracted from DIContainer but handles **plugin resolution**, not service creation:
- PluginResolver: "Give me the VariableDiscoveryPlugin for this platform"
- ServiceLocator: "Give me the VariableDiscovery service"

They are separate concerns with separate protocols.

### ScannerContext (Consumer)

ScannerContext calls ServiceLocator methods during runtime:
```python
class ScannerContext:
    def __init__(self, di: DIContainer, ...):
        self._di = di
    
    def feature_detector(self) -> FeatureDetector:
        return self._di.factory_feature_detector()
```

### di_helpers (Consumer)

`di_helpers.py` provides typed protocol for DIContainer:
```python
class DIProtocol(Protocol):
    def factory_variable_discovery(self) -> VariableDiscovery: ...
    # etc.
```

This allows code to accept any DIContainer-like object with explicit type checking (no duck typing).

---

## Design Constraints & Trade-Offs

### Constraint 1: Owned by DIContainer
**Decision**: ServiceLocator cannot exist independently; it requires DIContainer's state.  
**Rationale**: Simplifies ownership model, prevents dangling references, eases testing.  
**Trade-off**: Cannot use ServiceLocator outside DIContainer context (by design — not needed).

### Constraint 2: GIL-Based Thread Safety
**Decision**: Rely on Python GIL for atomic dict operations; use RLock only for cache updates.  
**Rationale**: Matches existing DIContainer design, reduces lock contention.  
**Trade-off**: Not suitable for non-CPython implementations (PyPy, Jython) without modification.

### Constraint 3: Fail-Closed Deferred Imports
**Decision**: Deferred imports will raise ImportError if modules unavailable at call time.  
**Rationale**: Better than silent fallbacks; import errors are caught early in tests.  
**Trade-off**: Cannot handle lazy-loading scenarios (not a requirement in prism).

### Constraint 4: No Cache TTL
**Decision**: Cached services live for the container's lifetime.  
**Rationale**: Simplifies design; containers are short-lived (per scan).  
**Trade-off**: Cannot cache services longer/shorter than container lifetime (by design — not needed).

---

## Success Criteria (Verification Plan)

**Protocol Completeness**:
- ✅ All 6 factory methods documented with signatures
- ✅ All mock/override behaviors documented
- ✅ All caching semantics documented
- ✅ All thread safety guarantees documented
- ✅ Mypy --strict validation on ServiceLocatorProtocol

**Deferred Import Correctness**:
- ✅ No import-time circular dependencies
- ✅ Module loads successfully
- ✅ First call to factory_variable_discovery() succeeds
- ✅ First call to factory_feature_detector() succeeds

**Cache Coordination**:
- ✅ replace_scan_options() invalidates variable_discovery cache
- ✅ replace_scan_options() invalidates feature_detector cache
- ✅ replace_scan_options() does NOT invalidate event_bus cache
- ✅ Concurrent calls to same factory return same cached instance

**Thread Safety**:
- ✅ Multiple threads can call factory methods simultaneously
- ✅ No race conditions in cache population
- ✅ Mock injection is thread-safe
- ✅ No deadlocks from nested lock calls

---

## Implementation Readiness

**Stub Code**: service-locator-protocol.py provides full signatures, docstrings, and mock implementations.

**Missing Implementation Details** (for builder phase):
1. Integration with DIContainer (replace 6 methods with delegation)
2. Cache coordination with replace_scan_options()
3. Mock/override orchestration
4. Unit test harness for ServiceLocator
5. Integration test for cache invalidation

**Deliverables Provided**:
1. ✅ ServiceLocatorProtocol (interface definition)
2. ✅ ServiceLocator (stub implementation)
3. ✅ Deferred import helpers (_create_variable_discovery, _create_feature_detector)
4. ✅ Thread safety documentation
5. ✅ Cache coordination specification (separate file)
6. ✅ Deferred import strategy documentation (separate file)

---

## Next Steps (Builder Phase)

1. **Task 2.1**: Extract ServiceLocator implementation to src/prism/scanner_core/service_locator.py
2. **Task 2.2**: Integrate ServiceLocator with DIContainer (replace 6 methods with delegation)
3. **Task 2.3**: Unit test ServiceLocator (80%+ coverage)
4. **Task 2.4**: Integration test cache invalidation with replace_scan_options()
5. **Task 2.5**: Verify thread safety with concurrent factory calls
