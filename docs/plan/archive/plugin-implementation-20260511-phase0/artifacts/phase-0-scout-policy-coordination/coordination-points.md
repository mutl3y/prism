# Coordination Points: Policy System Integration Seams

## Overview

This document maps 7 critical coordination points where multiple components interact via policies. These are the "seams" where architecture decisions cascade and where race conditions, ordering issues, or state corruption risks exist.

---

## Coordination Point #1: Bundle Creation → Orchestration Gateway

**Location**: `api_layer/non_collection.py:671-682` + `scanner_plugins/bundle_resolver.py:97-160`

**Components Involved**:
- API entry point (`run_scan()`)
- Plugin facade (`ensure_prepared_policy_bundle()`)
- Bundle resolver (`ensure_prepared_policy_bundle()`)
- Execution request builder
- DI container

**Flow**:
```
run_scan()
  ↓
_ensure_prepared_policy_bundle_for_execution_request()
  ↓ calls
plugin_facade.ensure_prepared_policy_bundle()
  ↓ delegates to
scanner_plugins.bundle_resolver.ensure_prepared_policy_bundle()
  ├→ resolve_task_line_parsing_policy_plugin(di)
  ├→ resolve_task_annotation_policy_plugin(di)
  ├→ resolve_task_traversal_policy_plugin(di)
  ├→ resolve_yaml_parsing_policy_plugin(di)
  ├→ resolve_jinja_analysis_policy_plugin(di)
  └→ resolve_variable_extractor_policy_plugin(di)
  ↓ stores result in
scan_options['prepared_policy_bundle']
```

**Coordination Risk**: **MEDIUM** - Race Condition

**Scenario**:
- Thread A and Thread B both call `run_scan()` simultaneously
- Both reach `ensure_prepared_policy_bundle()`
- If `scan_options` dict is shared, both threads could overwrite bundle

**Current Protection**:
- Unclear; API entry point not documented as thread-safe
- `scan_options` dict is passed by reference in some paths

**Mitigation Required**: YES
- Document thread-safety guarantee or add lock
- Ensure each scan gets isolated `scan_options` dict

**Decision Blocker**: What is the thread-safety contract for `run_scan()`?

---

## Coordination Point #2: Bundle Validation → ScannerContext Initialization

**Location**: `scanner_core/scanner_context.py:229-253` + `scanner_core/scanner_context.py:318-340`

**Components Involved**:
- Bundle resolver (returns PreparedPolicyBundle)
- ScannerContext validator (`_require_prepared_policy_bundle()`)
- ScannerContext initializer
- Policy constants builder

**Flow**:
```
ensure_prepared_policy_bundle()
  ↓ returns
PreparedPolicyBundle dict
  ↓ stored in
scan_options['prepared_policy_bundle']
  ↓
ScannerContext.__init__()
  ├→ _require_prepared_policy_bundle(scan_options)  [Validates bundle shape]
  ├→ check task_line_parsing has required attrs
  ├→ check jinja_analysis callable
  └→ build_policy_constants(prepared_policy_bundle)  [Extract immutable cache]
```

**Coordination Risk**: **LOW** - Ordering Dependency

**Scenario**:
- If ScannerContext is initialized BEFORE bundle creation
- `_require_prepared_policy_bundle()` raises ValueError
- Scan fails with clear error

**Current Protection**: ✅ Explicit validation
- `_require_prepared_policy_bundle()` checks for bundle existence and shape
- Clear error messages if preconditions violated

**Mitigation Required**: NO
- Validation is working correctly
- Ordering contract is enforced

**Decision Made**: Sequential initialization required; error message sufficient

---

## Coordination Point #3: Hotloop Access → Policy Resolution Caching

**Location**: `scanner_extract/task_line_parsing.py` (module-level proxies) + `scanner_core/di_helpers.py:101-113` (require_prepared_policy)

**Components Involved**:
- Policy-backed proxies (`_PolicyBackedCollectionProxy`, `_PolicyBackedRegexProxy`)
- `require_prepared_policy()` resolver
- DI container (accessed with `di=None`)
- Scan options dict

**Flow** (per collection access in hotloop):
```
TASK_INCLUDE_KEYS.__contains__(item)  [called 500+ times per scan]
  ↓
_PolicyBackedCollectionProxy.__contains__()
  ↓
_current_value()
  ↓
require_prepared_policy(None, "task_line_parsing", "task_line_parsing")
  ↓
get_prepared_policy_or_none(None, "task_line_parsing")
  ├→ scan_options_from_di(None)  [Returns None!]
  ├→ attempts dict.get("prepared_policy_bundle")  [On None!]
  └→ Returns None
  ↓ [But requires non-None!]
raise ValueError(...)
```

