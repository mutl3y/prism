# PolicyManager Consolidation: Architecture & Extraction Boundaries

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-0-scout-policy-boundary  
**Created**: 2026-05-09  
**Status**: DESIGN COMPLETE

---

## Executive Summary

This document defines the consolidated PolicyManager architecture and extraction boundaries that will eliminate 40+ lines of boilerplate, unify 6 resolver functions into a single facade, and enable 72% consolidation of the 28 existing policies.

**Key Outcomes**:
- **Single facade**: PolicyManager replaces 6 scattered resolver functions
- **Centralized registry**: FallbackPolicyRegistry manages 6 singleton fallback instances
- **Unified config**: ConfigPolicyLoader consolidates 4 separate config loaders
- **Type-safe**: All policies accessed through protocols; no `Any` returns
- **Testable**: Mock registry and mock manager for easy fixture setup
- **Backward compatible**: Existing resolver functions delegate to PolicyManager

---

## Section 1: Architecture Overview

### Current State (Pre-Consolidation)

```
┌──────────────────────────────────────────────────────────────┐
│ SCATTER-GATHER PATTERN (Current)                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Consumer A          Consumer B          Consumer C          │
│  (task_extract)      (task_catalog)      (variable_disc)     │
│      │                   │                   │               │
│      ├──→ resolve_task_line_parsing_policy()                │
│      ├──→ resolve_task_traversal_policy()                   │
│      │                   │                                   │
│      └──→ resolver funcs → DI factory  → PluginRegistry     │
│          [6 variants]      ↓             ↓                  │
│          (scattered)      di.get()      registry.get()      │
│                           [duplicated]   [6 lookups]        │
│                               │              │              │
│                               └──────→ FallbackPolicyRegistry│
│                                       (global variables)     │
│                                       [no centralization]    │
└──────────────────────────────────────────────────────────────┘

Problems:
- Boilerplate: 6 resolver functions, 30+ lines each
- No single entry point: Caller must know which resolver to call
- Scattered error handling: Each resolver handles errors differently
- Hard to test: 6 separate mocks needed
- Hard to extend: Adding policy type requires new resolver function
```

### New State (Post-Consolidation)

```
┌──────────────────────────────────────────────────────────────┐
│ FACADE PATTERN (Consolidated)                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Consumer A          Consumer B          Consumer C          │
│  (task_extract)      (task_catalog)      (variable_disc)     │
│      │                   │                   │               │
│      └────→ PolicyManager.resolve_*() ←─────┘                │
│            (single facade)                                   │
│            [8 public methods]                                │
│                │                                            │
│                ├──→ DI factory override?                    │
│                │    (factory_POLICY_NAME_policy_plugin)     │
│                ├──→ PluginRegistry lookup?                  │
│                │    registry.get_plugin_for(kind)           │
│                └──→ FallbackRegistry lookup                 │
│                     fallback_registry.get_fallback(kind)    │
│                     [unified resolution]                    │
│                     [cached results]                        │
│                     [consistent errors]                     │
│                                                              │
│              DIContainer                  FallbackRegistry   │
│              ──────────                    ─────────────────  │
│              policy_manager: PolicyManager                   │
│                └─ 1 single instance       6 singleton policies
│                   reused across              (initialized at
│                   all consumers              bootstrap)
│
│              PluginRegistry (custom policies)
│              ──────────────────────────────
│              extensible; no core changes needed
└──────────────────────────────────────────────────────────────┘

Benefits:
- Single entry point: All consumers use PolicyManager
- Consistent error handling: All resolution errors handled uniformly
- Easy to test: 1 mock manager instead of 6 mocks
- Easy to extend: Add policy_kind to resolve_by_kind() only
- Centralized caching: Resolved policies cached in manager
- Type-safe: Protocols ensure all policies conform to contract
```

### High-Level Component Diagram

