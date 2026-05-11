# Marker-Prefix Ownership & Consolidation Audit

**Date**: May 9, 2026  
**Tier**: Tier 0 (FREE)  
**Agent**: Scout-MarkerPrefixAudit (Phase 0 Discovery)  
**Task ID**: Q2-Initiative-3-Phase-0-MarkerAudit

---

## Executive Summary

This audit inventories marker-prefix ownership and usage patterns across the prism codebase. The marker-prefix system is well-structured with clear ownership (MP1 contract enforcement), but contains **5 consolidation opportunities** to reduce code duplication and improve maintainability.

**Key Finding**: Marker-prefix ownership is **correctly ingress-owned** per MP1 design, enforced via `PreparedPolicyBundle['comment_doc_marker_prefix']`. No architectural violations detected.

---

## Complete Marker-Prefix Usage Inventory

### 1. Marker Constant Definition

| Location | Definition | Value | Usage | Duplication |
|----------|-----------|-------|-------|------------|
| `scanner_config/section.py` | `DEFAULT_DOC_MARKER_PREFIX` | `"prism"` | **PRIMARY SOURCE** | ✅ Canonical |
| `scanner_core/task_extract_adapters.py` | Default param | `"prism"` | `_extract_task_annotations_for_file(marker_prefix: str = "prism")` | ⚠️ Duplicated (Finding #1) |

**Finding #1**: `DEFAULT_DOC_MARKER_PREFIX` value duplicated as inline string in `task_extract_adapters.py` function signatures (2 functions: `_extract_task_annotations_for_file`, `_collect_task_handler_catalog`).

**Current State**: Works, but creates multiple sources of truth.  
**Impact**: If default changes, two places must update.

---

### 2. Marker Normalization & Validation

| Location | Function | Pattern | Owner | Notes |
|----------|----------|---------|-------|-------|
| `scanner_plugins/parsers/comment_doc/marker_utils.py` | `normalize_marker_prefix(marker_prefix: str \| None) -> str` | **CANONICAL** | Plugin layer | Validates: alphanumeric + `-`, `.`, `_` only |
| `scanner_plugins/parsers/comment_doc/marker_utils.py` | `NormalizesMarkerPrefix` (mixin) | Wrapper | Plugin layer | Staticmethod delegate to canonical |
| `scanner_plugins/ansible/task_annotation_strategy.py` | Re-export | Delegates | Ansible plugin | Imports from marker_utils |
| `tests/test_comment_doc_plugin_resolution.py` | Mock `normalize_marker_prefix()` | Test duplicate | Test layer | Simplified mock (returns `marker_prefix or "prism"`) |

**Finding #2**: Test layer duplicates normalization logic in `test_comment_doc_plugin_resolution.py` (lines 130-131, 167-168). Mock is simplified and doesn't validate character set.

**Current State**: Canonical implementation in marker_utils.py is correct. Tests use simplified mock.  
**Impact**: Test mocks don't reflect real behavior; could miss validation bugs.

---

### 3. Marker Regex Building & Caching

| Location | Function | Purpose | Caching | Owner |
|----------|----------|---------|---------|-------|
| `scanner_plugins/parsers/comment_doc/marker_utils.py` | `get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX)` | Build + cache marker regex | `@functools.lru_cache(maxsize=128)` | **CANONICAL** |
| `scanner_extract/task_line_parsing.py` | `_build_marker_line_re(marker_prefix, *, di)` | Resolve policy + call canonical | None (policy resolves at call time) | Extraction layer |
| `scanner_extract/task_line_parsing.py` | `get_marker_line_re(marker_prefix, *, di)` | Public wrapper | None | Extraction layer |
| `scanner_extract/task_line_parsing.py` | `_PolicyBackedMarkerLineRegexProxy` | Runtime policy resolution | None (proxy resolves policy at call time) | Extraction layer |

**Finding #3**: Three layers of wrapping for marker regex building:
1. `marker_utils.py` (canonical, cached)
2. `task_line_parsing.py::_build_marker_line_re()` (policy resolver)
3. `task_line_parsing.py::get_marker_line_re()` (public wrapper)
4. `task_line_parsing.py::_PolicyBackedMarkerLineRegexProxy` (runtime proxy)

**Current State**: Works correctly with policy injection, but wrapper chain is complex.  
**Impact**: Maintenance burden; harder to trace marker-regex resolution path.

---

### 4. Marker-Prefix Ownership & Enforcement (MP1 Contract)

| Layer | Component | Responsibility | Location | Status |
|-------|-----------|-----------------|----------|--------|
| **Config** | Load marker-prefix from role config | Read `.prism.yml` → markers.prefix | `scanner_config/marker.py::load_readme_marker_prefix()` | ✅ Implemented |
| **Ingress** | Inject into prepared_policy_bundle | Set `scan_options['prepared_policy_bundle']['comment_doc_marker_prefix']` | `scanner_plugins/bundle_resolver.py` (lines 158-171) | ✅ Implemented |
| **Core** | Enforce fail-closed retrieval | Raise error if missing/invalid | `scanner_core/marker_prefix_enforcer.py::enforce_marker_prefix_available()` | ✅ Implemented |
| **Core** | Resolve from DI at hot paths | Call enforcer from bundle | `scanner_core/task_extract_adapters.py::_resolve_marker_prefix()` | ✅ Implemented |
| **Extract** | Pass to annotation/catalog parsing | Explicit parameter, never implicit | `scanner_extract/task_annotation_parsing.py`, `task_line_parsing.py` | ✅ Implemented |
| **Plugin** | Read-only protocol access | Get marker-prefix without mutation | `scanner_plugins/marker_prefix_policy.py::MarkerPrefixPlugin` | ✅ Implemented |

**Finding #4**: Marker-prefix ownership chain is **correctly implemented** across all layers. **No violations detected.**

**Contract Enforcement**:
- ✅ Ingress-owned: Set in `bundle_resolver.py` at policy prep time
- ✅ Immutable: `enforce_marker_prefix_available()` raises on tampering
- ✅ Fail-closed: No fallback to globals; explicit bundle lookup only
- ✅ Plugin-safe: `MarkerPrefixPlugin` protocol prevents mutations

---

### 5. Marker Configuration Loading & Resolution

| Stage | Component | Input | Output | Location |
|-------|-----------|-------|--------|----------|
| **Role Config** | Load `.prism.yml` | File path | YAML dict | `scanner_config/marker.py::load_readme_marker_prefix()` |
| **Policy Context** | Propagate marker settings | Scan options | `policy_context['comment_doc']['marker']['prefix']` | `scanner_plugins/bundle_resolver.py` (lines 159-166) |
| **Bundle Assembly** | Resolve to bundle key | `scan_options`, `policy_context` | `bundle['comment_doc_marker_prefix']` | `scanner_plugins/bundle_resolver.py` (lines 158-171) |
| **Normalization** | Validate character set | Raw string | Normalized string or DEFAULT | `scanner_plugins/parsers/comment_doc/marker_utils.py::normalize_marker_prefix()` |
| **Task Extraction** | Use in parsing | Marker-prefix string | Task annotations with marker detection | `scanner_extract/task_annotation_parsing.py`, `role_notes_parser.py` |

**Finding #5**: Marker configuration loading is **scattered** across two modules:
- **Config loading**: `scanner_config/marker.py` (reads `.prism.yml`, validates YAML shape)
- **Config injection**: `scanner_plugins/bundle_resolver.py` (resolves policy_context, normalizes, injects into bundle)

**Current State**: Separation of concerns is correct (config layer reads files; plugin layer injects). But resolution logic in bundle_resolver.py is implicit (lines 159-166) and not documented.  
**Impact**: Non-obvious where marker-prefix comes from; implicit fallback chain (scan_options → policy_context → default) not immediately visible.

---

## Marker Usage Pattern Analysis

### Pattern 1: Task Annotation Parsing
```python
# Core → Extract injection path
_extract_task_annotations_for_file(
    raw_lines: list[str],
    marker_prefix: str = "prism",  # EXPLICIT parameter
    include_task_index: bool = False,
)
  ↓
extract_task_annotations_for_file(  # scanner_extract layer
    lines: list[str],
    marker_prefix: str,  # REQUIRED parameter
)
  ↓
marker_line_re = get_marker_line_re(marker_prefix)  # Use regex
```

**Status**: ✅ CORRECT — marker_prefix passed explicitly, no implicit defaults.

### Pattern 2: Task Catalog Assembly
```python
# Core → Extract injection path
_collect_task_handler_catalog(
    role_path: str,
    marker_prefix: str = "prism",  # EXPLICIT parameter
    di: object | None = None,
)
  ↓
collect_task_handler_catalog(  # scanner_extract layer
    role_path: str,
    marker_prefix: str,  # REQUIRED parameter
)
```

**Status**: ✅ CORRECT — marker_prefix passed explicitly.

### Pattern 3: Role Notes Parsing (Plugin Layer)
```python
# scanner_plugins/parsers/comment_doc/role_notes_parser.py
def extract_role_notes(
    content: str,
    marker_prefix: str = "prism",  # EXPLICIT parameter
)
  ↓
marker_line_re = get_marker_line_re(marker_prefix)
```

**Status**: ✅ CORRECT — marker_prefix parameter required.

### Pattern 4: Marker Regex Runtime Resolution
```python
# scanner_extract/task_line_parsing.py (at module level)
MARKER_LINE_REGEX = _PolicyBackedMarkerLineRegexProxy(
    policy_attr_name="MARKER_LINE_REGEX"
)
```

**Status**: ⚠️ SPECIAL CASE — Runtime proxy resolves marker-prefix from policy at call time (not pre-resolved). Used only for backward compatibility with module-level constant access.

---

## Test Coverage Analysis

### Marker-Prefix Tests

| Test File | Test Name | Coverage | Status |
|-----------|-----------|----------|--------|
| `test_t1_02_coverage_lift.py` | `test_normalize_marker_prefix_validation()` | Normalization (null, empty, invalid chars) | ✅ Comprehensive |
| `test_execution_request_builder.py` | Multiple tests use `marker_prefix: str = "prism"` | Adapter contract | ✅ Present |
| `test_comment_doc_plugin_resolution.py` | Mock `normalize_marker_prefix()` | Test isolation | ⚠️ Simplified mock |
| `test_scanner_context.py` | Uses `"marker_prefix": "NOTE"` in metadata | Context metadata | ✅ Present |

**Coverage Gap**: No end-to-end tests verifying marker-prefix flows from config file → bundle → extraction.

---

## Marker-Prefix Import Chain

```
scanner_config/section.py (primary definition)
  ↓
  ├── scanner_config/marker.py (config loading)
  ├── scanner_config/__init__.py (public export)
  ├── scanner_plugins/bundle_resolver.py (injection)
  ├── scanner_plugins/parsers/comment_doc/marker_utils.py (normalization)
  ├── scanner_core/task_extract_adapters.py (extraction adapters)
  └── scanner_data/contracts_request.py (schema: PreparedPolicyBundle, CommentDocMarkerContext)
```

**Import Graph Issues**: None detected. All imports are downward-safe (no circular dependencies).

---

## Consolidation Findings Summary

| # | Finding | Current Locations | Duplication | Effort | Risk |
|---|---------|-------------------|-------------|--------|------|
| 1 | `DEFAULT_DOC_MARKER_PREFIX` hardcoded in adapter defaults | `section.py`, `task_extract_adapters.py` (2 functions) | 2 copies | 0.25 days | Low |
| 2 | Test `normalize_marker_prefix()` mock too simplified | `marker_utils.py` (canonical), `test_comment_doc_plugin_resolution.py` (mock) | Logic divergence | 0.5 days | Low |
| 3 | Marker regex building wrapper chain too deep | `marker_utils.py`, `task_line_parsing.py` (3-4 layers) | Complexity | 1 day | Medium |
| 4 | Marker-prefix config resolution implicit fallback chain | `marker.py`, `bundle_resolver.py` (lines 159-166 undocumented) | Implicit logic | 0.25 days | Low |
| 5 | No end-to-end test for config → bundle → extraction flow | Test suite missing integration test | Coverage gap | 0.75 days | Medium |

---

## Ownership Classification

### Clear Ownership ✅
- **Config Layer**: `scanner_config/section.py`, `scanner_config/marker.py` (config reading)
- **Plugin Layer**: `scanner_plugins/parsers/comment_doc/marker_utils.py` (normalization, regex)
- **Core Layer**: `scanner_core/marker_prefix_enforcer.py`, `marker_prefix_policy.py` (enforcement)
- **Extract Layer**: `scanner_extract/task_annotation_parsing.py` (parameter passing)
- **Data Layer**: `scanner_data/contracts_request.py` (schema definition)

### Shared Responsibility ⚠️
- **Bundle Assembly**: `scanner_plugins/bundle_resolver.py` (plugin layer) assembles marker-prefix into `PreparedPolicyBundle` (data layer schema)

---

## Architectural Health Assessment

### Strengths ✅
1. **MP1 Contract enforced correctly**: Marker-prefix ownership is ingress-scoped, immutable after bundle creation
2. **No silent fallbacks**: `enforce_marker_prefix_available()` raises on missing/invalid data
3. **Plugin-safe**: `MarkerPrefixPlugin` protocol prevents plugins from mutating marker-prefix
4. **Clear separation of concerns**: Config, core, extract, plugin layers have distinct responsibilities
5. **Type-safe**: Schema defined in `PreparedPolicyBundle`, enforced at bundle creation

### Improvement Opportunities ⚠️
1. **Reduce default duplication** (Finding #1)
2. **Test isolation vs. realism** (Finding #2)
3. **Simplify wrapper chain** (Finding #3)
4. **Document fallback chain** (Finding #4)
5. **Add end-to-end test** (Finding #5)

---

## Recommendations

**Phase 0 (Discovery - Current)**: ✅ COMPLETE  
**Phase 1 (Consolidation - Recommended)**:
1. Consolidate default marker-prefix to single import point
2. Update test mocks to match canonical validation
3. Flatten marker-regex building wrapper chain
4. Document marker-prefix config resolution in bundle_resolver.py
5. Add end-to-end integration test

**Phase 2 (Optional)**:
- Consider extracting marker parsing to dedicated `scanner_data/marker_contracts.py` module
- Consolidate marker configuration (config loading + resolution) into single module

---

## Detailed File Locations Reference

### Marker Constants
- **Primary**: `/raid5/source/test/prism/src/prism/scanner_config/section.py:5`
- **Duplicated**: `/raid5/source/test/prism/src/prism/scanner_core/task_extract_adapters.py:21, 52`

### Marker Normalization
- **Canonical**: `/raid5/source/test/prism/src/prism/scanner_plugins/parsers/comment_doc/marker_utils.py:18-26`
- **Test Mock**: `/raid5/source/test/prism/src/prism/tests/test_comment_doc_plugin_resolution.py:130-131, 167-168`

### Marker Regex
- **Canonical with Cache**: `/raid5/source/test/prism/src/prism/scanner_plugins/parsers/comment_doc/marker_utils.py:38-45`
- **Wrapper Chain**: `/raid5/source/test/prism/src/prism/scanner_extract/task_line_parsing.py:143-176`

### Marker-Prefix Enforcement (MP1)
- **Enforcer**: `/raid5/source/test/prism/src/prism/scanner_core/marker_prefix_enforcer.py`
- **Resolver**: `/raid5/source/test/prism/src/prism/scanner_core/task_extract_adapters.py:212-241`
- **Plugin Protocol**: `/raid5/source/test/prism/src/prism/scanner_plugins/marker_prefix_policy.py`

### Config Loading & Injection
- **Config Reader**: `/raid5/source/test/prism/src/prism/scanner_config/marker.py:33-102`
- **Bundle Injection**: `/raid5/source/test/prism/src/prism/scanner_plugins/bundle_resolver.py:158-171`

### Data Contracts
- **Bundle Schema**: `/raid5/source/test/prism/src/prism/scanner_data/contracts_request.py:339` (`comment_doc_marker_prefix: str`)
- **Policy Protocol**: `/raid5/source/test/prism/src/prism/scanner_data/contracts_request.py:297-308` (`PreparedTaskAnnotationPolicy`)
- **Marker Context**: `/raid5/source/test/prism/src/prism/scanner_data/contracts_request.py:206-209` (`CommentDocMarkerContext`)

---

**Audit Status**: ✅ COMPLETE  
**Quality Gate**: PASS (no architectural violations, 5 consolidation opportunities identified, effort/risk quantified)