**Coordination Risk**: **CRITICAL** - Hotloop Inefficiency + Design Flaw

**Scenario**:
- Module-level proxy is instantiated at import time
- Proxy stores `policy_attr_name = "TASK_INCLUDE_KEYS"`
- When `TASK_INCLUDE_KEYS.__contains__()` is called with `di=None`, resolver cannot access scan_options
- Resolver fails or returns None

**Current Implementation Issue**:
```python
# Line 19 in task_line_parsing.py
TASK_INCLUDE_KEYS: Collection[str] = _PolicyBackedCollectionProxy("TASK_INCLUDE_KEYS")

# When used: "task" in TASK_INCLUDE_KEYS
# Calls: _current_value()
# Which calls: require_prepared_policy(None, "task_line_parsing", ...)
# Which calls: get_prepared_policy_or_none(None, "task_line_parsing")
# Which fails because di=None and cannot find scan_options
```

**Expected vs. Actual**:
- Expected: Proxy resolves task_line_parsing policy from ScannerContext or DI
- Actual: Proxy passes `di=None`, resolver cannot find DI context

**Root Cause**: Proxy is created at module level; no DI context available at that time

**Mitigation Required**: YES (CRITICAL)
- Option 1: Cache policy in ScannerContext.policy_constants (recommended)
- Option 2: Modify proxy to accept DI context at access time
- Option 3: Pre-populate module-level cache during ScannerContext init

**Decision Blocker**: How should hotloop policies be cached?

---

## Coordination Point #4: Fallback Registry Resolution → Policy Consistency

**Location**: `scanner_io/loader.py:93-120` (with fallback registry)

**Components Involved**:
- Loader module
- Registry resolver (`_resolve_policy_with_registry()`)
- Fallback plugin registry
- Bundle resolver

**Flow**:
```
_get_yaml_parsing_policy(di=None)
  ├→ Try: get_prepared_policy_or_none(di, "yaml_parsing")
  │         ↓ Returns policy if found
  │
  └→ Except: Invoke fallback registry
             ├→ _resolve_policy_with_registry(resolver, di)
             │   ├→ If di has plugin_registry: use it
             │   └→ Else: use global fallback registry
             ↓
             Return resolved policy
```

**Coordination Risk**: **MEDIUM** - Policy Consistency

**Scenario**:
- Thread A: Uses policy from prepared_policy_bundle (immutable, pre-resolved)
- Thread B: Uses policy from fallback registry (could be mutable, dynamic)
- Both threads working on same scan, different policy instances
- Policy behavior inconsistent between threads

**Current Protection**:
- Fallback registry is read-only (no mutation documented)
- But type system doesn't enforce immutability

**Mitigation Required**: YES
- Audit all fallback registry usage paths
- Ensure fallback and prepared_policy_bundle return equivalent policies
- Consider caching fallback result in bundle

**Decision Blocker**: Is fallback registry the only place where dynamic policy resolution happens?

---

## Coordination Point #5: Plugin Factory Initialization → DI Ownership Transfer

**Location**: `scanner_core/di_helpers.py` + `scanner_core/scanner_context.py` + plugin factories

**Components Involved**:
- DI container (DIContainer)
- Variable discovery plugin factory
- Feature detection plugin factory
- Scan options dict with prepared_policy_bundle

**Flow**:
```
DIContainer(scan_options=options)
  ├→ stores scan_options in self.scan_options
  ├→ factory_variable_discovery_plugin() called
  │   ├→ VariableDiscoveryPlugin(di=container)
  │   └→ Plugin receives di with scan_options
  │
  └→ factory_feature_detection_plugin() called
      ├→ FeatureDetectionPlugin(di=container)
      └→ Plugin receives di with scan_options

During scan execution:
  Plugin accesses: prepared_policy_bundle = di.scan_options.get("prepared_policy_bundle")
  ↓
  If scan_options is mutated by another thread/component, plugin sees stale bundle
```

**Coordination Risk**: **MEDIUM** - State Mutation

**Scenario**:
- Plugin initialized with DI container at time T1
- Plugin caches reference to `di.scan_options`
- At time T2, APILayer updates `di.scan_options["prepared_policy_bundle"]` = new_bundle
- Plugin still references old bundle; behavior diverges

**Current Protection**:
- Deep-copy of bundle stored in scan_options by scan_request
- But DI container holds reference, not copy

**Mitigation Required**: YES
- Document whether plugins should cache or re-read policy
- Consider immutable bundle contract

**Decision Blocker**: Are plugins expected to re-read policy on each operation, or cache at initialization?

---

## Coordination Point #6: Policy Constants Extraction → Hotloop Cache

**Location**: `scanner_core/scanner_context.py:340` + `scanner_data/policy_constants.py`