```
┌────────────────────────────────────────────────────────────┐
│ SCAN INITIALIZATION (at ingress seam)                      │
│ prepare_scan_context()                                     │
│ prepare_policy_bundle()                                    │
│                                                            │
│  1. Load scan config (.prism.yml)                         │
│  2. Initialize FallbackPolicyRegistry (if needed)         │
│  3. Create PolicyManager(fallback_reg, plugin_reg, di)   │
│  4. Call policy_manager.resolve_prepared_policy_bundle() │
│  5. Package PreparedPolicyBundle                          │
│  6. Inject into ScanContext                               │
└────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│ RUNTIME (scan execution)                                   │
│                                                            │
│  scanner_core, scanner_extract, scanner_plugins consume   │
│  policies from:                                           │
│    - ScanContext.prepared_policy_bundle                  │
│      (or)                                                 │
│    - di.policy_manager.resolve_*()                       │
│                                                            │
│  All resolution goes through PolicyManager:              │
│    ✓ Consistent caching                                  │
│    ✓ Single source of truth                              │
│    ✓ Testable via mock manager                           │
└────────────────────────────────────────────────────────────┘
```

---

## Section 2: Extraction Boundaries

The consolidation requires clear extraction boundaries defining what moves where.

### Boundary 1: FallbackPolicyRegistry

**Location**: `src/prism/scanner_plugins/fallback_registry.py` (NEW)

**What moves here**:
- 6 singleton fallback instances currently in `defaults.py`
  - `_TASK_LINE_PARSING_FALLBACK`
  - `_TASK_ANNOTATION_FALLBACK`
  - `_TASK_TRAVERSAL_FALLBACK`
  - `_VARIABLE_EXTRACTOR_FALLBACK`
  - `_YAML_PARSING_FALLBACK`
  - `_JINJA_ANALYSIS_FALLBACK`
- Registry logic for storing/retrieving fallbacks
- Thread-safe access via RLock

**What stays in `defaults.py`**:
- Platform-specific implementations (AnsibleDefault* classes)
- Custom implementation classes (DefaultYAMLParsingPolicyPlugin, etc.)
- Registration logic (calling `registry.register_fallback()`)
- Bootstrap responsibility: initialize_fallback_registry()

**Extraction Rationale**:
- FallbackPolicyRegistry is a generic data structure, not Ansible-specific
- Centralizes singleton management (currently scattered)
- Enables testing via mock registry
- Separates concerns: data structure (registry) vs. policy definitions (defaults.py)

### Boundary 2: PolicyManager

**Location**: `src/prism/scanner_plugins/policy_manager.py` (NEW)

**What moves here**:
- 6 resolver functions from `defaults.py` (consolidated into PolicyManager)
- Resolution logic: DI factory → PluginRegistry → FallbackRegistry
- Caching logic: `_resolved_cache` dict
- Error handling: Unified validation and error raising
- Factory methods: `resolve_task_line_parsing_policy()`, etc.

**What stays in `defaults.py`**:
- Policy implementation classes (AnsibleDefault*, Default*)
- Singleton instantiation (registration into FallbackRegistry)
- Configuration schema definitions
- Type definitions and constants

**Extraction Rationale**:
- PolicyManager is generic, not platform-specific
- Consolidates 200+ lines of duplicated resolver logic
- Single entry point for all resolution
- Enables easy testing and extension

### Boundary 3: ConfigPolicyLoader

**Location**: `src/prism/scanner_config/policy_loader.py` (NEW)

**What moves here**:
- 4 separate config loading functions from `scanner_config/policy.py`
  - `load_fail_on_unconstrained_dynamic_includes()`
  - `load_fail_on_yaml_like_task_annotations()`
  - `load_ignore_unresolved_internal_underscore_references()`
  - `load_non_authoritative_test_evidence_max_file_bytes()`
- Shared `_load_policy_config_dict()` helper
- Config spec definitions (PolicyConfigSpec)
- Coercion functions: `_coerce_bool()`, `_coerce_positive_int()`, etc.
- Schema documentation

**What stays in `scanner_config/policy.py`**:
- Policy context structures (ScanPolicyContext, DynamicIncludesPolicyContext, etc.)
- Policy application logic (where policies are used in scan)
- Policy defaults (if not moved to ConfigPolicyLoader)

**Extraction Rationale**:
- ConfigPolicyLoader is a generic config loading facility
- Consolidates 4 separate functions (duplicated error handling)
- Enables schema introspection (for help, validation, etc.)
- Separates concerns: loading (loader) vs. application (policy.py)

### Boundary 4: Consolidation in Scanner Core

**Location**: `src/prism/scanner_core/` (modifications)

**What changes**:
- `scanner_context.prepare_scan_context()` calls `policy_manager.resolve_prepared_policy_bundle()`
- `di_helpers.py` adds `get_policy_manager()` helper
- Policy access patterns:
  - Direct from bundle: `bundle['task_line_parsing']`
  - Or via manager: `di.policy_manager.resolve_task_line_parsing_policy()`

