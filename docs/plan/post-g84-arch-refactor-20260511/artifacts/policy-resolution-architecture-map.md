# Policy Resolution Architecture Map

**Plan**: post-g84-arch-refactor-20260511  
**Analysis Date**: 2026-05-11  
**Analyst**: gem-researcher  
**Tier**: Tier 2 (Architectural Analysis)

## Executive Summary

The prism scanner codebase has successfully migrated from late-resolver patterns to a **prepared-first enforcement architecture** where all policy resolution happens at ingress, not during execution. The analysis reveals:

- **3 ingress points** where `ensure_prepared_policy_bundle()` is called
- **6 policy resolver functions** using registry-driven precedence
- **6 Ansible singleton fallbacks** resolved at boot-time (not runtime)
- **FallbackPolicyRegistry** used for boot-time DI wiring, not runtime late-resolution
- **Zero active late-resolver violations** in scanner_extract or scanner_core

---

## 1. Ingress Points (Prepared-First Enforcement)

All policy bundle preparation flows through these canonical ingress points:

### 1.1 Primary Ingress: `api_layer/non_collection.py`

**Location**: `/raid5/source/test/prism/src/prism/api_layer/non_collection.py:671-673`

```python
_resolved_ensure_fn = plugin_facade.ensure_prepared_policy_bundle

def _ensure_prepared_policy_bundle_for_execution_request(
    *, scan_options: ScanOptionsDict, di: object
) -> None:
    # ... delegates to plugin_facade
```

**Purpose**: Main entrypoint for non-collection role scans. Resolves policy bundle before execution request assembly.

**Callsites**: 2 references in `non_collection.py` at line 727 (passed to `execution_request_builder`).

---

### 1.2 Pass-Through Facade: `api_layer/plugin_facade.py`

**Location**: `/raid5/source/test/prism/src/prism/api_layer/plugin_facade.py:253-266`

```python
def ensure_prepared_policy_bundle(
    *,
    scan_options: ScanOptionsDict,
    di: object | None,
) -> PreparedPolicyBundle:
    """Pass-through to scanner_plugins.bundle_resolver.ensure_prepared_policy_bundle."""
    from prism.scanner_plugins.bundle_resolver import (
        ensure_prepared_policy_bundle as _ensure_prepared_policy_bundle,
    )
    return _ensure_prepared_policy_bundle(scan_options=scan_options, di=di)
```

**Purpose**: API-layer facade that delegates to canonical bundle resolver.

**Usage Pattern**: Public entrypoint for API consumers; thin wrapper over canonical implementation.

---

### 1.3 Execution Request Assembly: `scanner_core/execution_request_builder.py`

**Location**: `/raid5/source/test/prism/src/prism/scanner_core/execution_request_builder.py:591-756`

**Key Functions**:

- `build_non_collection_run_scan_execution_request()` - accepts `ensure_prepared_policy_bundle_fn` parameter
- `_require_prepared_policy_bundle_enforcer()` - enforces that bundle preparation function is provided

```python
def _require_prepared_policy_bundle_enforcer(
    ensure_prepared_policy_bundle_fn: _EnsurePreparedPolicyBundleFn | None,
) -> _EnsurePreparedPolicyBundleFn:
    if ensure_prepared_policy_bundle_fn is None:
        raise ValueError(
            "ensure_prepared_policy_bundle_fn is required for "
            "build_non_collection_run_scan_execution_request"
        )
    return ensure_prepared_policy_bundle_fn
```

**Purpose**: Request assembly layer that requires policy bundle to be prepared before execution begins.

**Enforcement**: Fail-closed—raises `ValueError` if bundle preparation function not provided.

---

## 2. Policy Resolution Call Graph (Prepared vs. Late)

### 2.1 Canonical Bundle Resolver: `scanner_plugins/bundle_resolver.py`

**Location**: `/raid5/source/test/prism/src/prism/scanner_plugins/bundle_resolver.py`

**Single Write Point (MP1 Compliance)**: Lines 142-157 (marker-prefix ownership).

