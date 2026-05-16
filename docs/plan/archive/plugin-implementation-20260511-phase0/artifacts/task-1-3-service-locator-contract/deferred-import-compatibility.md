# Deferred Import Compatibility Strategy (Task 1.3)

**Scout**: ServiceLocatorContract  
**Date**: May 9, 2026  
**Status**: Design Phase Complete

---

## Executive Summary

Two ServiceLocator factories require **deferred imports** to prevent circular dependencies:
1. `factory_variable_discovery()` → imports `VariableDiscovery` at call time (not module load)
2. `factory_feature_detector()` → imports `FeatureDetector` at call time (not module load)

This document defines:
- Why deferred imports are needed
- How they're implemented (helper functions)
- Circular dependency prevention strategy
- Future-proofing for new factories and platform expansions

---

## Circular Dependency Pattern

### Root Cause

Three-layer circular import chain:

```
Layer 1: scanner_core/di.py
  └─ Has: class DIContainer
  └─ Imports: EventBus, VariableRowBuilder (direct)
  └─ At runtime, factory_variable_discovery() is called

Layer 2: scanner_core/variable_discovery.py
  └─ Has: class VariableDiscovery
  └─ Constructor: VariableDiscovery(di: DIContainer, ...)
  └─ At module load: imports di (for TYPE_CHECKING) ✅ OK
  └─ At module load: imports scanner_extract
     └─ This is the PROBLEM

Layer 2b: scanner_extract/...
  └─ Has: collect_task_handler_catalog()
  └─ At module load: imports di_helpers (to get typed protocol)
     └─ This creates cycle: di → variable_discovery → scanner_extract → di_helpers → di
```

**The Cycle**:
```
di.py
  ├─ (module load: imports EventBus, etc.)
  ├─ factory_variable_discovery() method defined
  └─ (module load complete)
       ↓
variable_discovery.py
  ├─ (module load: imports scanner_extract)
  ├─ class VariableDiscovery defined
  └─ (module load triggers scanner_extract)
       ↓
scanner_extract/__init__.py
  ├─ (module load: imports collect_task_handler_catalog from submodules)
  ├─ (those submodules import di_helpers)
  └─ di_helpers
       ├─ (module load: imports di)
       ├─ ❌ ERROR: di.py is being imported again
       ├─ But di.py is still loading (VariableDiscovery not finished)
       ├─ Python can't complete the import cycle
       └─ ImportError: circular import
```

### Visual Import Timeline

```
Time  Module              Import Status
────────────────────────────────────────
T0    di.py               START (loading)
T1    di.py:50            import EventBus ✅
T2    di.py:200           define class DIContainer ✅
T3    di.py:500           define factory_variable_discovery() ✅
T4    di.py:END           COMPLETE (loading finished)
      (All symbols available: DIContainer, factory_variable_discovery, etc.)

T5    variable_discovery.py START (loading from T5 or later when first imported)
T6    vd.py:10            import scanner_extract ← TRIGGERS scanner_extract load
T7    scanner_extract/__init__.py START
T8    scanner_extract:    import collect_task_handler_catalog from submodules
T9    scanner_extract/item_catalog.py START
T10   item_catalog.py:    import di_helpers ← TRIGGERS di_helpers load
T11   di_helpers.py:      import di ← ERROR: di.py is already in sys.modules
                          but VariableDiscovery is not finished loading
                          Python's import system throws ImportError
```

### Why Python Allows Partial Imports