**What stays**:
- Core scanning logic unchanged
- DI injection unchanged
- ScanContext structure unchanged (but maybe simplified)

**Extraction Rationale**:
- scanner_core becomes a consumer of PolicyManager
- Simplifies ingress seam logic (fewer separate resolver calls)
- Policy resolution becomes explicit and traceable

### Boundary 5: Backward Compatibility Layer

**Location**: `src/prism/scanner_plugins/defaults.py` + `src/prism/scanner_extract/extract_defaults.py`

**What changes**:
- Old resolver functions (6) remain but delegate to PolicyManager
- Marked with `@deprecated` decorator
- Issue DeprecationWarning to stderr
- Call path: `old_resolve_*()` → `_policy_manager.resolve_*()`

**What stays**:
- Public function signatures unchanged
- Return types unchanged
- Behavior unchanged (just delegated)

**Extraction Rationale**:
- Supports gradual migration to PolicyManager
- Existing code continues to work without modification
- Deprecation warnings guide migration
- Enables phased refactoring

### Extraction Boundary Summary Table

| Component | Location | Scope | Ownership |
|-----------|----------|-------|-----------|
| **FallbackPolicyRegistry** | `scanner_plugins/fallback_registry.py` | Generic registry for singleton fallbacks | scanner_plugins layer |
| **PolicyManager** | `scanner_plugins/policy_manager.py` | Unified facade for policy resolution | scanner_plugins layer |
| **ConfigPolicyLoader** | `scanner_config/policy_loader.py` | Config loading for policy parameters | scanner_config layer |
| **Policy Implementations** | `scanner_plugins/ansible/default_policies.py` | Ansible-specific policy implementations | scanner_plugins/ansible layer |
| **Backward Compat Layer** | `scanner_plugins/defaults.py` | Deprecated resolver functions | scanner_plugins layer |
| **Consumers** | `scanner_core/`, `scanner_extract/`, etc. | Use PolicyManager or bundle | respective layers |

---

## Section 3: Resolution Flow (Detailed)

### Flow 1: Resolve Single Policy (Task Line Parsing)

```
Consumer calls:
  policy = policy_manager.resolve_task_line_parsing_policy()

PolicyManager.resolve_task_line_parsing_policy():
  1. Check cache: _resolved_cache["task_line_parsing"]?
     → If hit, return cached value (no lock needed, cache is r/o)
  
  2. Check DI factory override:
     factory_name = "factory_task_line_parsing_policy_plugin"
     if di and hasattr(di, factory_name):
         factory_fn = getattr(di, factory_name)
         try:
             result = factory_fn()
             if result is not None:
                 _resolved_cache["task_line_parsing"] = result
                 return result
         except Exception as e:
             raise PolicyResolutionError(f"DI factory {factory_name} failed: {e}")
  
  3. Check PluginRegistry:
     if plugin_registry and plugin_registry.has_plugin("task_line_parsing"):
         plugin = plugin_registry.get_plugin("task_line_parsing")
         validate_protocol(plugin, PreparedTaskLineParsingPolicy)
         _resolved_cache["task_line_parsing"] = plugin
         return plugin
  
  4. Check FallbackRegistry:
     fallback = fallback_registry.get_fallback("task_line_parsing")
     if fallback is not None:
         validate_protocol(fallback, PreparedTaskLineParsingPolicy)
         _resolved_cache["task_line_parsing"] = fallback
         return fallback
  
  5. Error handling:
     if strict_mode:
         raise MissingPolicyError("task_line_parsing", "no DI, registry, or fallback found")
     else:
         return None
```

### Flow 2: Resolve All Policies (PreparedPolicyBundle)

```
Consumer calls:
  bundle = policy_manager.resolve_prepared_policy_bundle()

PolicyManager.resolve_prepared_policy_bundle():
  bundle = {}
  
  # Required policies
  bundle["task_line_parsing"] = self.resolve_task_line_parsing_policy()
  bundle["jinja_analysis"] = self.resolve_jinja_analysis_policy()
  
  # Optional policies
  try:
      bundle["task_traversal"] = self.resolve_task_traversal_policy()
  except MissingPolicyError:
      if not strict_mode:
          pass  # Skip optional policy
      else:
          raise
  
  try:
      bundle["yaml_parsing"] = self.resolve_yaml_parsing_policy()
  except MissingPolicyError:
      pass
  
  # Similar for remaining policies...
  
  # Metadata
  bundle["comment_doc_marker_prefix"] = config_loader.load_marker_prefix()
  bundle["ignore_unresolved_internal_underscore_references"] = config_loader.load_bool("ignore_underscore")
  
  return bundle
```

