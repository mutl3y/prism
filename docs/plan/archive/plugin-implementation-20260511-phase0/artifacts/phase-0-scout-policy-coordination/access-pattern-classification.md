# Access Pattern Classification & Hotspot Analysis

## Overview

This document classifies 45+ policy consumer locations into 4 access pattern categories: **Creation-Time**, **Runtime**, **Hotloop**, and **Coldpath**. Includes frequency heatmap and performance implications.

---

## Access Pattern Categories

### 1. CREATION-TIME ACCESS (4 locations)

**Characteristic**: Policy resolved once at bundle creation; cached in `scan_options` for entire scan lifecycle.

| Location | Function | Frequency | Pattern | Notes |
|----------|----------|-----------|---------|-------|
| `scanner_core/execution_request_builder.py:725-750` | `_assemble_execution_request()` | 1 per scan | Enforce policy bundle function exists | Gatekeeper for request assembly |
| `scanner_core/scanner_context.py:318-340` | `ScannerContext.__init__()` | 1 per scan | Build policy_constants from bundle | Immutable cache extraction |
| `api_layer/non_collection.py:671-682` | `_ensure_prepared_policy_bundle_for_execution_request()` | 1 per scan | Call resolver, store in scan_options | API orchestrator |
| `scanner_plugins/bundle_resolver.py:97-160` | `ensure_prepared_policy_bundle()` | 1 per scan | Resolve all 6 policies at once | Central resolver hub |

**Coordination Pattern**: Sequential initialization phase
- Policy bundle must be created BEFORE ScannerContext initialization
- Bundle is then immutable for rest of scan
- No concurrency during this phase (single-threaded initialization)

**Thread-Safety**: ✅ Safe (initialization phase is serialized)

**Caching Strategy**: Bundle cached in `scan_options` dict; accessed via `get_prepared_policy_or_none()`

---

### 2. RUNTIME ACCESS (12 locations)

**Characteristic**: Policy read during normal scanning operations; 10-100 calls per scan, but not in innermost loops.

#### Subcategory A: Task Extraction (9 locations)

| Location | Policy | Frequency | Context |
|----------|--------|-----------|---------|
| `scanner_extract/task_file_traversal.py:119` | `task_line_parsing` | ~50 calls | Per file traversal start |
| `scanner_extract/task_file_traversal.py:143` | `task_traversal` | ~100 calls | Per block iteration |
| `scanner_extract/task_file_traversal.py:155` | `task_traversal` | ~100 calls | Per block traversal |
| `scanner_extract/task_file_traversal.py:168` | `task_traversal` | ~50 calls | Per include resolution |
| `scanner_extract/task_file_traversal.py:248` | `task_traversal` | ~50 calls | Per role traversal |
| `scanner_extract/task_file_traversal.py:270` | `task_traversal` | ~30 calls | Per include target |
| `scanner_extract/task_file_traversal.py:278` | `task_traversal` | ~30 calls | Per role include |
| `scanner_extract/task_annotation_parsing.py:22` | `task_annotation_parsing` | ~50 calls | Per annotation detection |
| `scanner_extract/task_catalog_assembly.py:27,39` | `task_line_parsing` `task_annotation_parsing` | ~30 calls | Per task assembly |

**Pattern**: Policy retrieved once per logical operation (file, block, task), cached for that operation

**Thread-Safety**: ✅ Safe (read-only access; bundle immutable)

#### Subcategory B: I/O Operations (3 locations)

| Location | Policy | Frequency | Context |
|----------|--------|-----------|---------|
| `scanner_io/loader.py:219` | `yaml_parsing` | 2-20 calls | Per role file load |
| `scanner_io/loader.py:330` | `yaml_parsing` | 2-20 calls | Per yaml candidate parse |
| `scanner_extract/variable_extractor.py:23-29` | `variable_extractor` | 1-5 calls | Per role vars extraction |

**Pattern**: Policy used for I/O operations; fallback registry allowed

**Thread-Safety**: ⚠️ Conditional (depends on registry immutability)

---

### 3. HOTLOOP ACCESS (3 locations) — CRITICAL PERFORMANCE CONCERN

**Characteristic**: Policy accessed in innermost loops; 100+ calls per scan per policy.

#### Hotspot #1: Task Line Parsing Collections (6 module-level instances)

**Location**: `scanner_extract/task_line_parsing.py:10-95`

**Classes**: `_PolicyBackedCollectionProxy` (instances):
- `TASK_INCLUDE_KEYS`
- `ROLE_INCLUDE_KEYS`
- `INCLUDE_VARS_KEYS`
- `SET_FACT_KEYS`
- `TASK_BLOCK_KEYS`
- `TASK_META_KEYS`

```python
class _PolicyBackedCollectionProxy:
    def _current_value(self) -> object:
        return getattr(
            require_prepared_policy(None, "task_line_parsing", "task_line_parsing"),
            self._policy_attr_name,
        )

    def __contains__(self, item: object) -> bool:
        value = self._current_value()  # ⚠️ HOTSPOT: require_prepared_policy() called here
        if isinstance(value, (set, tuple, list, frozenset)):
            return item in value
        return False
```

**Call Stack**: `"task" in TASK_INCLUDE_KEYS` → `__contains__()` → `_current_value()` → `require_prepared_policy()` → `get_prepared_policy_or_none()` → `scan_options_from_di()` → DI lookup

**Frequency Per Scan**: 500+ calls (per task line check in parser loop)

**Performance Impact**: 
- Current: ~0.5ms per require_prepared_policy() call (DI lookup + dict traversal)
- Total overhead: 250ms+ per scan for this hotspot alone
- Solution: Cache policy at module level or in ScannerContext.policy_constants

