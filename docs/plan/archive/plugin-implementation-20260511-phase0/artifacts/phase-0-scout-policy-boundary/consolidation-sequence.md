# PolicyManager Consolidation: Implementation Sequence

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-0-scout-policy-boundary  
**Created**: 2026-05-09  
**Status**: SEQUENCING COMPLETE

---

## Executive Summary

This document provides a step-by-step implementation sequence for the PolicyManager consolidation, broken into 7 implementation waves with clear dependencies and validation gates.

**Total Scope**: ~8 person-days  
**Validation Gates**: 7 (one per wave)  
**Risk Level**: LOW (isolated refactoring, backward compatible)  

---

## Wave 0: Preparation (0.5 days)

### Task 0.1: Create directory structure

Create all new modules (no implementation yet):

```bash
# Create new modules (empty files with module docstrings)
touch src/prism/scanner_plugins/fallback_registry.py
touch src/prism/scanner_plugins/policy_manager.py
touch src/prism/scanner_config/policy_loader.py

# Create test fixtures
touch tests/scanner_plugins/test_fallback_registry.py
touch tests/scanner_plugins/test_policy_manager.py
touch tests/scanner_config/test_policy_loader.py
```

**Validation**:
- All files exist and are importable
- No syntax errors

### Task 0.2: Extract type definitions

Move protocol definitions from contracts_request.py to new locations (if needed):

```python
# scanner_plugins/policy_manager.py (imports from contracts_request)
from scanner_data.contracts_request import (
    PreparedTaskLineParsingPolicy,
    PreparedJinjaAnalysisPolicy,
    PreparedTaskTraversalPolicy,
    PreparedTaskAnnotationPolicy,
    PreparedYAMLParsingPolicy,
    PreparedVariableExtractorPolicy,
    PreparedPolicyBundle,
)
```

**Validation**:
- Protocols importable from policy_manager module
- No circular imports

---

## Wave 1: FallbackPolicyRegistry (1 day)

### Task 1.1: Implement FallbackPolicyRegistry class

**File**: `src/prism/scanner_plugins/fallback_registry.py`

**Implementation**:

```python
import threading
from typing import Any

class FallbackPolicyRegistry:
    """Centralized registry for fallback policies."""
    
    def __init__(self) -> None:
        self._fallbacks: dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def register_fallback(self, policy_kind: str, plugin: Any) -> None:
        """Register a fallback policy instance."""
        if plugin is None:
            raise TypeError("Cannot register None as fallback policy")
        
        with self._lock:
            if policy_kind in self._fallbacks:
                raise ValueError(f"Fallback for {policy_kind!r} already registered")
            self._fallbacks[policy_kind] = plugin
    
    def get_fallback(self, policy_kind: str) -> Any | None:
        """Retrieve registered fallback policy."""
        with self._lock:
            return self._fallbacks.get(policy_kind)
    
    def get_all_fallbacks(self) -> dict[str, Any]:
        """Return snapshot of all registered fallbacks."""
        with self._lock:
            return dict(self._fallbacks)
    
    def has_fallback(self, policy_kind: str) -> bool:
        """Check if policy kind is registered."""
        with self._lock:
            return policy_kind in self._fallbacks
    
    def unregister_fallback(self, policy_kind: str) -> None:
        """Unregister a fallback policy (testing only)."""
        with self._lock:
            if policy_kind in self._fallbacks:
                del self._fallbacks[policy_kind]
```

**Tests**: `tests/scanner_plugins/test_fallback_registry.py`

- Test registration and retrieval
- Test thread safety
- Test duplicate registration error
- Test None registration error

**Validation Gate 1.1**:
```bash
pytest tests/scanner_plugins/test_fallback_registry.py -v
# Expected: All 6 tests pass, 0 warnings
```

### Task 1.2: Create initialize_fallback_registry() bootstrap function

**File**: `src/prism/scanner_plugins/bootstrap.py` (or new file)

**Implementation**:

```python
def initialize_fallback_registry() -> FallbackPolicyRegistry:
    """Create and populate default fallback registry."""
    from scanner_plugins.ansible.default_policies import (
        AnsibleDefaultTaskLineParsingPolicyPlugin,
        AnsibleDefaultTaskAnnotationPolicyPlugin,
        AnsibleDefaultTaskTraversalPolicyPlugin,
        AnsibleDefaultVariableExtractorPolicyPlugin,
    )
    from scanner_plugins.parsers.yaml import DefaultYAMLParsingPolicyPlugin
    from scanner_plugins.parsers.jinja import DefaultJinjaAnalysisPolicyPlugin
    
    registry = FallbackPolicyRegistry()
    
    # Register Ansible defaults
    registry.register_fallback(
        "task_line_parsing",
        AnsibleDefaultTaskLineParsingPolicyPlugin()
    )
    registry.register_fallback(
        "task_annotation_parsing",
        AnsibleDefaultTaskAnnotationPolicyPlugin()
    )
    registry.register_fallback(
        "task_traversal",
        AnsibleDefaultTaskTraversalPolicyPlugin()
    )
    registry.register_fallback(
        "variable_extractor",
        AnsibleDefaultVariableExtractorPolicyPlugin()
    )
    
    # Register generic parser defaults
    registry.register_fallback("yaml_parsing", DefaultYAMLParsingPolicyPlugin())
    registry.register_fallback("jinja_analysis", DefaultJinjaAnalysisPolicyPlugin())
    
    return registry
```

**Tests**: Test bootstrap creates registry with 6 policies registered

**Validation Gate 1.2**:
```bash
python -c "from scanner_plugins.bootstrap import initialize_fallback_registry; r = initialize_fallback_registry(); assert r.has_fallback('task_line_parsing'); print('✓ Bootstrap successful')"
```

### Task 1.3: Store FallbackPolicyRegistry in DIContainer

**File**: `src/prism/scanner_core/di.py`

**Implementation**:

```python
@dataclass
class DIContainer:
    # ... existing fields ...
    fallback_policy_registry: FallbackPolicyRegistry
    
    @classmethod
    def default(cls) -> "DIContainer":
        """Create default DIContainer with bootstrapped components."""
        fallback_registry = initialize_fallback_registry()
        return cls(
            # ... existing fields ...
            fallback_policy_registry=fallback_registry,
        )
```

**Validation Gate 1.3**:
```bash
pytest tests/scanner_core/test_di.py -k "fallback_policy_registry" -v
```

---

## Wave 2: PolicyManager Implementation (2 days)

### Task 2.1: Implement PolicyManager class

**File**: `src/prism/scanner_plugins/policy_manager.py`

**Implementation**: (stub shown; full implementation in interface spec)

```python
class PolicyManager:
    """Unified facade for policy resolution."""
    
    def __init__(
        self,
        fallback_registry: FallbackPolicyRegistry,
        plugin_registry: Any | None = None,
        di: Any | None = None,
    ) -> None:
        self._fallback_registry = fallback_registry
        self._plugin_registry = plugin_registry
        self._di = di
        self._resolved_cache: dict[str, Any] = {}
    
    def _call_factory_override(self, factory_name: str) -> Any | None:
        """Call DI factory override if available."""
        if not self._di or not hasattr(self._di, factory_name):
            return None
        try:
            factory_fn = getattr(self._di, factory_name)
            return factory_fn()
        except Exception as e:
            raise PolicyResolutionError(
                f"DI factory {factory_name} failed: {e}"
            ) from e
    
    def resolve(self, policy_kind: str) -> Any:
        """Resolve policy by kind."""
        # Check cache
        if policy_kind in self._resolved_cache:
            return self._resolved_cache[policy_kind]
        
        # Check DI factory
        factory_name = f"factory_{policy_kind}_policy_plugin"
        factory_result = self._call_factory_override(factory_name)
        if factory_result is not None:
            self._resolved_cache[policy_kind] = factory_result
            return factory_result
        
        # Check registry
        if self._plugin_registry and hasattr(self._plugin_registry, "get_plugin"):
            plugin = self._plugin_registry.get_plugin(policy_kind)
            if plugin is not None:
                self._resolved_cache[policy_kind] = plugin
                return plugin
        
        # Check fallback
        fallback = self._fallback_registry.get_fallback(policy_kind)
        if fallback is not None:
            self._resolved_cache[policy_kind] = fallback
            return fallback
        
        raise MissingPolicyError(policy_kind)
    
    def resolve_task_line_parsing_policy(self) -> Any:
        return self.resolve("task_line_parsing")
    
    def resolve_jinja_analysis_policy(self) -> Any:
        return self.resolve("jinja_analysis")
    
    def resolve_task_traversal_policy(self) -> Any:
        return self.resolve("task_traversal")
    
    def resolve_task_annotation_parsing_policy(self) -> Any:
        return self.resolve("task_annotation_parsing")
    
    def resolve_yaml_parsing_policy(self) -> Any:
        return self.resolve("yaml_parsing")
    
    def resolve_variable_extractor_policy(self) -> Any:
        return self.resolve("variable_extractor")
    
    def resolve_prepared_policy_bundle(self) -> PreparedPolicyBundle:
        """Resolve all policies into bundle."""
        return {
            "task_line_parsing": self.resolve_task_line_parsing_policy(),
            "jinja_analysis": self.resolve_jinja_analysis_policy(),
            "task_traversal": self.resolve_task_traversal_policy(),
            "yaml_parsing": self.resolve_yaml_parsing_policy(),
            "variable_extractor": self.resolve_variable_extractor_policy(),
            "task_annotation_parsing": self.resolve_task_annotation_parsing_policy(),
        }
    
    def clear_cache(self) -> None:
        """Clear resolution cache."""
        self._resolved_cache.clear()
```