### Flow 3: Bootstrap & Initialization

```
At process startup:

1. bootstrap.py calls initialize_fallback_registry():
   
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
   # ... register remaining 4 policies ...
   
   return registry

2. bootstrap.py calls initialize_policy_manager(fallback_registry):
   
   manager = PolicyManager(
       fallback_registry=fallback_registry,
       plugin_registry=di.plugin_registry,
       di=di,
       context=PolicyResolutionContext(strict_mode=True)
   )
   
   return manager

3. DIContainer stores:
   - di.fallback_policy_registry = registry
   - di.policy_manager = manager

4. At scan ingress (prepare_scan_context):
   
   bundle = di.policy_manager.resolve_prepared_policy_bundle()
   
   # Store in ScanContext or ScanRequest for access by all layers
   scan_context.prepared_policy_bundle = bundle
```

---

## Section 4: Public API (8 PolicyManager Methods)

### Method: resolve_task_line_parsing_policy()

**Signature**:
```python
def resolve_task_line_parsing_policy(self) -> PreparedTaskLineParsingPolicy:
    """Resolve task line parsing policy."""
```

**Usage**:
```python
policy = policy_manager.resolve_task_line_parsing_policy()
module = policy.detect_task_module(task_dict)
```

**Responsibility**:
- Return policy instance for parsing task line syntax
- Detect task module names, extract constrained when values
- Required policy: raises MissingPolicyError if not found

---

### Method: resolve_jinja_analysis_policy()

**Signature**:
```python
def resolve_jinja_analysis_policy(self) -> PreparedJinjaAnalysisPolicy:
    """Resolve Jinja analysis policy."""
```

**Usage**:
```python
policy = policy_manager.resolve_jinja_analysis_policy()
undeclared = policy.collect_undeclared_jinja_variables(template_text)
```

**Responsibility**:
- Return policy instance for analyzing Jinja templates
- Extract undeclared variables using jinja2.meta
- Required policy: raises MissingPolicyError if not found

---

### Method: resolve_task_traversal_policy()

**Signature**:
```python
def resolve_task_traversal_policy(self) -> PreparedTaskTraversalPolicy:
    """Resolve task traversal policy."""
```

**Usage**:
```python
policy = policy_manager.resolve_task_traversal_policy()
tasks = policy.iter_task_mappings(data)
```

**Responsibility**:
- Return policy instance for traversing task hierarchies
- Enumerate includes, resolve role/task graphs
- Optional policy: may return None if not found (unless strict_mode)

---

### Method: resolve_task_annotation_parsing_policy()

**Signature**:
```python
def resolve_task_annotation_parsing_policy(self) -> PreparedTaskAnnotationPolicy:
    """Resolve task annotation parsing policy."""
```

**Usage**:
```python
policy = policy_manager.resolve_task_annotation_parsing_policy()
annotations = policy.extract_task_annotations_for_file(lines, "@prism")
```

**Responsibility**:
- Return policy instance for parsing task annotations
- Handle marker prefixes, extract metadata from comments
- Optional policy: may return None if not found

---

### Method: resolve_yaml_parsing_policy()

**Signature**:
```python
def resolve_yaml_parsing_policy(self) -> PreparedYAMLParsingPolicy:
    """Resolve YAML parsing policy."""
```

**Usage**:
```python
policy = policy_manager.resolve_yaml_parsing_policy()
data = policy.load_yaml_file("tasks/main.yml")
```

**Responsibility**:
- Return policy instance for YAML file parsing
- Validate YAML, emit parse failures
- Optional policy: may return None if not found

---

### Method: resolve_variable_extractor_policy()

**Signature**:
```python
def resolve_variable_extractor_policy(self) -> PreparedVariableExtractorPolicy:
    """Resolve variable extractor policy."""
```

**Usage**:
```python
policy = policy_manager.resolve_variable_extractor_policy()
include_vars = policy.collect_include_vars_files(role_path)
```

