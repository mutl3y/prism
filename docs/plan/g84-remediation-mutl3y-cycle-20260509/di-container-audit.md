# DI Container Audit: Complete Method Inventory

**Audit Date**: May 10, 2026  
**Target File**: `src/prism/scanner_core/di.py`  
**Scope**: All factory, plugin, and service methods in DIContainer (1000+ lines)  
**Status**: Read-only discovery complete; 18 public factory methods identified + 3 private helpers

---

## Executive Summary

The DIContainer class manages two primary responsibilities:
1. **Service Locator**: Orchestrates creation/caching of core runtime services (5-7 methods)
2. **Plugin Resolver**: Delegates plugin resolution through `PluginResolver` and `ServiceLocator` seams (11+ methods)

Current architecture already has partial extraction (PluginResolver in separate class), but additional refactoring opportunities exist for cleaner responsibility boundaries.

---

## Complete Method Inventory

### Public Factory Methods: SERVICE LOCATOR (Core Services)

| Method | Parameters | Return Type | Classification | Data Flow | Lines | Status |
|--------|-----------|-------------|-----------------|-----------|-------|--------|
| `factory_event_bus()` | none | `EventBus` | Service Locator | Reads: none; Returns: cached singleton | ~3 | ✅ Delegated to ServiceLocator |
| `factory_scanner_context()` | none | `ScannerContext` | Service Locator | Reads: `_scanner_context_wiring`, `_role_path`, `_scan_options`; Creates: ScannerContext | ~20 | ⚙️ Orchestration |
| `factory_variable_discovery()` | none | `VariableDiscovery` | Service Locator | Reads: mocks, overrides, `_role_path`, `_scan_options`; Creates/caches: VariableDiscovery | ~18 | ⚙️ Orchestration |
| `factory_feature_detector()` | none | `FeatureDetector` | Service Locator | Reads: mocks, overrides, `_role_path`, `_scan_options`; Creates/caches: FeatureDetector | ~18 | ⚙️ Orchestration |
| `factory_variable_row_builder()` | none | `VariableRowBuilder` | Factory Pattern | Creates/caches: VariableRowBuilder (lightweight, reusable) | ~7 | ⚙️ Orchestration |
| `factory_policy_registry()` | none | `FallbackPolicyRegistry` | Service Locator | Reads: mocks, overrides; Creates/caches: FallbackPolicyRegistry | ~12 | ⚙️ Orchestration |
| `factory_policy_manager()` | none | `PolicyManager` | Service Locator | Reads: mocks, overrides, `policy_registry`; Creates/caches: PolicyManager | ~13 | ⚙️ Orchestration |

**Summary**: 7 service locator methods managing object lifecycle with caching + mock/override routing.

---

### Public Factory Methods: PLUGIN RESOLVER (Registry-Backed)

| Method | Parameters | Return Type | Classification | Data Flow | Lines | Status |
|--------|-----------|-------------|-----------------|-----------|-------|--------|
| `factory_variable_discovery_plugin()` | none | `VariableDiscoveryPlugin` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_variable_discovery_plugin()` | ~6 | ✅ Delegated |
| `factory_feature_detection_plugin()` | none | `FeatureDetectionPlugin` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_feature_detection_plugin()` | ~6 | ✅ Delegated |
| `factory_comment_driven_doc_plugin()` | none | `CommentDrivenDocumentationPlugin \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_comment_driven_doc_plugin()` | ~6 | ✅ Delegated |
| `factory_task_annotation_policy_plugin()` | none | `PreparedTaskAnnotationPolicy \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_task_annotation_policy_plugin()` | ~6 | ✅ Delegated |
| `factory_task_line_parsing_policy_plugin()` | none | `PreparedTaskLineParsingPolicy \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_task_line_parsing_policy_plugin()` | ~6 | ✅ Delegated |
| `factory_task_traversal_policy_plugin()` | none | `PreparedTaskTraversalPolicy \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_task_traversal_policy_plugin()` | ~6 | ✅ Delegated |
| `factory_variable_extractor_policy_plugin()` | none | `PreparedVariableExtractorPolicy \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_variable_extractor_policy_plugin()` | ~6 | ✅ Delegated |
| `factory_yaml_parsing_policy_plugin()` | none | `YAMLParsingPolicyPlugin \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_yaml_parsing_policy_plugin()` | ~6 | ✅ Delegated |
| `factory_jinja_analysis_policy_plugin()` | none | `JinjaAnalysisPolicyPlugin \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_jinja_analysis_policy_plugin()` | ~6 | ✅ Delegated |
| `factory_audit_plugin()` | none | `VariableDiscoveryPlugin \| None` | Plugin Resolver | Reads: mocks, overrides; Delegates: `_plugin_resolver.factory_audit_plugin()` | ~6 | ✅ Delegated |