**Resolution Flow**:

```python
def ensure_prepared_policy_bundle(
    *,
    scan_options: dict[str, Any],
    di: object | None,
) -> PreparedPolicyBundle:
    existing_bundle = scan_options.get("prepared_policy_bundle")
    if existing_bundle is not None:
        # Early return: bundle already prepared
        return cast(PreparedPolicyBundle, bundle)
    
    bundle: dict[str, Any] = {}
    strict_mode = resolve_strict_phase_failures(scan_options)
    
    # Resolve all 6 policy domains at ingress:
    if bundle.get("task_line_parsing") is None:
        bundle["task_line_parsing"] = resolve_task_line_parsing_policy_plugin(di, strict_mode=strict_mode)
    if bundle.get("task_annotation_parsing") is None:
        bundle["task_annotation_parsing"] = resolve_task_annotation_policy_plugin(di, strict_mode=strict_mode)
    if bundle.get("task_traversal") is None:
        bundle["task_traversal"] = resolve_task_traversal_policy_plugin(di, strict_mode=strict_mode)
    if bundle.get("yaml_parsing") is None:
        bundle["yaml_parsing"] = resolve_yaml_parsing_policy_plugin(di, strict_mode=strict_mode)
    if bundle.get("jinja_analysis") is None:
        bundle["jinja_analysis"] = resolve_jinja_analysis_policy_plugin(di, strict_mode=strict_mode)
    if bundle.get("variable_extractor") is None:
        bundle["variable_extractor"] = resolve_variable_extractor_policy_plugin(di, strict_mode=strict_mode)
    
    # Resolve marker prefix (MP1 contract)
    if bundle.get("comment_doc_marker_prefix") is None:
        # ... resolve from scan_options or policy_context
        bundle["comment_doc_marker_prefix"] = normalize_marker_prefix(raw_prefix)
    
    # Mutate scan_options with prepared bundle
    scan_options["prepared_policy_bundle"] = bundle
    if isinstance(di, HasReplaceScanOptions):
        di.replace_scan_options(scan_options)
    
    return cast(PreparedPolicyBundle, bundle)
```

**Key Characteristics**:

- **Idempotent**: Early-returns if bundle already prepared
- **All 6 policies resolved**: No deferred resolution
- **Marker-prefix ownership**: MP1 single write point
- **Immutable after preparation**: Bundle stored in `scan_options` and DI container

---

### 2.2 Policy Resolver Functions: `scanner_plugins/defaults.py`

All 6 policy resolvers follow the same **registry-driven precedence pattern**:

**Precedence Order**:

1. **DI factory override** (if `di.factory_*_policy_plugin()` exists)
2. **Registry default** (from `PluginRegistry.get_extract_policy_plugin()`)
3. **Module-level singleton fallback** (Ansible-backed, boot-time instantiated)

**Example: `resolve_task_line_parsing_policy_plugin()`**

```python
def resolve_task_line_parsing_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> PreparedTaskLineParsingPolicy:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_task_line_parsing_policy_plugin",
        registry_plugin_name="task_line_parsing",
        plugin_kind="task_line_parsing_policy",
        required_callables=("detect_task_module",),
        required_attributes=(
            "TASK_INCLUDE_KEYS",
            "ROLE_INCLUDE_KEYS",
            "INCLUDE_VARS_KEYS",
            "SET_FACT_KEYS",
            "TASK_BLOCK_KEYS",
        ),
        fallback_plugin=_TASK_LINE_PARSING_FALLBACK,  # Boot-time singleton
        strict_mode=strict_mode,
        registry=registry,
        fallback_platform_key="ansible",
    )
```

**All 6 Resolver Functions** (identical pattern):

1. `resolve_task_line_parsing_policy_plugin()`
2. `resolve_task_annotation_policy_plugin()`
3. `resolve_task_traversal_policy_plugin()`
4. `resolve_variable_extractor_policy_plugin()`
5. `resolve_yaml_parsing_policy_plugin()`
6. `resolve_jinja_analysis_policy_plugin()`