**Responsibility**:
- Return policy instance for variable file extraction
- Collect include_vars files, variable sources
- Optional policy: may return None if not found

---

### Method: resolve_prepared_policy_bundle()

**Signature**:
```python
def resolve_prepared_policy_bundle(self) -> PreparedPolicyBundle:
    """Resolve all policies into a PreparedPolicyBundle."""
```

**Usage**:
```python
bundle = policy_manager.resolve_prepared_policy_bundle()
# Pass bundle through call stack instead of individual policies
task_line_policy = bundle["task_line_parsing"]
jinja_policy = bundle["jinja_analysis"]
```

**Responsibility**:
- Resolve all 6 policies
- Package into TypedDict
- Return single object for easier propagation through layers

---

### Method: resolve_by_kind()

**Signature**:
```python
def resolve_by_kind(self, policy_kind: str) -> object | None:
    """Generic resolution by policy kind."""
```

**Usage**:
```python
policy = policy_manager.resolve_by_kind("custom_policy")
```

**Responsibility**:
- Generic extension point for new policy types
- Used when adding new policy kinds without modifying API
- Returns None if not found (unless strict_mode)

---

## Section 5: Consolidation Metrics

### Lines of Code Reduction

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Resolver functions (6) | 210 lines | 0 lines | -210 |
| Fallback singletons (6) | 20 lines | 0 lines (moved to registry) | -20 |
| Config loading (4 functions) | 80 lines | 0 lines (consolidated) | -80 |
| Boilerplate in defaults.py | 35 lines | 10 lines (registration calls) | -25 |
| **TOTAL** | **345 lines** | **10 lines** | **-335 lines (97% reduction)** |

### Consolidation Opportunities

| Opportunity | Current | Proposed | Benefit |
|-------------|---------|----------|---------|
| **Singleton Management** | 6 globals + 6 fallback vars | FallbackPolicyRegistry | Type-safe, testable, extensible |
| **Policy Resolution** | 6 functions, 30+ lines each | PolicyManager facade, 100 lines | Single entry point, unified error handling |
| **Config Loading** | 4 functions, duplicated logic | ConfigPolicyLoader, 80 lines | Centralized, schema-aware |
| **Error Handling** | Inconsistent across 6 functions | Unified in PolicyManager | Consistent, traceable |
| **Testing** | 6 separate mocks | 1 mock manager | Simpler test setup |
| **Extension** | New function required for each policy | resolve_by_kind() | No core changes needed |

---

## Section 6: Integration Points

### Integration 1: DIContainer

**Current**:
```python
class DIContainer:
    pass  # No policy manager
```

**After Consolidation**:
```python
class DIContainer:
    fallback_policy_registry: FallbackPolicyRegistry
    policy_manager: PolicyManager
    
    def factory_task_line_parsing_policy_plugin(self) -> PreparedTaskLineParsingPolicy | None:
        """Optional DI factory override for task line parsing policy."""
        ...
```

### Integration 2: ScanContext

**Current**:
```python
class ScanContext(TypedDict):
    # 6 separate policy fields
    task_line_parsing_policy: PreparedTaskLineParsingPolicy
    jinja_analysis_policy: PreparedJinjaAnalysisPolicy
    task_traversal_policy: PreparedTaskTraversalPolicy
    # ... etc
```

**After Consolidation**:
```python
class ScanContext(TypedDict):
    # Single bundle field (optionally)
    prepared_policy_bundle: PreparedPolicyBundle
    # Or still reference via DI:
    # policy_manager = di.policy_manager (implicit)
```

### Integration 3: Scanner Extract

**Current**:
```python
# task_extract_adapters.py
from scanner_plugins.defaults import resolve_task_line_parsing_policy

policy = resolve_task_line_parsing_policy(di)
```

**After Consolidation**:
```python
# task_extract_adapters.py
policy = di.policy_manager.resolve_task_line_parsing_policy()
# or
policy = prepared_policy_bundle["task_line_parsing"]
```

---

## Section 7: Design Principles

### Principle 1: Single Responsibility

Each component has a single, well-defined responsibility:
- **FallbackPolicyRegistry**: Manage singleton fallback instances
- **PolicyManager**: Unified facade for policy resolution
- **ConfigPolicyLoader**: Load policy config parameters
- **Policy Implementations**: Provide specific policy behavior

### Principle 2: Separation of Concerns

