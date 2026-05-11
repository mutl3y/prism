# PolicyManager Architecture (Wave 4 Frozen)

**Status**: FROZEN (Phase 2 Wave 4 consolidation complete)  
**Last Updated**: 2026-05-09  
**Version**: 2.0 (Wave 4 consolidation locked)

## Overview

The PolicyManager architecture is now **frozen** after Phase 2 Wave 4 consolidation. This document defines the canonical entry points, resolution flow, caching strategy, constraints, and extension points for future waves.

---

## Canonical Entry Point Flow

All policy access routes through this 5-point entry flow:

```text
1. Entry Point
   ↓
   Use di.policy_manager property (preferred)
   OR ensure_policy_manager(di) module function
   OR di.factory_policy_manager() (legacy, still supported)
   ↓
2. DIContainer Routing
   Requests routed through DIContainer._cache_lock (thread-safe)
   ↓
3. First Access: Lazy Initialization
   If NOT in _cache:
     Create PolicyManager(registry=di.policy_registry)
     Store in _cache["policy_manager"]
   ↓
4. Registry Bootstrap
   FallbackPolicyRegistry lazily initializes on first access
   Registry loads 6 policy factories (Ansible + future platforms)
   Stored in _cache["policy_registry"]
   ↓
5. Resolution
   PolicyManager.resolve_prepared_bundle() delegates to FallbackPolicyRegistry
   Registry returns complete PreparedPolicyBundle with all 6 policy types
```

### Entry Points (All Valid, Ordered by Preference)

#### Tier 1: Property Access (Preferred)

```python
manager = di.policy_manager           # Cleanest, recommended
registry = di.policy_registry
```

#### Tier 2: Module-Level Functions (Backward Compat)

```python
from prism.scanner_core.di import ensure_policy_manager, ensure_policy_registry
manager = ensure_policy_manager(di)   # Explicit delegation
registry = ensure_policy_registry(di)
```

#### Tier 3: Legacy Factory Methods (Still Supported)

```python
manager = di.factory_policy_manager()   # Legacy, still works
registry = di.factory_policy_registry()
```

### Caching Strategy (Lazy, Per-Container)

- **Initialization**: Lazy (on first access)
- **Scope**: Per-DIContainer instance
- **Duration**: Lifetime of container (cleared only via `di.clear_cache()`)
- **Thread Safety**: Guarded by `di._cache_lock` (threading.RLock)
- **Isolation**: Each DIContainer has independent cache

```python
# First call: Creates instance
manager1 = di.policy_manager
# Subsequent calls: Returns cached instance
manager2 = di.policy_manager
assert manager1 is manager2  # Same object

# After cache clear: New instance
di.clear_cache()
manager3 = di.policy_manager
assert manager3 is not manager1  # Different object
```

---

## Architectural Constraints (Frozen)
# 1. Single Source of Truth

These constraints define the locked architecture. Changes require ADR and approval.

### 1. Single Source of Truth
- **Policy Manager**: All policy access routes through `PolicyManager.resolve_prepared_bundle()`
- **Policy Registry**: Single `FallbackPolicyRegistry` per container
- **No Direct Instantiation**: Never create policies outside registry
- **Fail-Closed**: Missing policies raise `ValueError`, never silent fallback

```python
# ✅ CORRECT: Via manager
bundle = di.policy_manager.resolve_prepared_bundle(scan_options=opts)

# ❌ WRONG: Direct instantiation outside manager
fro# 2. Registry Immutability After Initialization
llbackPolicyRegistry
registry = FallbackPolicyRegistry()  # Wrong: should use di.policy_registry
```

### 2. Registry Immutability After Initialization
- **No Runtime Registration**: Policies registered at initialization time only
- **No Mutation After Startup**: Registry state frozen after container creation
- **Idempotent Bootstrap**: Multiple accesses safe, always return same instance

```python
# ✅ Initialization time (OK)
registry = di.policy_registry
registry.register_policy("task_line_parsing", {...})

# ❌# 3. All Policy Resolution Through Manager
nstraint)
# In runtime code:
# registry.register_policy(...)  # ERROR: Violates frozen architecture
```

### 3. All Policy Resolution Through Manager
- **6 Policy Types**: task_line_parsing, task_annotation, task_traversal, variable_extractor, yaml_parsing, jinja_analysis
- **One Entry Point**: `PolicyManager.resolve_prepared_bundle()`
- **No Bypass Paths**: No direct access to individual policies from registry