**Components Involved**:
- ScannerContext initializer
- Policy constants builder
- Module-level proxy accessors

**Flow**:
```
ScannerContext.__init__()
  ├→ if prepared_policy_bundle:
  │    policy_constants = build_policy_constants(prepared_policy_bundle)
  │    self.policy_constants = policy_constants
  │
  └→ Now: TASK_INCLUDE_KEYS could read from:
         Option A: self.policy_constants.task_include_keys (cache)
         Option B: require_prepared_policy(...) (dynamic)
```

**Coordination Risk**: **LOW** - Cache Consistency

**Scenario**:
- Module-level TASK_INCLUDE_KEYS proxy NOT updated during ScannerContext init
- Hotloop code still calls require_prepared_policy() instead of using policy_constants cache
- Performance opportunity missed

**Current Protection**:
- None; proxies don't know about policy_constants cache
- Hotloop still resolves policy dynamically

**Mitigation Required**: YES (PERFORMANCE)
- Inject policy_constants into proxies at ScannerContext init
- Or: Switch hotloop code to access self.policy_constants instead

**Decision Blocker**: Should module-level proxies be updated with cache, or should hotloop code be refactored to use ScannerContext cache?

---

## Coordination Point #7: Cache Invalidation → Bundle Fingerprint Staleness

**Location**: `api_layer/non_collection.py:507-523` (cache marker computation)

**Components Involved**:
- Cache marker function (`_prepared_policy_bundle_cache_marker()`)
- Bundle fingerprint computation
- Scan result caching layer

**Flow**:
```
run_scan()
  ├→ Compute bundle fingerprint: _prepared_policy_bundle_cache_marker(scan_options)
  │   ├→ Extract prepared_policy_bundle
  │   ├→ Compute fingerprint of all bundle values
  │   └→ Return fingerprint for cache key
  │
  ├→ Execute scan with this bundle
  │   (During execution, if bundle is mutated, fingerprint becomes stale)
  │
  └→ Cache scan results under fingerprint key
      (If fingerprint was stale, wrong cache entry reused next scan)
```

**Coordination Risk**: **MEDIUM** - Cache Invalidation

**Scenario**:
- Bundle fingerprint computed at T1 with values V1
- During scan execution, bundle is mutated to V2
- Scan completes with V2 results
- Cache stored under key derived from V1
- Next scan with V2: Cache key differs, but bundle values same; stale cache not invalidated

**Current Protection**:
- Deep-copy of bundle prevents mutations visible to cache layer
- Fingerprint computed upfront before mutation window

**Mitigation Required**: YES (LOW PRIORITY)
- Document when cache invalidation occurs
- Consider periodic fingerprint re-computation if mutation possible

**Decision Blocker**: Is bundle mutation during scan execution possible, and if so, when should cache be invalidated?

---

## Coordination Summary Table

| Point | Risk Level | Type | Current Protection | Mitigation | Blocker |
|-------|-----------|------|-------------------|-----------|---------|
| #1: Bundle Creation | MEDIUM | Race Condition | None | Add lock or isolate scan_options | YES - Thread-safety contract |
| #2: Bundle Validation | LOW | Ordering | Explicit validation | None needed | NO |
| #3: Hotloop Access | CRITICAL | Inefficiency | None | Cache in policy_constants | YES - Hotloop strategy |
| #4: Fallback Registry | MEDIUM | Inconsistency | Read-only assumption | Audit all paths | YES - Fallback audit |
| #5: Plugin Factory | MEDIUM | State Mutation | Deep-copy | Document cache policy | YES - Plugin contract |
| #6: Policy Constants | LOW | Cache Opportunity | Missed optimization | Refactor hotloop access | YES - Cache strategy |
| #7: Cache Invalidation | MEDIUM | Staleness | Deep-copy safety | Document triggers | YES - Invalidation contract |

---

## Blocking Decisions Required

1. **Bundle Immutability**: Should prepared_policy_bundle be immutable after creation? (Affects #3, #5, #7)
2. **Thread-Safety Contract**: Is run_scan() thread-safe? (Affects #1)
3. **Hotloop Strategy**: How should 500+ policy accesses in inner loops be cached? (Affects #3, #6)
4. **Plugin Contract**: Should plugins cache policy or re-read on each operation? (Affects #5)
5. **Fallback Audit**: Are there other fallback registry paths besides scanner_io/loader.py? (Affects #4)

---

## Recommended Coordination Improvements

1. Make PreparedPolicyBundle immutable (freeze after creation)
2. Add lock to bundle creation in orchestrator
3. Cache hotloop policies in ScannerContext.policy_constants
4. Document thread-safety guarantees in run_scan()
5. Audit all fallback registry paths
6. Define cache invalidation triggers explicitly
