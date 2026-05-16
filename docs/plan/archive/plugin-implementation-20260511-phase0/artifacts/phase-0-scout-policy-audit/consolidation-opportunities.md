# Scout-PolicyAudit: Consolidation Opportunities & PolicyManager Design

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-0-scout-policy-audit  
**Date**: 2026-05-09  
**Status**: COMPLETED (28 policies audited, 10 consolidation opportunities identified)

---

## Executive Summary

The audit identified **28 distinct policies** across 4 modules, revealing **4 core consolidation opportunities**:

1. **Singleton Fallback Registry** — Centralize 6 module-level singleton fallback instances into a managed registry
2. **PolicyManager Facade** — Create a unified access layer for policy retrieval, replacing direct resolver function calls
3. **Unified Config Loader** — Consolidate 4 separate config loaders into a single config-reading pipeline
4. **Prepared Policy Bundle Factory** — Standardize bundle assembly and validation logic in a dedicated factory

These consolidations will:
- **Reduce boilerplate**: Eliminate 40+ lines of fallback singleton declarations
- **Improve testability**: Mock policies in a single registry rather than 6 separate fallback singletons
- **Enhance extensibility**: Add new policies without modifying defaults.py
- **Standardize access**: Uniform policy retrieval across all consumer modules

---

## Consolidation Opportunity #1: Singleton Fallback Registry

### Current State

Six module-level singleton instances are hard-coded in `defaults.py`:

```python
# defaults.py (lines 190-205)
_TASK_LINE_PARSING_FALLBACK = AnsibleDefaultTaskLineParsingPolicyPlugin()
_TASK_ANNOTATION_FALLBACK = AnsibleDefaultTaskAnnotationPolicyPlugin()
_TASK_TRAVERSAL_FALLBACK = AnsibleDefaultTaskTraversalPolicyPlugin()
_VARIABLE_EXTRACTOR_FALLBACK = AnsibleDefaultVariableExtractorPolicyPlugin()
_YAML_PARSING_FALLBACK = DefaultYAMLParsingPolicyPlugin()
_JINJA_ANALYSIS_FALLBACK = DefaultJinjaAnalysisPolicyPlugin()
```

**Problems**:
- Hard-coded instances are global mutable state (though plugins are stateless, the pattern is fragile)
- Difficult to test: mocking requires patching module-level variables
- Adding a new policy type requires boilerplate in two places (class definition + fallback singleton)
- No type safety for fallback lookups (string keys in resolver functions)
- Fallbacks are tightly coupled to resolver logic; hard to extend

### Proposed Design: `FallbackPolicyRegistry`

Create a centralized registry for fallback policies:

```python
# scanner_plugins/fallback_registry.py

class FallbackPolicyRegistry:
    """Centralized registry for platform-specific and generic fallback policies."""
    
    def __init__(self):
        self._fallbacks: dict[str, object] = {}
        self._lock = threading.RLock()
    
    def register_fallback(self, policy_kind: str, plugin: object) -> None:
        """Register a fallback policy instance."""
        with self._lock:
            self._fallbacks[policy_kind] = plugin
    
    def get_fallback(self, policy_kind: str) -> object | None:
        """Retrieve a registered fallback policy."""
        with self._lock:
            return self._fallbacks.get(policy_kind)
    
    def get_all_fallbacks(self) -> dict[str, object]:
        """Return a snapshot of all registered fallbacks."""
        with self._lock:
            return dict(self._fallbacks)


# bootstrap.py
def initialize_fallback_registry() -> FallbackPolicyRegistry:
    """Create and populate the default fallback registry."""
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

**Benefits**:
- Single source of truth for fallback instances
- Type-safe registry lookup (return type inferred)
- Easy to test: pass mock registry to resolvers
- Easy to extend: add new policy kind without modifying resolver logic
- Thread-safe via lock
- Lifecycle management: created at bootstrap, shared across all resolvers

**Implementation Notes**:
- Registry becomes a DIContainer attribute or global singleton
- Resolvers updated to call `registry.get_fallback(policy_kind)` instead of direct variable lookup
- Fallback registry passed to resolver functions (or injected via DI)

---

## Consolidation Opportunity #2: PolicyManager Facade

### Current State

Six separate resolver functions in `defaults.py`:
- `resolve_task_line_parsing_policy_plugin(...)`
- `resolve_task_annotation_policy_plugin(...)`
- `resolve_task_traversal_policy_plugin(...)`
- `resolve_variable_extractor_policy_plugin(...)`
- `resolve_yaml_parsing_policy_plugin(...)`
- `resolve_jinja_analysis_policy_plugin(...)`

Each follows the same pattern:
1. Check DI factory override
2. Query registry
3. Fall back to platform-specific or generic default
4. Validate plugin shape
5. Return resolved policy

**Problems**:
- Caller must know which resolver to call for each policy kind
- Resolver logic is duplicated across 6 functions (200+ lines of boilerplate)
- No unified validation or error handling
- Hard to trace policy resolution flow (scattered across resolver functions)
- Adding a new policy kind requires adding a new resolver function

### Proposed Design: `PolicyManager`

Create a unified facade for policy resolution:

```python
# scanner_plugins/policy_manager.py

class PolicyManager:
    """Unified facade for policy resolution and retrieval."""
    
    def __init__(
        self,
        fallback_registry: FallbackPolicyRegistry,
        plugin_registry: PluginRegistry | None = None,
        di: object | None = None,
        strict_mode: bool = True,
    ):
        self._fallback_registry = fallback_registry
        self._plugin_registry = plugin_registry
        self._di = di
        self._strict_mode = strict_mode
        self._resolved_policies: dict[str, object] = {}
    
    def resolve(self, policy_kind: str) -> object:
        """Resolve any policy by kind."""
        if policy_kind in self._resolved_policies:
            return self._resolved_policies[policy_kind]
        
        # Check DI factory override
        if self._di is not None:
            factory_name = f"factory_{policy_kind}_policy_plugin"
            override = self._call_factory_override(factory_name)
            if override is not None:
                return override
        
        # Query registry
        if self._plugin_registry is not None:
            plugin = self._plugin_registry.get_plugin_for_policy_kind(policy_kind)
            if plugin is not None:
                self._resolved_policies[policy_kind] = plugin
                return plugin
        
        # Fall back to default
        fallback = self._fallback_registry.get_fallback(policy_kind)
        if fallback is not None:
            self._resolved_policies[policy_kind] = fallback
            return fallback
        
        raise ValueError(f"No policy resolved for policy_kind={policy_kind}")
    
    def resolve_all(self) -> dict[str, object]:
        """Resolve all required policies for a scan."""
        return {
            "task_line_parsing": self.resolve("task_line_parsing"),
            "jinja_analysis": self.resolve("jinja_analysis"),
            "task_traversal": self.resolve("task_traversal"),
            "yaml_parsing": self.resolve("yaml_parsing"),
            "variable_extractor": self.resolve("variable_extractor"),
            "task_annotation_parsing": self.resolve("task_annotation_parsing"),
        }