```python
# ✅# 4. Factory Overrides Set Once
 all policies
manager = di.policy_manager
bundle = manager.resolve_prepared_bundle(scan_options=opts)
task_line_policy = bundle.task_line_parsing_policy
```

### 4. Factory Overrides Set Once
- **Initialization Parameter**: Passed at DIContainer creation
- **No Runtime Changes**: Factory overrides immutable after init
- **Precedence**: Overrides > Registry > Factory Defaults

```python
# ✅ Setup time: Override provided at DIContainer init
di = DIContainer(
    "role",
    scan_opts,
    factory_overrides={"policy_manager_factory": custom_factory}
)

# ❌ Runtime: Cannot change overrides
# di._factory_overrides["..."] = ...  # ERROR: Frozen architecture
```

---


**Location**: `FallbackPolicyRegistry._bootstrap_resolvers()`

**Contract**:

These extension points are reserved for future waves. They define hooks where new behavior can be plugged in without violating frozen constraints.

### 1. Plugin Registry Integration (Wave 5)

**Purpose**: Load policies from external plugins  
**Location**: `FallbackPolicyRegistry._bootstrap_resolvers()`  
**Contract**:
- Registry bootstraps resolvers from PluginRegistry
- Each platform (Ansible, Kubernetes, Terraform) registers factory
- Factories return `PreparedPolicy` objects matching contracts

```python
# Wave 5+ usage (not yet implemented)
registry = di.policy_registry

**Location**: `DIContainer._cache` and `PolicyManager._cache`

**Contract**:
pe="task_line_parsing",
    platform_key="kubernetes",
    factory_fn=lambda: {...}
)
```

### 2. Caching Strategy Pluggability (Wave 5)

**Purpose**: Allow custom cache implementations  
**Location**: `DIContainer._cache` and `PolicyManager._cache`  
**Contract**:
- Cache implements dict-like interface (get, set, delete, clear)
- Thread-safe (caller manages locking)
- Per-container or shared (configurable)


**Location**: `PolicyManager` or `FallbackPolicyRegistry`

**Contract**:
ign (not yet implemented)
class CustomCache:
    def __getitem__(self, key): ...
    def __setitem__(self, key, value): ...
    def clear(self): ...

di = DIContainer(..., cache_backend=CustomCache())
```

### 3. Policy Validation Hooks (Wave 5)

**Purpose**: Custom validation before policies are used  
**Location**: `PolicyManager` or `FallbackPolicyRegistry`  
**Contract**:

**Location**: `FallbackPolicyRegistry._resolvers` dict

**Contract**:
ng `resolve_prepared_bundle()` before returning
- Can transform or reject policies

```python
# Wave 5+ design (not yet implemented)
def validate_ansible_policies(policies):
    # Custom validation logic
    return policies

registry.register_validator("ansible", validate_ansible_policies)
```

### 4. Platform Expansion (Wave 5+)

**Purpose**: Support new platforms (Kubernetes, Terraform, etc.)  
**Location**: `FallbackPolicyRegistry._resolvers` dict  
**Contract**:
- New platform key (e.g., "kubernetes", "terraform")
- 6 policy resolvers per platform
- Same policy contracts as Ansible

```python
# Wave 5+ design (not yet implemented)
# Kubernetes platform registration
registry.register_resolver("task_line_parsing", "kubernetes", k8s_task_line_factory)
registry.register_resolver("task_annotation", "kubernetes", k8s_annotation_factory)
# ... 4 more resolvers for kubernetes
```

---

## Configuration Points

### DIContainer Initialization

```python
from prism.scanner_data.contracts_request import ScanOptionsDict

scan_options: ScanOptionsDict = {
    "platform": "ansible",  # or "kubernetes", "terraform", etc.
    "scan_pipeline_plugin": "ansible",
    "policy_context": {
        "selection": {
            "plugin": "ansible"
        }
    }
}

di = DIContainer(
    role_path="my_role",
    scan_options=scan_options,
    # Optional:
    platform_key="ansible",  # Explicit override
    factory_overrides={...},  # Custom factories
    registry=custom_registry,  # Custom plugin registry
)
```

### Accessing PolicyManager and Registry

```python
# Preferred: Properties
manager = di.policy_manager
registry = di.policy_registry

# Or: Module functions
from prism.scanner_core.di import ensure_policy_manager, ensure_policy_registry
manager = ensure_policy_manager(di)
registry = ensure_policy_registry(di)