**Summary**: 10 plugin resolver methods with uniform pattern (mock → override → delegate to PluginResolver).

---

### Special-Purpose Factory Methods

| Method | Parameters | Return Type | Classification | Data Flow | Lines | Status |
|--------|-----------|-------------|-----------------|-----------|-------|--------|
| `factory_blocker_fact_builder()` | none | `BlockerFactBuilder` (callable) | Factory Pattern | Reads: `_blocker_fact_builder_fn`; Falls back: imports from `scanner_plugins.defaults` | ~10 | ⚙️ Orchestration |

**Note**: This is hybrid between service locator (caches result) and factory pattern (creates callable).

---

### Private Methods & Helpers

| Method | Parameters | Return Type | Classification | Purpose | Lines |
|--------|-----------|-------------|-----------------|---------|-------|
| `_get_registry()` | none | `PluginRegistry` | Plugin Resolver | Validates registry is not None; raises if missing | ~8 |
| `_resolve_platform_key()` | none | `str` | Plugin Resolver | Returns pre-resolved key or delegates to module `resolve_platform_key()` | ~5 |
| `_call_factory_override()` | `name: str` | `object \| None` | DI Orchestration | Executes factory override callable; wraps in error handling | ~15 |
| `_invalidate_scan_option_dependent_cache_locked()` | none | none | Cache Management | Clears feature_detector, variable_discovery from cache | ~4 |

---

### Property Facades (Wave 3 Additions)

| Property | Returns | Delegates To | Classification | Lines |
|----------|---------|--------------|-----------------|-------|
| `policy_manager` | `PolicyManager` | `factory_policy_manager()` | Service Locator | ~3 |
| `policy_registry` | `FallbackPolicyRegistry` | `factory_policy_registry()` | Service Locator | ~3 |

---

### Module-Level Functions (Wave 4 Consolidation)

| Function | Parameters | Returns | Classification | Purpose | Lines |
|----------|-----------|---------|-----------------|---------|-------|
| `ensure_policy_manager()` | `di: DIContainer` | `PolicyManager` | Backward Compat | Delegates to `di.policy_manager`; convenience wrapper | ~20 |
| `ensure_policy_registry()` | `di: DIContainer` | `FallbackPolicyRegistry` | Backward Compat | Delegates to `di.policy_registry`; convenience wrapper | ~20 |
| `resolve_platform_key()` | `scan_options, registry=None` | `str` | Plugin Resolver | Resolves platform key from multiple sources with fallback | ~20 |

---

## Method Classification Breakdown

### DI Container Logic (Orchestration Only)
These methods manage the container's lifecycle, initialization, and cache invalidation:
- `__init__()` — Container initialization
- `replace_scan_options()` — Cache invalidation coordination
- `_invalidate_scan_option_dependent_cache_locked()` — Cache management
- `_call_factory_override()` — Override dispatch
- `inject_mock()` — Testing support
- `clear_mocks()` — Testing support
- `clear_cache()` — Testing support

**Total**: 7 methods, **~70 lines**

### Service Locator (Object Lifecycle)
These manage creation/caching of core singleton services:
- `factory_event_bus()`
- `factory_scanner_context()`
- `factory_variable_discovery()`
- `factory_feature_detector()`
- `factory_variable_row_builder()`
- `factory_policy_registry()`
- `factory_policy_manager()`
- `policy_manager` (property)
- `policy_registry` (property)

**Total**: 9 methods/properties, **~80 lines**