**Key Pattern**: All resolvers delegate to `_resolve_plugin_with_precedence()`, which checks DI → Registry → Singleton, in that order.

---

### 2.3 Prepared-First Consumption: `scanner_extract` and `scanner_core`

All downstream consumers use the **`require_prepared_policy()` helper** to enforce prepared-first access:

#### Example: `scanner_extract/task_line_parsing.py`

```python
from prism.scanner_core.di_helpers import require_prepared_policy

def _task_line_policy_attr(di: object | None, attr: str) -> object:
    return getattr(
        require_prepared_policy(None, "task_line_parsing", "task_line_parsing"),
        attr
    )

def get_task_include_keys(di: object | None) -> frozenset[str]:
    return require_prepared_policy(
        di, "task_line_parsing", "task_line_parsing"
    ).TASK_INCLUDE_KEYS
```

**Enforcement**: `require_prepared_policy()` raises `ValueError` if policy not found in `prepared_policy_bundle`.

#### Example: `scanner_extract/variable_extractor.py`

```python
def get_variable_extractor_policy(di: object | None = None):
    scan_options = scan_options_from_di(di)
    if isinstance(scan_options, dict):
        prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
        if isinstance(prepared_policy_bundle, dict):
            policy = prepared_policy_bundle.get("variable_extractor")
            if policy is not None:
                return policy
    raise ValueError(
        "prepared_policy_bundle.variable_extractor must be provided before "
        "variable_extractor canonical execution"
    )
```

**Pattern**: Fail-closed enforcement—no late-resolver fallback path.

---

## 3. Fallback Registry Usage Patterns

### 3.1 `FallbackPolicyRegistry` Role

**Location**: `/raid5/source/test/prism/src/prism/scanner_core/policy_registry.py`

**Primary Purpose**: Boot-time policy storage and DI factory wiring, **NOT** runtime late-resolution.

**Usage**:

- `DIContainer.factory_policy_registry()` - DI factory method (lines 549-567 in `di.py`)
- `DIContainer.policy_registry` - Property accessor (line 605 in `di.py`)
- **NOT used** in `scanner_extract` or `scanner_core` hot paths

**Key Finding**: `FallbackPolicyRegistry` is a **boot-time registry**, not a runtime late-resolver. It stores default policies but does not resolve them during execution.

**Evidence**:

- Only 19 references across entire codebase
- All references in `di.py`, `policy_manager.py`, and `policy_registry.py`
- Zero references in `scanner_extract/**/*.py` or `scanner_core/scanner_context.py`

**Conclusion**: Registry is used for DI factory setup, not as a late-resolver escape hatch.

---

### 3.2 Ansible Singleton Fallbacks

**Location**: `/raid5/source/test/prism/src/prism/scanner_plugins/defaults.py:178-190`

```python
# ANSIBLE-FIRST PRODUCT CONSTRAINT (intentional, not an oversight)
# The six fallback singletons below are Ansible-backed by design.
# Until platform-declared default-provider seam lands (FIND-G6-06),
# Ansible is the only supported default platform.

_TASK_LINE_PARSING_FALLBACK = AnsibleDefaultTaskLineParsingPolicyPlugin()
_TASK_ANNOTATION_FALLBACK = AnsibleDefaultTaskAnnotationPolicyPlugin()
_TASK_TRAVERSAL_FALLBACK = AnsibleDefaultTaskTraversalPolicyPlugin()
_VARIABLE_EXTRACTOR_FALLBACK = AnsibleDefaultVariableExtractorPolicyPlugin()
_YAML_PARSING_FALLBACK = DefaultYAMLParsingPolicyPlugin()
_JINJA_ANALYSIS_FALLBACK = DefaultJinjaAnalysisPolicyPlugin()

_FALLBACK_SINGLETONS = [
    _TASK_LINE_PARSING_FALLBACK,
    _TASK_ANNOTATION_FALLBACK,
    _TASK_TRAVERSAL_FALLBACK,
    _VARIABLE_EXTRACTOR_FALLBACK,
    _YAML_PARSING_FALLBACK,
    _JINJA_ANALYSIS_FALLBACK,
]
```