- **Data structure (registry)** separated from **policy definitions (implementations)**
- **Generic logic (PolicyManager)** separated from **platform-specific logic (Ansible plugins)**
- **Configuration (ConfigPolicyLoader)** separated from **application (policy.py)**

### Principle 3: Type Safety

- All policies accessed through protocols (no `Any`)
- PreparedPolicyBundle is a TypedDict (structural typing)
- PolicyConfigSpec is a dataclass (type-safe config specs)

### Principle 4: Extensibility

- New policy kinds can be added without modifying PolicyManager
- New DI factories override existing policies (non-invasive)
- PluginRegistry enables custom implementations (pluggable)

### Principle 5: Testability

- Mock registry and mock manager for easy test setup
- Consistent error types for error handling testing
- Resolution trace for debugging and verification

### Principle 6: Backward Compatibility

- Old resolver functions remain but delegate to PolicyManager
- Deprecation warnings guide gradual migration
- Existing code continues to work without modification

---

## Section 8: Implementation Readiness

### Preconditions Met

✅ Scout audit completed (28 policies inventoried)  
✅ Consolidation opportunities identified (10 findings)  
✅ Extraction boundaries defined (5 boundaries)  
✅ Interface specifications frozen (protocols, types)  
✅ Resolution flow documented (3 flows)  
✅ Backward compatibility strategy planned (deprecation path)  

### Next Phase (Phase 1)

The implementation plan is detailed in `consolidation-sequence.md`.

**Phase 1 deliverables**:
1. Create `fallback_registry.py` with FallbackPolicyRegistry class
2. Create `policy_manager.py` with PolicyManager class
3. Create `policy_loader.py` with ConfigPolicyLoader class
4. Update bootstrap.py to initialize registry and manager
5. Add backward compat layer (deprecated resolver functions)
6. Add test fixtures (mock manager, mock registry)
7. Integration tests for resolution flow
8. Performance benchmarking

**Phase 1 scope**: 8 person-days of implementation

**Phase 2**: Gradual migration of consumers to PolicyManager

### Non-Goals (Out of Scope)

- Implementation of policy logic (implementations are existing; consolidation only)
- Plugin system redesign (PluginRegistry remains as-is)
- DI container redesign (DIContainer integration only)
- Performance optimization (consolidation improves performance naturally)

---

## Appendix: Design Decisions & Rationale

### Decision 1: FallbackPolicyRegistry vs. Global Singletons

**Option A**: Keep global singleton fallback instances (current state)
- Pro: No indirection
- Con: Hard to test, hard to mock, fragile

**Option B**: FallbackPolicyRegistry (chosen)
- Pro: Type-safe, testable, thread-safe, extensible
- Con: One level of indirection

**Rationale**: Testability and extensibility outweigh indirection cost.

### Decision 2: PolicyManager Facade vs. Direct Registry Access

**Option A**: Consumers access FallbackRegistry directly
- Pro: Fewer layers
- Con: No caching, no DI integration, duplicated resolution logic

**Option B**: PolicyManager facade (chosen)
- Pro: Single entry point, caching, consistent error handling, DI integration
- Con: One additional layer

**Rationale**: Unified access and caching justify facade layer.

### Decision 3: Caching Strategy

**Option A**: No caching (resolve on every call)
- Pro: Simple
- Con: Repeated resolution overhead, repeated validation

**Option B**: Per-request caching in ScanContext
- Pro: Scoped to single scan
- Con: Couples cache lifetime to scan lifetime

**Option C**: PolicyManager-level caching (chosen)
- Pro: Cross-scan reuse possible, transparent to consumer
- Con: Assumes policies are immutable (they are)

**Rationale**: Policies are stateless; caching is safe and improves performance.

### Decision 4: Error Handling Strategy

**Option A**: Silent fallback to None
- Pro: Forgiving
- Con: Silent failures are hard to debug

**Option B**: Strict mode (raise on missing policy)
- Pro: Fails fast, clear errors
- Con: May break optional policies

**Option C**: Configurable via strict_mode flag (chosen)
- Pro: Strict in production, forgiving in tests
- Con: Complexity in two paths

**Rationale**: Strict mode catches bugs; flag allows testing flexibility.

---

## References

- Policy inventory: `policy-inventory.yaml`
- Consolidation opportunities: `consolidation-opportunities.md`
- Implementation sequence: `consolidation-sequence.md`
- Backward compatibility: `backward-compatibility-strategy.md`