### Plugin Resolver (Registry-Backed)
These delegate to PluginResolver for plugin instantiation:
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
- `_get_registry()` (helper)
- `_resolve_platform_key()` (helper)

**Total**: 12 methods, **~80 lines** (all delegate pattern)

### Factory Pattern (Lightweight Services)
Ephemeral object creation without singleton caching:
- `factory_variable_row_builder()` — Returns new builder each time
- `factory_blocker_fact_builder()` — Caches callable, not instances

**Total**: 2 methods, **~20 lines**

---

## Structural Observations

### Already Extracted Seams ✅
1. **PluginResolver** (`plugin_resolver.py`):
   - Owns: registry validation, platform-key resolution, plugin construction
   - Called by: 10 factory methods in DIContainer (mock/override gatekeeping happens at DIContainer level)
   - Status: Already separate class; DIContainer delegates but controls mock/override logic

2. **ServiceLocator** (`service_locator.py`):
   - Owns: `factory_event_bus()` and placeholder for future service methods
   - Called by: `factory_event_bus()` delegates directly
   - Status: Partial extraction; only EventBus currently delegated

### Potential Refactoring Targets
1. **Consolidate ServiceLocator**: Move all 7 service lifecycle methods into ServiceLocator
   - Impact: 70+ lines moved, cleaner responsibility boundary
   - Risk: Medium (already partially extracted; full move straightforward)

2. **Extract "Override/Mock Gateway"**: Create `MockAndOverrideGateway` class
   - Currently: Every plugin factory checks mocks → overrides → resolver
   - Duplication: 10 identical branches (mock check → override check → delegate)
   - Opportunity: Single centralized gateway reduces boilerplate

3. **Clarify DIContainer Orchestration Role**: 
   - After extraction, DIContainer would own only: cache management, wiring injection, property facades
   - ~30-40 lines of pure orchestration logic

---

## God-Object Risk Assessment

**Current Status**: MODERATE

- ✅ Two responsibilities already extracted (PluginResolver, partial ServiceLocator)
- ⚠️ DIContainer still owns: cache orchestration, mock gateway, override dispatch, object lifetime
- ⚠️ 1000+ lines with multiple concerns interleaved (caching, wiring, delegation, composition)

**Risk Level**: The file is not a god-object yet, but consolidation of remaining service factories into ServiceLocator would make responsibilities clearer.

---

## Call Frequency (From callsite analysis)

| Method | Call Sites | Primary Callers | Frequency |
|--------|-----------|-----------------|-----------|
| `factory_variable_discovery_plugin()` | 3+ | tests, scanner_context | Medium |
| `factory_feature_detection_plugin()` | 3+ | tests, scanner_context | Medium |
| `factory_event_bus()` | 5+ | tests, scanner_context, CLI progress | Medium |
| `factory_scanner_context()` | 2+ | execution_request_builder, tests | Low |
| `factory_variable_discovery()` | 2+ | scanner_context | Low |
| `factory_feature_detector()` | 2+ | scanner_context | Low |
| `factory_variable_row_builder()` | 2+ | tests, variable_discovery | Low |
| `factory_policy_*()` | 3+ | tests, policy_manager | Low |
| All other methods | <1 | rare | Minimal |

**Observation**: Plugin methods and event_bus are accessed most frequently; good candidates for optimization/refactoring.

---

## Extraction Readiness Scorecard

| Criteria | Status | Notes |
|----------|--------|-------|
| All methods identified | ✅ | 18 public + 4 private + 3 module-level = 25 total |
| Classifications clear | ✅ | 7 orchestration, 7 service locator, 12 plugin resolver, 2 factory pattern |
| Boundaries non-overlapping | ✅ | PluginResolver methods have mock gateway at DIContainer; no ambiguity |
| Callsites analyzed | ✅ | 90+ matches across tests and runtime paths |
| Circular dependencies checked | ✅ | PluginResolver/ServiceLocator only reference DIContainer; no back-references |
| Mock/override patterns consistent | ✅ | All 10 plugin methods follow identical mock → override → delegate pattern |

**Conclusion**: DI Container is **EXTRACTION-READY**. Proposed next steps in extraction-boundaries.yaml.