# Or: Legacy factories
manager = di.factory_policy_manager()
registry = di.factory_policy_registry()
```

### Resolving Policies

```python
# Get prepared policy bundle
bundle = manager.resolve_prepared_bundle(scan_options=di.scan_options)

# Access individual policies
task_line_policy = bundle.task_line_parsing_policy
task_annotation_policy = bundle.task_annotation_policy
task_traversal_policy = bundle.task_traversal_policy
variable_extractor_policy = bundle.variable_extractor_policy
yaml_parsing_policy = bundle.yaml_parsing_policy
jinja_analysis_policy = bundle.jinja_analysis_policy
```

---

## Thread Safety Guarantees

### Caching (Thread-Safe)

- **Lock Type**: `threading.RLock` (reentrant lock)
- **Protected**: `di._cache` dictionary and `PolicyManager._cache`
- **Granularity**: Per-container (separate lock per DIContainer)
- **Behavior**: Multiple threads accessing same cache get same instance

```python
import threading

di = DIContainer("role", {})

# Thread-safe: Multiple threads get same manager
managers = []
def get_manager():
    managers.append(di.policy_manager)

threads = [threading.Thread(target=get_manager) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()

# All managers are identical (same object)
assert all(m is managers[0] for m in managers)
```

### Registry Bootstrap (Idempotent)

- **Multiple Calls**: Safe to call registry factory multiple times
- **Same Instance**: Always returns cached instance
- **Bootstrap Once**: Resolver initialization happens once

---

## Testing and Validation

### Key Test Classes

| Test Class | Purpose | Count |
|-----------|---------|-------|
| `TestWave4DIConsolidation` | Factory/property delegation, caching | 6 |
| `TestWave4ArchitectureLock` | Immutability, constraints, thread safety | 6 |
| `TestWave4ExtensionPoints` | Extension point existence and API | 7 |
| `TestWave4FullIntegration` | End-to-end scenarios | 8 |
| `TestWave4MigrationValidation` | Backward compatibility | 12 |

**Total**: 39 tests validating Wave 4 architecture

### Validation Gates

```bash
# All tests must pass together:
pytest tests/test_policy_manager.py -xvs

# Type checking (mypy strict)
mypy --strict src/prism/scanner_core/di.py
mypy --strict src/prism/scanner_core/policy_manager.py
mypy --strict src/prism/scanner_core/policy_registry.py

# Linting
ruff check src/prism/scanner_core/di*.py
black --check src/prism/scanner_core/di*.py
```

---

## Migration Guide

### For New Code (Wave 4+)

**Use Properties**:
```python
# ✅ New code: Use properties
manager = di.policy_manager
registry = di.policy_registry
```

### For Existing Code

**No Changes Required** - Full backward compatibility:
```python
# ✅ Old factory methods still work
manager = di.factory_policy_manager()
registry = di.factory_policy_registry()

# ✅ Old module-level functions still work (if used)
from prism.scanner_core.di_helpers import resolve_policy_manager
# ... old code continues to work
```

---

## Known Limitations & Future Work

### Current (Wave 4)

- ✅ Single platform (Ansible) fully supported
- ✅ 6 policy types fully coordinated
- ✅ Thread-safe caching
- ✅ 100% backward compatible

### Wave 5+ (Not Implemented)

- 🔲 Plugin-based policy resolution (blocked by plugin architecture)
- 🔲 Custom caching backends (blocked by cache pluggability)
- 🔲 Policy validation hooks (blocked by validation architecture)
- 🔲 Multi-platform support (Kubernetes, Terraform)
- 🔲 Dynamic policy registration at runtime

**Extension points are documented above for Wave 5 implementation.**

---

## Related Documents

- [DIContainer API Documentation](../src/prism/scanner_core/di.py)
- [PolicyManager API Documentation](../src/prism/scanner_core/policy_manager.py)
- [FallbackPolicyRegistry Documentation](../src/prism/scanner_core/policy_registry.py)
- [Test Suite](../tests/test_policy_manager.py)
- [Phase 2 Wave 4 Plan](plan/phase-2-wave-4-consolidation.yaml) *(if exists)*

---

## Change History

| Version | Date | Change | Wave |
|---------|------|--------|------|
| 2.0 | 2026-05-09 | Architecture frozen, consolidation complete | 4 |
| 1.0 | 2026-05-08 | Initial property/factory pattern | 3 |
| 0.1 | 2026-05-01 | Stub implementation | 0-2 |

**Frozen After Wave 4**: Future architectural changes require Architecture Decision Record (ADR) and review.