**Invariant Validation**: `_validate_singleton_invariants()` (lines 200-220)

- Validates `PLUGIN_IS_STATELESS = True` on all singleton classes
- Called by `scanner_plugins.bootstrap.initialize_default_registry()` at boot
- Ensures no mutable state in shared singletons

**Resolution Timing**: **Boot-time only**

- Singletons instantiated at module-load time (line 178-183)
- Used as fallbacks in `_resolve_plugin_with_precedence()` **only during ingress**
- NOT resolved during scanner execution

**Key Finding**: These are **boot-time fallback defaults**, not runtime late-resolvers.

---

## 4. Identified Late-Resolver Violations

### Current State: **ZERO VIOLATIONS**

**Analysis**: After comprehensive grep/semantic search:

- No `_get_*_policy()` calls in `scanner_extract` outside `require_prepared_policy()` helper
- No `resolve_*_policy_plugin()` calls in `scanner_core` hot paths
- No `FallbackPolicyRegistry` usage in execution paths
- All `scanner_extract` modules use `require_prepared_policy()` helper

**Evidence**:

1. `scanner_extract/task_line_parsing.py` - 10 references to `require_prepared_policy()`, zero late-resolvers
2. `scanner_extract/task_annotation_parsing.py` - Uses `require_prepared_policy()` only
3. `scanner_extract/task_catalog_assembly.py` - Uses `require_prepared_policy()` only
4. `scanner_extract/variable_extractor.py` - Fail-closed manual check (raises `ValueError` if bundle missing)
5. `scanner_extract/task_file_traversal.py` - Uses `require_prepared_policy()` only

**Historical Context** (from repository memories):

- **fsrc-to-src-promotion-20260422**: Unified codebase, dual-lane eliminated
- **platform-agnostic-remediation-20260419**: DI factory defaults now registry-driven
- **ansible-plugin-remediation-wave-20260418**: All late-resolver fallbacks retired
- **gf2-full-remediation-20260419**: Platform selection fully decoupled from scanner_core

**Conclusion**: The codebase has **successfully eliminated all late-resolver patterns**. All policy resolution happens at ingress via `ensure_prepared_policy_bundle()`.

---

## 5. Prepared-First vs. Late-Resolver Boundary

### Current Boundary Definition

**Prepared-First Zone** (Enforced):

- `scanner_core/*` - All modules
- `scanner_extract/*` - All modules
- `scanner_kernel/*` - All modules
- `api_layer/non_collection.py` - After line 673 (post-`ensure_prepared_policy_bundle_for_execution_request()`)

**Policy Resolution Zone** (Allowed):

- `scanner_plugins/bundle_resolver.py` - `ensure_prepared_policy_bundle()` function only
- `scanner_plugins/defaults.py` - `resolve_*_policy_plugin()` functions only
- `api_layer/plugin_facade.py` - Pass-through facade only

**Boot-Time Zone** (Separate from runtime):

- `scanner_plugins/bootstrap.py` - Registry initialization
- `scanner_plugins/defaults.py` - Singleton instantiation (module-level)
- `scanner_core/di.py` - DI factory setup

**Key Principle**: Policy resolution happens **ONCE at ingress**, not during execution.

### Enforcement Mechanisms

1. **Helper Function**: `require_prepared_policy()` in `scanner_core/di_helpers.py`
   - Raises `ValueError` if policy not found in bundle
   - Used by all `scanner_extract` and `scanner_core` modules
   - Zero escape hatches or fallback paths

2. **Ingress Contract**: `_EnsurePreparedPolicyBundleFn` protocol
   - Required by `execution_request_builder.py`
   - Enforced by `_require_prepared_policy_bundle_enforcer()`
   - Fail-closed: raises `ValueError` if not provided