**Tests**: `tests/scanner_plugins/test_policy_manager.py`

- Test resolution chain (DI → registry → fallback)
- Test cache behavior
- Test MissingPolicyError on not found
- Test each resolve_*() method

**Validation Gate 2.1**:
```bash
pytest tests/scanner_plugins/test_policy_manager.py -v
# Expected: 15+ tests pass
```

### Task 2.2: Add PolicyManager to DIContainer

**File**: `src/prism/scanner_core/di.py`

**Implementation**:

```python
@dataclass
class DIContainer:
    # ... existing fields ...
    fallback_policy_registry: FallbackPolicyRegistry
    policy_manager: PolicyManager
    
    @classmethod
    def default(cls) -> "DIContainer":
        """Create default DIContainer."""
        fallback_registry = initialize_fallback_registry()
        manager = PolicyManager(
            fallback_registry=fallback_registry,
        )
        return cls(
            # ... existing fields ...
            fallback_policy_registry=fallback_registry,
            policy_manager=manager,
        )
```

**Validation Gate 2.2**:
```bash
pytest tests/scanner_core/test_di.py::test_di_container_has_policy_manager -v
```

### Task 2.3: Test resolution flow end-to-end

**File**: `tests/integration/test_policy_resolution_flow.py`

**Tests**:

1. Test resolution through full chain
2. Test caching prevents repeated resolution
3. Test DI factory override
4. Test plugin registry lookup
5. Test fallback as final resort

**Validation Gate 2.3**:
```bash
pytest tests/integration/test_policy_resolution_flow.py -v
# Expected: All 5 tests pass
```

---

## Wave 3: ConfigPolicyLoader (1.5 days)

### Task 3.1: Implement PolicyConfigSpec and ConfigPolicyLoader

**File**: `src/prism/scanner_config/policy_loader.py`

**Implementation**:

```python
from dataclasses import dataclass

@dataclass
class PolicyConfigSpec:
    config_key: str
    python_type: type
    default_value: Any
    coerce_fn: Callable[[Any], Any]
    description: str
    required: bool = False


class ConfigPolicyLoader:
    """Unified loader for policy configuration."""
    
    POLICY_CONFIG_SPECS: dict[str, PolicyConfigSpec] = {
        "fail_on_unconstrained": PolicyConfigSpec(
            config_key="policy_context.dynamic_includes.fail_on_unconstrained",
            python_type=bool,
            default_value=False,
            coerce_fn=_coerce_bool,
            description="Fail if unconstrained dynamic includes detected",
        ),
        "fail_on_yaml_like": PolicyConfigSpec(
            config_key="policy_context.annotations.fail_on_yaml_like",
            python_type=bool,
            default_value=False,
            coerce_fn=_coerce_bool,
            description="Fail if YAML-like annotations detected",
        ),
        "include_underscore_prefixed": PolicyConfigSpec(
            config_key="policy_context.references.include_underscore_prefixed",
            python_type=bool,
            default_value=False,
            coerce_fn=_coerce_bool,
            description="Include underscore-prefixed references",
        ),
        "marker_prefix": PolicyConfigSpec(
            config_key="comment_doc_marker_prefix",
            python_type=str,
            default_value="@prism",
            coerce_fn=str,
            description="Comment marker prefix for task annotations",
        ),
    }
    
    def __init__(self, config_dict: dict[str, Any] | None = None):
        self._config_dict = config_dict or {}
    
    def load_all(self) -> dict[str, Any]:
        """Load all policy config parameters."""
        result = {}
        for key, spec in self.POLICY_CONFIG_SPECS.items():
            result[key] = self.load_by_key(key)
        return result
    
    def load_by_key(self, key: str) -> Any:
        """Load single config by key."""
        if key not in self.POLICY_CONFIG_SPECS:
            raise KeyError(f"Unknown policy config key: {key!r}")
        
        spec = self.POLICY_CONFIG_SPECS[key]
        value = self._get_nested(self._config_dict, spec.config_key.split("."))
        
        if value is None:
            if spec.required:
                raise ValueError(f"Required config {key!r} not found")
            return spec.default_value
        
        return spec.coerce_fn(value)
    
    @staticmethod
    def _get_nested(d: dict, keys: list[str]) -> Any | None:
        """Get nested dict value safely."""
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key)
            else:
                return None
        return d
    
    @classmethod
    def get_schema(cls) -> dict[str, PolicyConfigSpec]:
        """Return config schema."""
        return cls.POLICY_CONFIG_SPECS.copy()
```

**Tests**: `tests/scanner_config/test_policy_loader.py`

- Test loading all configs
- Test loading by key
- Test defaults when missing
- Test coercion functions
- Test required field enforcement

**Validation Gate 3.1**:
```bash
pytest tests/scanner_config/test_policy_loader.py -v
```

### Task 3.2: Integrate ConfigPolicyLoader into PolicyManager

**File**: Update `src/prism/scanner_plugins/policy_manager.py`

**Implementation**: Add metadata handling to `resolve_prepared_policy_bundle()`

```python
def resolve_prepared_policy_bundle(
    self,
    config_loader: ConfigPolicyLoader | None = None,
) -> PreparedPolicyBundle:
    """Resolve all policies with config metadata."""
    bundle = {
        "task_line_parsing": self.resolve_task_line_parsing_policy(),
        "jinja_analysis": self.resolve_jinja_analysis_policy(),
        # ... other policies ...
    }
    
    if config_loader:
        bundle["comment_doc_marker_prefix"] = config_loader.load_by_key("marker_prefix")
        bundle["ignore_unresolved_internal_underscore_references"] = \
            config_loader.load_by_key("include_underscore_prefixed")
    
    return bundle
```

**Validation Gate 3.2**:
```bash
pytest tests/integration/test_policy_bundle_with_config.py -v
```

---

## Wave 4: Backward Compatibility Layer (1 day)

### Task 4.1: Implement deprecated resolver function wrappers

**File**: `src/prism/scanner_plugins/defaults.py`

**Implementation**: Wrap existing resolver functions

```python
import warnings
from functools import wraps

def _deprecated_resolver(policy_kind: str):
    """Decorator for deprecated resolver functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated; use policy_manager.resolve_{policy_kind}_policy() instead",
                DeprecationWarning,
                stacklevel=2,
            )
            # Get policy_manager from DI
            di = kwargs.get("di") or args[0] if args else None
            if di and hasattr(di, "policy_manager"):
                method_name = f"resolve_{policy_kind}_policy"
                return getattr(di.policy_manager, method_name)()
            # Fallback to old implementation
            return func(*args, **kwargs)
        return wrapper
    return decorator

@_deprecated_resolver("task_line_parsing")
def resolve_task_line_parsing_policy_plugin(di):
    """DEPRECATED: Use policy_manager.resolve_task_line_parsing_policy()"""
    # Old implementation (preserved for fallback)
    ...

# Similar for other 5 resolver functions
```