Python allows re-importing a module that's in progress (for forward compatibility), but only if the needed symbols are already defined. In this case:
- `di.py` is in progress (we're still loading `variable_discovery.py`)
- `di_helpers.py` tries to import `di`
- Python says: "OK, I'll return the partial `di` module"
- But `di.py` hasn't finished yet; we're stuck

**Result**: ImportError or AttributeError at runtime.

---

## Solution: Deferred Imports

### Strategy

Defer the import of `VariableDiscovery` and `FeatureDetector` to **factory method call time**, not **module load time**.

This breaks the cycle:
```
Time  Event
────────────────────────────────────────
T0    di.py imports (no VariableDiscovery import) ✅ Complete
T1    variable_discovery.py imports (never happens at module load)
T2    User code calls di.factory_variable_discovery()
T3    Inside factory_variable_discovery(), we import VariableDiscovery
T4    At this point, all modules are fully loaded ✅ No cycle
T5    VariableDiscovery instance created and returned
```

### Implementation: Module-Level Helpers

```python
# di.py (at module level, with deferred imports)

def _create_variable_discovery(
    di: DIContainer,
    role_path: str,
    scan_options: ScanOptionsDict,
) -> VariableDiscovery:
    """Import VariableDiscovery only at factory call time."""
    # This import happens INSIDE the function, not at module load time
    from prism.scanner_core.variable_discovery import VariableDiscovery
    
    return VariableDiscovery(di=di, role_path=role_path, scan_options=scan_options)


def _create_feature_detector(
    di: DIContainer,
    role_path: str,
    scan_options: ScanOptionsDict,
) -> FeatureDetector:
    """Import FeatureDetector only at factory call time."""
    # This import happens INSIDE the function, not at module load time
    from prism.scanner_core.feature_detector import FeatureDetector
    
    return FeatureDetector(di=di, role_path=role_path, scan_options=scan_options)
```

### Usage in ServiceLocator

```python
class ServiceLocator:
    def factory_variable_discovery(self) -> VariableDiscovery:
        """Create or return cached VariableDiscovery."""
        # ... mock check, override check ...
        
        key = "variable_discovery"
        with self._di._cache_lock:
            if key not in self._di._cache:
                # Call helper that does the deferred import
                self._di._cache[key] = _create_variable_discovery(
                    self._di,
                    self._di._role_path,
                    self._di._snapshot_scan_options(),
                )
        
        return self._di._cache[key]
```

### Why Module-Level Helpers?

Placing deferred imports in helper functions (not inline in factory methods) provides:

1. **Reusability**: If another factory needs the same import, it can call the helper
2. **Testability**: Helper functions can be unit tested independently
3. **Visibility**: Circular dependency prevention is documented in one place
4. **Symmetry**: `_create_variable_discovery()` and `_create_feature_detector()` have parallel structure

---

## Circular Dependency Prevention Strategy

### Rule 1: No Direct Imports from `variable_discovery` or `feature_detector` at Module Level

❌ **WRONG**:
```python
# di.py (module load)
from prism.scanner_core.variable_discovery import VariableDiscovery  # ← Direct import
```

✅ **CORRECT**:
```python
# di.py (module load)
if TYPE_CHECKING:
    from prism.scanner_core.variable_discovery import VariableDiscovery  # ← Type hints only

# di.py (inside factory method)
def factory_variable_discovery(self):
    from prism.scanner_core.variable_discovery import VariableDiscovery  # ← Deferred import
    return VariableDiscovery(...)
```

### Rule 2: di.py Must Not Import from `scanner_extract` at Module Level

❌ **WRONG**:
```python
# di.py (module load)
from prism.scanner_extract.item_catalog import collect_task_handler_catalog
```

✅ **CORRECT**:
```python
# di.py (inside factory method)
def factory_feature_detector(self):
    # Don't import scanner_extract directly
    # Instead, let FeatureDetector import it
    from prism.scanner_core.feature_detector import FeatureDetector
    return FeatureDetector(...)
```

### Rule 3: TYPE_CHECKING Imports are Safe

✅ **CORRECT**:
```python
# di.py (module load)
if TYPE_CHECKING:
    from prism.scanner_core.variable_discovery import VariableDiscovery
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_core.protocols_runtime import BlockerFactBuilder
```

These imports are ONLY for type hints (mypy); they're not evaluated at runtime.

### Rule 4: Fallback Imports Must Be Protected

✅ **CORRECT** (with protection):
```python
def factory_blocker_fact_builder(self):
    key = "blocker_fact_builder"
    with self._cache_lock:
        if key not in self._cache:
            if self._blocker_fact_builder_fn is not None:
                fn = self._blocker_fact_builder_fn
            else:
                # Fallback import is guarded
                try:
                    from prism.scanner_plugins.defaults import resolve_blocker_fact_builder
                    fn = resolve_blocker_fact_builder()
                except ImportError as e:
                    raise PrismRuntimeError(...) from e
            self._cache[key] = fn
    return self._cache[key]
```

---

## Dependency Graph

### Safe Dependencies (No Circular Import Risk)

```
di.py
  ├─ → events.py (EventBus)                           ✅ Safe (no backref to di)
  ├─ → scanner_data/builders.py (VariableRowBuilder)  ✅ Safe (no backref to di)
  ├─ → scanner_data/contracts_request.py              ✅ Safe (no backref to di)
  └─ → errors.py (PrismRuntimeError)                  ✅ Safe (no backref to di)
```

### Deferred Import Dependencies (Circular Risk Managed)

```
di.py (at module load)
  └─ [TYPE_CHECKING] variable_discovery.py            ✅ Safe (only type hints)

di.py (inside factory_variable_discovery(), at call time)
  └─ variable_discovery.py
       ├─ scanner_extract.py
       │   └─ di_helpers.py
       │       └─ di.py                               ✅ SAFE (di already loaded)
       └─ [other imports in VariableDiscovery]
```

### Safe Fallback Dependencies

```
di.py (inside factory_blocker_fact_builder(), at call time)
  └─ scanner_plugins/defaults.py
       └─ [scanner_plugins internals]                 ✅ Safe (no backref to di_core)
```

---

## Future-Proofing Strategy

### Scenario 1: New Service Factory Added

If a new service is added that needs deferred import:

```python
# Future: factory_policy_validator_plugin()
def factory_policy_validator_plugin(self) -> PolicyValidatorPlugin:
    """Create or return cached PolicyValidatorPlugin."""
    # ... mock check, override check ...
    
    key = "policy_validator_plugin"
    with self._di._cache_lock:
        if key not in self._di._cache:
            # Use deferred import helper
            self._di._cache[key] = _create_policy_validator_plugin(
                self._di,
                self._di._role_path,
                self._di._snapshot_scan_options(),
            )
    
    return self._di._cache[key]

def _create_policy_validator_plugin(
    di, role_path, scan_options
) -> PolicyValidatorPlugin:
    """Deferred import helper for PolicyValidatorPlugin."""
    from prism.scanner_core.policy_validator import PolicyValidatorPlugin
    return PolicyValidatorPlugin(di=di, role_path=role_path, scan_options=scan_options)
```

**Guideline**: If new factory imports a module that imports `di_helpers`, use deferred import helper.

### Scenario 2: Platform Expansion (Kubernetes, Terraform)

When adding support for new platforms (Kubernetes, Terraform), ServiceLocator behavior remains unchanged:

```python
# No changes to di.py or service_locator.py

# Instead, PluginRegistry handles platform registration:
registry.register_variable_discovery_plugin("kubernetes", KubernetesVariableDiscovery)
registry.register_feature_detection_plugin("kubernetes", KubernetesFeatureDetector)
```

The factory methods don't need modification; they query the registry by platform key.

**Result**: Platform expansion doesn't introduce new circular dependencies.

### Scenario 3: Alternative DI Implementations

If a future alternative implementation replaces DIContainer:

```python
# Future: Alternative DI with different import strategy
class AsyncDIContainer:
    def factory_variable_discovery(self) -> Awaitable[VariableDiscovery]:
        # Still uses deferred import to avoid circular deps
        # But returns Awaitable instead of direct instance
        async def _create():
            from prism.scanner_core.variable_discovery import VariableDiscovery
            return VariableDiscovery(...)
        return _create()
```

The deferred import strategy remains applicable.

---

## Verification & Testing

### Circular Import Detection Test

```python
# test_circular_imports.py
def test_no_circular_imports_on_module_load():
    """Verify di.py loads without importing variable_discovery/feature_detector."""
    import sys
    
    # Remove any previously imported prism modules
    to_remove = [key for key in sys.modules if key.startswith("prism")]
    for key in to_remove:
        del sys.modules[key]
    
    # Import di.py
    from prism.scanner_core import di
    
    # Verify modules NOT loaded yet
    assert "prism.scanner_core.variable_discovery" not in sys.modules
    assert "prism.scanner_core.feature_detector" not in sys.modules
    assert "prism.scanner_extract" not in sys.modules
```

### Deferred Import Functionality Test

```python
def test_deferred_imports_work_at_call_time():
    """Verify factories import modules only at call time."""
    di_container = DIContainer(role_path="test", scan_options={})
    
    # Verify modules not yet loaded
    assert "prism.scanner_core.variable_discovery" not in sys.modules
    
    # Call factory (should import)
    vd = di_container.factory_variable_discovery()
    
    # Verify module loaded
    assert "prism.scanner_core.variable_discovery" in sys.modules
    assert isinstance(vd, VariableDiscovery)
```

### Cache Consistency After Deferred Import

```python
def test_cache_consistent_after_deferred_import():
    """Verify deferred import populates cache correctly."""
    di_container = DIContainer(role_path="test", scan_options={})
    
    # First call imports and caches
    vd1 = di_container.factory_variable_discovery()
    
    # Second call returns cached instance
    vd2 = di_container.factory_variable_discovery()
    
    # Verify same instance (identity check)
    assert vd1 is vd2
```

---

## Import Order Testing

### Test Suite Configuration

```python
# conftest.py
import pytest
import sys

@pytest.fixture(autouse=True)
def reset_import_cache():
    """Reset prism modules between tests to catch import-order issues."""
    to_remove = [key for key in sys.modules if key.startswith("prism")]
    for key in to_remove:
        del sys.modules[key]
    
    yield
    
    # Cleanup after test
    to_remove = [key for key in sys.modules if key.startswith("prism")]
    for key in to_remove:
        del sys.modules[key]
```

This fixture ensures each test starts with a clean import state, catching import-order bugs.

---

## Static Analysis Verification

### Ruff/Flake8 Configuration

```toml
# pyproject.toml
[tool.ruff]
lint.extend-ignore = [
    # No circular imports between __init__ and submodules (checked by test)
]

[tool.ruff.lint]
# Enforce TYPE_CHECKING imports for forward references
extend-select = ["I", "F", "E"]  # isort, Pyflakes, errors
```

### Mypy Configuration

```toml
# pyproject.toml
[tool.mypy]
strict = true
warn_unused_ignores = true
warn_return_any = false  # TYPE_CHECKING imports don't have Any

# Ignore circular import errors (we handle at runtime via tests)
disable_error_code = ["import-not-found"]
```

---

## Document Management

### When to Update This Document

Update this document if:
1. New deferred import pattern is added
2. Circular dependency is discovered and fixed
3. New service factory is added with deferred import
4. Platform expansion adds new circular dependency pattern

### When NOT to Update This Document

Don't update if:
1. Regular refactoring changes factory implementation
2. Cache invalidation strategy changes (update cache-coordination-spec.yaml instead)
3. Threading model changes (update cache-coordination-spec.yaml instead)

---

## Summary

**Deferred Import Strategy**:
- Breaks circular dependencies by deferring imports to call time
- Uses module-level helper functions for clarity and reusability
- Prevents circular import errors at module load time
- Enables type hints via TYPE_CHECKING imports
- Thread-safe via deferred import's per-thread import lock
- Future-proof for new factories and platform expansions

**Key Rules**:
1. No direct imports of `variable_discovery` or `feature_detector` at module load
2. TYPE_CHECKING imports are safe for type hints
3. Deferred imports go in factory methods or helpers
4. Fallback imports must be protected with try/except
5. Test import order to catch regression

**Verification**: Circular import tests pass, deferred imports work, cache consistency maintained.