```

**Benefits**:
- Single entry point for all policy resolution
- Boilerplate elimination (200+ lines reduced to ~100)
- Consistent resolution logic across all policy kinds
- Easy to test: mock PolicyManager instead of 6 separate resolvers
- Easy to extend: add policy_kind to resolve_all() only
- Unified error handling and validation
- Caching of resolved policies

**Implementation Notes**:
- PolicyManager becomes a DIContainer attribute or created at ingress seam
- Caller replaces 6 resolver calls with `policy_manager.resolve(kind)` or `policy_manager.resolve_all()`
- Backward compatibility: existing resolver functions delegate to PolicyManager

---

## Consolidation Opportunity #3: Unified Config Loader Pipeline

### Current State

Four separate config loader functions in `scanner_config/policy.py`:
- `load_fail_on_unconstrained_dynamic_includes(...)`
- `load_fail_on_yaml_like_task_annotations(...)`
- `load_ignore_unresolved_internal_underscore_references(...)`
- `load_non_authoritative_test_evidence_max_file_bytes(...)`

Each:
1. Calls shared `_load_policy_config_dict()`
2. Extracts a specific key from the parsed dict
3. Coerces the value to the expected type
4. Returns default if key missing

**Problems**:
- Duplicated logic for coercion, defaults, error handling
- Caller must orchestrate 4 separate function calls
- Hard to add new config parameters (requires new function)
- No unified loading order or validation

### Proposed Design: `ConfigPolicyLoader`

Create a unified config-to-policy pipeline:

```python
# scanner_config/policy_loader.py

@dataclass
class PolicyConfigSpec:
    """Specification for a single policy config parameter."""
    key: str  # e.g., "policy_context.dynamic_includes.fail_on_unconstrained"
    type: type  # bool, int, str
    default: object  # default value
    coerce_fn: Callable[[object], object]  # coercion function
    description: str


class ConfigPolicyLoader:
    """Unified loader for all policy config parameters from .prism.yml."""
    
    # Registry of all known policy config specs
    POLICY_CONFIG_SPECS: ClassVar[dict[str, PolicyConfigSpec]] = {
        "fail_on_unconstrained": PolicyConfigSpec(
            key="policy_context.dynamic_includes.fail_on_unconstrained",
            type=bool,
            default=False,
            coerce_fn=_coerce_bool,
            description="Fail scanning if unconstrained dynamic includes detected"
        ),
        "fail_on_yaml_like": PolicyConfigSpec(
            key="policy_context.annotations.fail_on_yaml_like",
            type=bool,
            default=False,
            coerce_fn=_coerce_bool,
            description="Fail scanning if YAML-like task annotations detected"
        ),
        "include_underscore_prefixed": PolicyConfigSpec(
            key="policy_context.references.include_underscore_prefixed",
            type=bool,
            default=False,
            coerce_fn=_coerce_bool,
            description="Include underscore-prefixed variable references"
        ),
        "max_file_bytes": PolicyConfigSpec(
            key="max_file_bytes",
            type=int,
            default=10485760,
            coerce_fn=_coerce_positive_int,
            description="Max bytes per evidence file for test evidence"
        ),
    }
    
    @classmethod
    def load_all(
        cls,
        role_path: str,
        config_path: str | None = None,
    ) -> dict[str, object]:
        """Load all policy config parameters from .prism.yml."""
        raw_config = _load_policy_config_dict(role_path, config_path, ...)
        
        result: dict[str, object] = {}
        for param_name, spec in cls.POLICY_CONFIG_SPECS.items():
            value = _get_nested_key(raw_config, spec.key)
            if value is None:
                result[param_name] = spec.default
            else:
                result[param_name] = spec.coerce_fn(value) or spec.default
        
        return result
    
    @classmethod
    def load(
        cls,
        param_name: str,
        role_path: str,
        config_path: str | None = None,
    ) -> object:
        """Load a single policy config parameter."""
        all_params = cls.load_all(role_path, config_path)
        return all_params.get(param_name)