**Validation Gate 4.1**:
```bash
pytest tests/scanner_plugins/test_backward_compat.py -v
# Check that deprecated functions still work and emit warnings
```

### Task 4.2: Test old code paths still work

**File**: `tests/scanner_plugins/test_backward_compat.py`

**Tests**:

- Old resolver functions return same policy as new
- DeprecationWarning is emitted
- Tests pass with and without warnings captured

**Validation Gate 4.2**:
```bash
pytest tests/scanner_plugins/test_backward_compat.py -W error::DeprecationWarning -v 2>&1 | grep -c "deprecated" && echo "✓ Deprecation warnings working"
```

---

## Wave 5: Integration with Scanner Core (1 day)

### Task 5.1: Update prepare_scan_context() to use PolicyManager

**File**: `src/prism/scanner_core/scanner_context.py`

**Implementation**:

```python
def prepare_scan_context(
    scan_options: ScanOptions,
    di: DIContainer,
) -> ScanContext:
    """Prepare scan context with policies resolved via PolicyManager."""
    
    # Load config
    config_loader = ConfigPolicyLoader(scan_options.policy_context)
    
    # Resolve policies via PolicyManager
    prepared_bundle = di.policy_manager.resolve_prepared_policy_bundle(config_loader)
    
    # Create context
    context = ScanContext(
        # ... existing fields ...
        prepared_policy_bundle=prepared_bundle,
    )
    
    return context
```

**Validation Gate 5.1**:
```bash
pytest tests/scanner_core/test_scanner_context.py::test_prepare_scan_context_uses_policy_manager -v
```

### Task 5.2: Add di_helpers for policy access

**File**: Update `src/prism/scanner_core/di_helpers.py`

**Implementation**:

```python
def get_prepared_policy_bundle(di: DIContainer) -> PreparedPolicyBundle | None:
    """Get prepared policy bundle from DI."""
    if hasattr(di, "policy_manager"):
        return di.policy_manager.resolve_prepared_policy_bundle()
    return None

def get_task_line_parsing_policy(di: DIContainer) -> PreparedTaskLineParsingPolicy:
    """Get task line parsing policy."""
    return di.policy_manager.resolve_task_line_parsing_policy()

# Similar for other policies
```

**Validation Gate 5.2**:
```bash
pytest tests/scanner_core/test_di_helpers.py -v
```

---

## Wave 6: Testing & Documentation (1 day)

### Task 6.1: Add comprehensive test fixtures

**File**: `tests/fixtures/policy_fixtures.py`

**Implementation**:

```python
@pytest.fixture
def mock_fallback_registry():
    """Create mock fallback registry for testing."""
    registry = FallbackPolicyRegistry()
    # Register mock policies
    registry.register_fallback("task_line_parsing", MockTaskLinePolicy())
    registry.register_fallback("jinja_analysis", MockJinjaPolicy())
    # ... etc ...
    return registry

@pytest.fixture
def mock_policy_manager():
    """Create mock policy manager for testing."""
    return PolicyManager(
        fallback_registry=mock_fallback_registry(),
    )

@pytest.fixture
def mock_config_loader():
    """Create mock config loader for testing."""
    return ConfigPolicyLoader({
        "policy_context": {
            "dynamic_includes": {"fail_on_unconstrained": False},
        },
    })
```

**Validation Gate 6.1**:
```bash
pytest tests/fixtures/ -v
```

### Task 6.2: Performance benchmarking

**File**: `tests/perf/test_policy_resolution_perf.py`

**Tests**:

- Single policy resolution time (<1ms)
- Bundle resolution time (<5ms)
- Cache hit time (<0.1ms)
- 1000× resolution throughput

**Validation Gate 6.2**:
```bash
pytest tests/perf/test_policy_resolution_perf.py -v --durations=10
# Expected: All tests pass, times within budget
```

### Task 6.3: Update documentation