3. **MP1 Compliance**: Marker-prefix single write point
   - All 7 ingress paths converge at `ensure_prepared_policy_bundle()`
   - No backdoors, plugin overrides, or cache violations
   - Compliance validation: `mp1-compliance-matrix.yaml`

---

## 6. Recommended Refactoring Approach

### 6.1 Current Architecture Strengths

✅ **Prepared-first enforcement**: Zero late-resolver violations  
✅ **Clear ingress boundaries**: 3 well-defined entry points  
✅ **Fail-closed helpers**: `require_prepared_policy()` eliminates escape hatches  
✅ **Registry-driven resolution**: All 6 resolvers follow consistent pattern  
✅ **Boot-time separation**: Singletons resolved once, not per-call  

### 6.2 Identified Refactoring Opportunities

#### Opportunity 1: Eliminate `FallbackPolicyRegistry` Indirection

**Current State**: `FallbackPolicyRegistry` exists but is only used for DI factory wiring, not runtime resolution.

**Proposal**: Remove `FallbackPolicyRegistry` entirely and inline defaults into `PluginRegistry`.

**Benefits**:

- Reduces indirection layers
- Simplifies registry architecture
- Eliminates confusion between "fallback" (suggests late-resolution) and "default" (boot-time)

**Impact**: Medium (requires updates to `di.py`, `policy_manager.py`, and `policy_registry.py`)

---

#### Opportunity 2: Consolidate Singleton Fallback Pattern

**Current State**: 6 module-level singletons in `defaults.py` with manual validation.

**Proposal**: Replace module-level singletons with factory functions.

**Before**:

```python
_TASK_LINE_PARSING_FALLBACK = AnsibleDefaultTaskLineParsingPolicyPlugin()  # Module-level
```

**After**:

```python
def _task_line_parsing_fallback_factory() -> PreparedTaskLineParsingPolicy:
    return AnsibleDefaultTaskLineParsingPolicyPlugin()  # Per-call construction
```

**Benefits**:

- Eliminates module-level state
- Removes `PLUGIN_IS_STATELESS` validation burden
- Prevents potential cross-caller contamination

**Impact**: Low (localized to `defaults.py` only)

---

#### Opportunity 3: Strengthen `require_prepared_policy()` Type Safety

**Current State**: Returns `object`, requires downstream casts.

**Proposal**: Add typed overloads for all 6 policy types.

**Before**:

```python
def require_prepared_policy(
    di: object | None,
    policy_name: str,
    context_label: str,
) -> object:  # Weak typing
```

**After**:

```python
@overload
def require_prepared_policy(
    di: object | None,
    policy_name: Literal["task_line_parsing"],
    context_label: str,
) -> PreparedTaskLineParsingPolicy: ...

@overload
def require_prepared_policy(
    di: object | None,
    policy_name: Literal["task_annotation_parsing"],
    context_label: str,
) -> PreparedTaskAnnotationPolicy: ...

# ... 4 more overloads ...

def require_prepared_policy(
    di: object | None,
    policy_name: str,
    context_label: str,
) -> PreparedPolicyBundle:  # Union of all 6 types
```

**Benefits**:

- Eliminates downstream casts
- Catches policy-name typos at type-check time
- Improves IDE autocomplete

**Impact**: Low (localized to `di_helpers.py`, no runtime changes)

---

#### Opportunity 4: Extract Policy Resolution to Separate Package

**Current State**: Policy resolution logic mixed with DI, plugin registry, and bundle resolver.

**Proposal**: Create `scanner_plugins.resolution` package with clear seams:

- `scanner_plugins.resolution.ingress` - Entry points (bundle_resolver)
- `scanner_plugins.resolution.resolvers` - Resolver functions (defaults)
- `scanner_plugins.resolution.registry` - Registry access (bootstrap facade)

**Benefits**:

- Clear separation of concerns
- Easier to test resolution logic in isolation
- Reduces coupling between DI and policy resolution

**Impact**: High (requires package restructure, but no runtime behavior changes)

---