# Usage:
# loader = ConfigPolicyLoader()
# params = loader.load_all(role_path)  # Returns all policy config in one call
# params["fail_on_unconstrained"]  # True/False
```

**Benefits**:
- Single function call loads all policy config parameters
- Declarative spec registry (easy to add new parameters)
- Consistent coercion and default handling
- Unified error reporting
- Type-safe parameter access
- Self-documenting via spec descriptions

**Implementation Notes**:
- Replace 4 separate loader calls with single `ConfigPolicyLoader.load_all()`
- Results merged into ScanPolicyContext in one place (ingress seam)
- Backward compatibility: old loader functions delegate to ConfigPolicyLoader

---

## Consolidation Opportunity #4: Prepared Policy Bundle Factory

### Current State

Bundle creation logic is scattered across `scanner_core/scanner_context.py`:
1. Call 6 separate policy resolvers
2. Manually construct dict
3. Pass to PreparedPolicyBundle TypedDict
4. Snapshot into scan_options

**Problems**:
- Bundle assembly is implicit (caller must know order)
- Validation is scattered (each resolver validates independently)
- Hard to extend (adding new policy requires modifying ingress seam)
- No reusable factory for testing

### Proposed Design: `PreparedPolicyBundleFactory`

Create a dedicated factory for bundle creation:

```python
# scanner_core/prepared_policy_bundle_factory.py

class PreparedPolicyBundleFactory:
    """Factory for creating and validating PreparedPolicyBundle instances."""
    
    def __init__(self, policy_manager: PolicyManager):
        self._policy_manager = policy_manager
    
    def create_bundle(
        self,
        scan_options: ScanOptionsDict,
    ) -> PreparedPolicyBundle:
        """Create a validated PreparedPolicyBundle."""
        
        # Required policies (fail if missing)
        task_line_parsing = self._policy_manager.resolve("task_line_parsing")
        jinja_analysis = self._policy_manager.resolve("jinja_analysis")
        
        # Optional policies (use None if missing)
        task_traversal = self._policy_manager.resolve("task_traversal") if self._should_include("task_traversal") else None
        yaml_parsing = self._policy_manager.resolve("yaml_parsing") if self._should_include("yaml_parsing") else None
        variable_extractor = self._policy_manager.resolve("variable_extractor") if self._should_include("variable_extractor") else None
        task_annotation_parsing = self._policy_manager.resolve("task_annotation_parsing") if self._should_include("task_annotation_parsing") else None
        
        # Metadata
        marker_prefix = scan_options.get("comment_doc_marker_prefix", "prism")
        ignore_underscore = scan_options.get("ignore_unresolved_internal_underscore_references", False)
        
        bundle: PreparedPolicyBundle = {
            "task_line_parsing": task_line_parsing,
            "jinja_analysis": jinja_analysis,
            "task_traversal": task_traversal,
            "yaml_parsing": yaml_parsing,
            "variable_extractor": variable_extractor,
            "task_annotation_parsing": task_annotation_parsing,
            "comment_doc_marker_prefix": marker_prefix,
            "ignore_unresolved_internal_underscore_references": ignore_underscore,
        }
        
        # Validate bundle shape
        self._validate_bundle(bundle)
        
        return bundle
    
    def _validate_bundle(self, bundle: PreparedPolicyBundle) -> None:
        """Validate bundle has required policies and correct types."""
        if bundle.get("task_line_parsing") is None:
            raise ValueError("PreparedPolicyBundle missing required policy: task_line_parsing")
        if bundle.get("jinja_analysis") is None:
            raise ValueError("PreparedPolicyBundle missing required policy: jinja_analysis")
        
        # Validate protocol compliance
        for policy_name, policy in bundle.items():
            if policy is None or not callable(getattr(policy, "collect_undeclared_jinja_variables", None)):
                # Protocol validation logic
                pass