**Files**:
- Update `scanner_plugins/README.md` with PolicyManager usage
- Update `scanner_core/README.md` with policy bundle propagation
- Add module docstrings

**Validation Gate 6.3**:
```bash
python -c "import scanner_plugins.policy_manager; help(scanner_plugins.policy_manager.PolicyManager)" | head -20
```

---

## Wave 7: Final Validation (0.5 days)

### Task 7.1: Full test suite

**Command**:

```bash
pytest tests/ -v --cov=src/prism/scanner_plugins/policy_manager \
                    --cov=src/prism/scanner_plugins/fallback_registry \
                    --cov=src/prism/scanner_config/policy_loader
```

**Expected**:
- 50+ tests pass
- Coverage >90%
- 0 warnings

### Task 7.2: Integration test with real scan

**Test**: Run a complete scan end-to-end

```bash
pytest tests/integration/test_full_scan_with_policies.py -v
```

**Expected**:
- Full scan completes successfully
- No deprecation warnings from new code paths
- Performance within baseline (±5%)

### Task 7.3: Lint & type checking

**Commands**:

```bash
# Type checking
mypy src/prism/scanner_plugins/policy_manager.py
mypy src/prism/scanner_plugins/fallback_registry.py
mypy src/prism/scanner_config/policy_loader.py

# Linting
ruff check src/prism/scanner_plugins/policy_manager.py
ruff check src/prism/scanner_plugins/fallback_registry.py
ruff check src/prism/scanner_config/policy_loader.py
```

**Expected**:
- 0 type errors
- 0 lint violations

### Validation Gate 7.3 (FINAL):

```bash
pytest tests/ -v \
  && mypy src/prism/scanner_plugins/policy_manager.py \
  && ruff check src/prism/ \
  && echo "✅ ALL VALIDATION GATES PASSED"
```

---

## Dependency Graph

```
Wave 0 (Prep)
  ├─→ Wave 1 (FallbackRegistry) 
  │     └─→ Wave 2 (PolicyManager)
  │           ├─→ Wave 3 (ConfigPolicyLoader)
  │           │     └─→ Wave 5 (Integration)
  │           └─→ Wave 4 (Backward Compat)
  │                 └─→ Wave 5 (Integration)
  └─→ Wave 6 (Testing & Docs)
        └─→ Wave 7 (Final Validation)
```

---

## Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Import cycles | Medium | Medium | Careful import ordering in bootstrap |
| Performance regression | Low | Medium | Benchmark in Wave 6, cache design |
| Backward compat broken | Low | High | Comprehensive deprecation testing |
| Type safety not enforced | Medium | Medium | mypy type checking in Wave 7 |
| Thread safety issue | Low | Medium | RLock in registry, immutable cache |

---

## Success Criteria

- ✅ All 7 waves completed on schedule (8 person-days)
- ✅ 50+ tests passing, >90% coverage
- ✅ Zero type errors (mypy clean)
- ✅ Zero lint violations (ruff clean)
- ✅ Full scan works end-to-end
- ✅ Performance within 5% baseline
- ✅ Backward compatibility maintained
- ✅ Deprecation warnings guide migration

---

## Rollback Plan

If any wave fails validation:

1. Keep Wave 0 and pre-consolidation state in sync
2. Rollback changes from failed wave
3. Fix issues and re-run validation
4. Continue to next wave

**Rollback commands**:

```bash
git checkout HEAD~N -- src/prism/scanner_plugins/policy_manager.py
git checkout HEAD~N -- src/prism/scanner_plugins/fallback_registry.py
git checkout HEAD~N -- src/prism/scanner_config/policy_loader.py
```

---

## Next Steps (After Phase 0)

**Phase 1 (Implementation)**: Execute Waves 0-7 (~8 person-days)  
**Phase 2 (Migration)**: Migrate consumers to PolicyManager (~5 person-days)  
**Phase 3 (Cleanup)**: Remove deprecated resolver functions (~1 person-day)  

---

## References

- Interface specifications: `policy-manager-interface.py`
- Architecture & boundaries: `policy-boundary-design.md`
- Backward compatibility: `backward-compatibility-strategy.md`