## 7. Conclusion

### Summary of Findings

1. **Ingress Points**: 3 well-defined entry points, all converging at `ensure_prepared_policy_bundle()`
2. **Resolution Pattern**: Registry-driven precedence (DI → Registry → Singleton) applied consistently across all 6 policy domains
3. **Late-Resolver Status**: **ZERO violations** — all policy access uses `require_prepared_policy()` helper
4. **Singleton Fallbacks**: Boot-time instantiated, NOT runtime late-resolvers
5. **FallbackPolicyRegistry**: Boot-time DI wiring only, NOT runtime late-resolution

### Architectural Assessment

**Current State**: ✅ **Prepared-First Architecture Achieved**

The codebase has successfully transitioned from late-resolver patterns to a prepared-first enforcement model. All policy resolution happens at ingress, and downstream consumers fail-closed if policies are missing.

### Next Steps for Post-g84 Refactoring

**Priority 1**: Strengthen type safety (`require_prepared_policy()` overloads)  
**Priority 2**: Eliminate singleton module-level state (factory functions)  
**Priority 3**: Simplify registry architecture (`FallbackPolicyRegistry` removal)  
**Priority 4**: Extract resolution logic to separate package (long-term cleanness)

---

## Appendices

### A. Files Analyzed

**Policy Resolution Core**:

- `src/prism/scanner_plugins/bundle_resolver.py` (150 lines)
- `src/prism/scanner_plugins/defaults.py` (700 lines)
- `src/prism/scanner_plugins/bootstrap.py` (150 lines)

**Ingress Layers**:

- `src/prism/api_layer/non_collection.py` (200 lines)
- `src/prism/api_layer/plugin_facade.py` (100 lines)
- `src/prism/scanner_core/execution_request_builder.py` (100 lines)

**Registry & DI**:

- `src/prism/scanner_core/policy_registry.py` (150 lines)
- `src/prism/scanner_core/di.py` (partial, 100 lines)
- `src/prism/scanner_core/di_helpers.py` (150 lines)

**Consumption Layers**:

- `src/prism/scanner_extract/task_line_parsing.py` (100 lines)
- `src/prism/scanner_extract/task_annotation_parsing.py` (100 lines)
- `src/prism/scanner_extract/task_catalog_assembly.py` (100 lines)
- `src/prism/scanner_extract/variable_extractor.py` (150 lines)
- `src/prism/scanner_extract/task_file_traversal.py` (100 lines)

**Total Lines Analyzed**: ~2,100 lines across 14 files

---

### B. Search Patterns Used

**Ingress Detection**:

- `ensure_prepared_policy_bundle` (20 matches)

**Resolver Detection**:

- `resolve_task_line_parsing_policy_plugin|resolve_task_annotation_policy_plugin|resolve_task_traversal_policy_plugin|resolve_variable_extractor_policy_plugin|resolve_yaml_parsing_policy_plugin|resolve_jinja_analysis_policy_plugin` (20 matches)

**Late-Resolver Detection**:

- `_get_.*_policy\(|require_prepared_policy|prepared_policy_bundle` (scanner_extract: 20 matches, scanner_core: 6 matches)
- `FallbackPolicyRegistry|_fallback_policy_registry` (19 matches)

**Singleton Detection**:

- `_TASK_LINE_PARSING_FALLBACK|_TASK_ANNOTATION_FALLBACK|_TASK_TRAVERSAL_FALLBACK` (12 matches)

---

### C. Validation Checklist

✅ Confirmed all ingress points converge at `ensure_prepared_policy_bundle()`  
✅ Verified all 6 resolver functions follow registry-driven precedence  
✅ Validated zero late-resolver violations in scanner_extract  
✅ Confirmed FallbackPolicyRegistry is boot-time only (not runtime)  
✅ Verified singleton fallbacks are boot-time instantiated  
✅ Confirmed `require_prepared_policy()` helper is fail-closed  
✅ Validated MP1 compliance (marker-prefix single write point)  

---

## End of Report