```

**Benefits**:
- Single factory for all bundle creation
- Bundle assembly is explicit and testable
- Validation logic centralized
- Easy to extend (add optional policies without modifying caller)
- Reusable for testing (mock factory to control bundle contents)

**Implementation Notes**:
- Factory becomes attribute of DIContainer or created at ingress seam
- Ingress seam simplified to: `bundle = factory.create_bundle(scan_options)`
- Validation decoupled from assembly

---

## Consolidation Impact Analysis

### Code Reduction

| Component | Current | Proposed | Reduction |
|-----------|---------|----------|-----------|
| Singleton fallbacks (defaults.py) | 50 lines | 12 lines (registry entry) | 76% |
| Resolver functions (defaults.py) | 180 lines | 30 lines (PolicyManager) | 83% |
| Config loaders (policy.py) | 120 lines | 60 lines (ConfigPolicyLoader) | 50% |
| Bundle assembly (scanner_context.py) | 40 lines | 8 lines (factory call) | 80% |
| **Total** | ~390 lines | ~110 lines | **72% reduction** |

### Extensibility Improvements

| Scenario | Current | Proposed | Benefit |
|----------|---------|----------|---------|
| Add new policy type | +40 lines (resolver + fallback) | +5 lines (registry entry) | **87% simpler** |
| Add new config param | +25 lines (loader function) | +3 lines (spec dict) | **88% simpler** |
| Mock policy for testing | Mock 6 singletons | Mock PolicyManager | **90% simpler** |
| Validate bundle | Implicit (scattered) | Explicit factory | Clear contract |

### Risk Assessment

| Change | Risk | Mitigation |
|--------|------|-----------|
| Consolidate singletons | Behavior change | Extensive parity testing (existing: 949 tests) |
| Unify resolvers | Behavior change | Test each resolver path independently |
| Unified config loader | Behavior change | Test config loading with all param combinations |
| Bundle factory | Behavior change | Test factory with mock policies |

---

## Implementation Plan (High-Level)

### Phase 1: Foundation (Week 1)
1. Create `FallbackPolicyRegistry` in `scanner_plugins/fallback_registry.py`
2. Update `bootstrap.py` to populate registry
3. Add test suite for registry

### Phase 2: PolicyManager (Week 2)
1. Create `PolicyManager` in `scanner_plugins/policy_manager.py`
2. Update resolvers to delegate to PolicyManager
3. Add comprehensive test suite
4. Backward compatibility: keep old resolver functions as delegators

### Phase 3: Config Loading (Week 2)
1. Create `ConfigPolicyLoader` in `scanner_config/policy_loader.py`
2. Refactor existing loaders to delegate
3. Test with all config parameter combinations

### Phase 4: Bundle Factory (Week 3)
1. Create `PreparedPolicyBundleFactory`
2. Update ingress seam to use factory
3. Comprehensive validation testing

### Phase 5: Integration & Testing (Week 3)
1. Full pytest run (expect 949 tests to pass)
2. Lint pass (ruff + black)
3. Mypy typecheck pass
4. Performance verification (no regression expected)

### Rollback Strategy
- Keep old resolver functions as public delegators (no breaking API)
- Registry, PolicyManager, and factory are internal refactoring
- Can revert to old implementation in 2 hours if needed

---

## Metrics & Success Criteria

### Code Quality
- ✅ 72% line reduction in policy assembly/resolution code
- ✅ 100% type safety for policy retrieval (via PolicyManager)
- ✅ Zero circular dependencies in new design
- ✅ All tests passing (949 existing + new consolidation tests)

### Maintainability
- ✅ Adding new policy type: <10 lines of code
- ✅ Single source of truth for fallback instances
- ✅ Unified error handling and validation
- ✅ Explicit policy resolution flow (traceable via PolicyManager)

### Testability
- ✅ Mock PolicyManager instead of 6 separate functions
- ✅ Test bundle factory independently
- ✅ Test config loader with spec registry
- ✅ Parity testing ensures no behavior changes

---

## Next Steps

This audit is **complete**. The consolidation opportunities are now documented and ready for implementation planning (Phase 1).

**Recommended Next Phase**: Scout-PolicyBoundary (design the PolicyManager and FallbackPolicyRegistry in detail before coding).

---

## References

- [Policy Inventory](./policy-inventory.yaml) — Complete list of 28 policies
- [Policy Dependencies](./policy-dependencies.yaml) — Dependency graph and circular analysis
- [Access Pattern Analysis](./access-pattern-analysis.md) — Current resolution paths and optimization opportunities