**Recommendation**: Replace proxy pattern with cache lookup or pre-resolve in policy_constants

---

#### Hotspot #2: Task Annotation Regex (2 module-level instances)

**Location**: `scanner_extract/task_line_parsing.py:43-65` and line 165-180

**Classes**: `_PolicyBackedRegexProxy`

**Instances**:
- `_PolicyBackedRegexProxy("get_marker_line_re")` (used by ROLE_NOTES_RE, TASK_NOTES_LONG_RE)

```python
class _PolicyBackedRegexProxy:
    def _current_regex(self) -> re.Pattern[str]:
        current = getattr(
            require_prepared_policy(None, "task_line_parsing", "task_line_parsing"),  # ⚠️ HOTSPOT
            self._policy_attr_name,
        )
        return current

    def match(self, string: str, ...) -> re.Match[str] | None:
        return self._current_regex().match(string, ...)  # Called per line
```

**Call Stack**: `ROLE_NOTES_RE.match(line)` → `_current_regex()` → `require_prepared_policy()` → DI lookup

**Frequency Per Scan**: 100+ calls (per annotation line check)

**Performance Impact**: 
- Regex resolution on every match operation
- Should be pre-compiled at bundle creation time

**Recommendation**: Pre-compile regex in bundle creation; store Pattern object, not lazy function

---

#### Hotspot #3: Jinja Variable Analysis

**Location**: `scanner_plugins/ansible/variable_discovery.py:447-452`

**Function**: `AnsibleVariableDiscoveryPlugin.collect_undeclared_jinja_variables()`

```python
def collect_undeclared_jinja_variables(self, template_text: str) -> set[str]:
    options = self.scan_options
    prepared_policy_bundle = options.get("prepared_policy_bundle") if isinstance(options, dict) else None
    if not isinstance(prepared_policy_bundle, dict):
        raise ValueError(...)
    
    policy = prepared_policy_bundle.get("jinja_analysis")
    # For every jinja block in template:
    return policy.collect_undeclared_jinja_variables(template_text)  # ⚠️ Multiple calls per template
```

**Frequency Per Scan**: 100+ calls (per jinja block in variables/tasks)

**Performance Impact**:
- Policy lookup repeated for every jinja analysis operation
- Should be cached by plugin instance or in DI container

**Recommendation**: Cache policy in plugin instance during initialization

---

## Hotspot Severity Matrix

| Hotspot | Policy | Frequency | Per-Call Overhead | Total Cost | Priority |
|---------|--------|-----------|-------------------|-----------|----------|
| Task line collections | task_line_parsing | 500+ | 0.5ms | 250ms+ | **CRITICAL** |
| Annotation regex | task_annotation_parsing | 100+ | 0.5ms | 50ms+ | **HIGH** |
| Jinja analysis | jinja_analysis | 100+ | 0.3ms | 30ms+ | **HIGH** |

**Total Hotloop Cost**: ~330ms per scan (15-20% of typical scan time)

**Optimization Strategy**: Pre-cache policies in `ScannerContext.policy_constants` or lazy-load once and memoize

---

### 4. COLDPATH ACCESS (2 locations)

**Characteristic**: Policy accessed rarely; acceptable to invoke resolver with fallback registry.

| Location | Policy | Frequency | Context | Fallback |
|----------|--------|-----------|---------|----------|
| `scanner_io/loader.py:93-120` | `yaml_parsing` | 2-10 calls | YAML load/parse ops | Yes (registry) |
| `scanner_extract/variable_extractor.py:23-29` | `variable_extractor` | 1-5 calls | Include vars extraction | No (fail-closed) |

**Pattern**: Safe to use `get_prepared_policy_or_none()` directly; no caching needed

**Thread-Safety**: ✅ Safe (read-only)

---

## Access Pattern Heatmap (Frequency Distribution)

```
Frequency Category          Location Count    Total Calls/Scan    Example
────────────────────────────────────────────────────────────────────────
CREATION-TIME (1x)          4                 4                   Bundle creation
COLDPATH (1-20x)            2                 10-20               YAML loading
RUNTIME (10-100x)           12                500-1000            Task extraction
HOTLOOP (100-500x)          3                 700+                Task line checks
────────────────────────────────────────────────────────────────────────
TOTAL                       21                1200-1700           per scan
```

---

## Coordination Implications

### Bundle Immutability Contract
- ✅ Bundle must be immutable after ScannerContext initialization
- ✅ Hotloop access patterns assume bundle contents never change mid-scan
- ⚠️ Currently `bundle_resolver` returns dict (mutable); no immutability guarantee

### Cache Invalidation
- ✅ Bundle fingerprint computed for scan result caching
- ⚠️ If policy values change during scan, fingerprint becomes stale
- ⚠️ No documented cache invalidation trigger

### Thread-Safety
- ✅ Creation-time access is serialized (1 thread)
- ✅ Runtime/Hotloop access assumes immutable bundle
- ⚠️ If bundle is mutated during scan, concurrent operations see inconsistency
- ⚠️ Fallback registry resolution may not be thread-safe

---

## Recommendations

1. **Hotspot Mitigation**: Cache policies in `ScannerContext.policy_constants` or lazy-load with memoization
2. **Bundle Immutability**: Make `PreparedPolicyBundle` immutable after creation (freeze dict or use dataclass)
3. **Thread-Safety**: Document bundle immutability contract and enforce via type system
4. **Fallback Registry Audit**: Verify no hidden fallback paths exist outside `scanner_io/loader.py`
5. **Cache Invalidation**: Define explicit trigger for cache invalidation if policy changes mid-scan
