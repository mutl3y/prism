# Marker-Prefix Ownership Audit (Q2 Initiative 3)

**Scout**: MarkerPrefixAudit  
**Date**: May 9, 2026  
**Scope**: Complete marker-prefix resolution and ownership analysis  
**Status**: ✅ COMPLETE  

---

## Executive Summary

Marker-prefix ownership is **clean and well-isolated**. Single point of entry (ingress), single point of write (bundle_resolver), standardized resolution throughout. No ownership violations detected.

**Key Finding**: `comment_doc_marker_prefix` follows a strict read-only pattern after `bundle_resolver.ensure_prepared_policy_bundle()` completes. All downstream consumers call `_resolve_marker_prefix(di)` to retrieve it.

---

## 1. Origins: Where Is `comment_doc_marker_prefix` Set?

### 1.1 Ingress Entry Point (API/CLI)

**File**: `src/prism/scanner_core/scan_request.py` (line ~95)

```python
def build_run_scan_options_canonical(
    *,
    role_path: str,
    # ... other params ...
) -> ScanOptionsDict:
    """Build canonical scan options from ingress parameters."""
```

- API/CLI callers pass `comment_doc_marker_prefix` into `scan_options` dict
- Type: `str | None`
- Default handled by fallback chain (see §1.3)

### 1.2 Single Write Point: Bundle Resolver

**File**: `src/prism/scanner_plugins/bundle_resolver.py` (lines 142-157)

```python
def ensure_prepared_policy_bundle(
    *,
    scan_options: dict[str, Any],
    di: object | None,
) -> PreparedPolicyBundle:
    # ... setup ...
    
    if bundle.get("comment_doc_marker_prefix") is None:
        raw_prefix = scan_options.get("comment_doc_marker_prefix")
        if not isinstance(raw_prefix, str):
            # Fallback: check policy_context.comment_doc.marker.prefix
            policy_context = scan_options.get("policy_context")
            if isinstance(policy_context, dict):
                cd = policy_context.get("comment_doc")
                if isinstance(cd, dict):
                    mk = cd.get("marker")
                    if isinstance(mk, dict):
                        p = mk.get("prefix")
                        if isinstance(p, str):
                            raw_prefix = p
        if isinstance(raw_prefix, str):
            bundle["comment_doc_marker_prefix"] = normalize_marker_prefix(raw_prefix)
        else:
            bundle["comment_doc_marker_prefix"] = DEFAULT_DOC_MARKER_PREFIX
```

**Ownership Assigned**: `prepared_policy_bundle["comment_doc_marker_prefix"]`  
**Post-Write Access Pattern**: READ-ONLY

### 1.3 Fallback Chain

| Priority | Source | File | Fallback Path |
|----------|--------|------|---|
| 1 | Ingress arg | `scan_options["comment_doc_marker_prefix"]` | Direct string |
| 2 | Policy context | `scan_options["policy_context"]["comment_doc"]["marker"]["prefix"]` | Nested dict lookup |
| 3 | Default | `scanner_config.section.DEFAULT_DOC_MARKER_PREFIX` | Hardcoded "prism" |

### 1.4 Default Constant

**File**: `src/prism/scanner_config/section.py` (line 5)

```python
DEFAULT_DOC_MARKER_PREFIX = "prism"
```

**Exported From**:
- `prism.scanner_config` (public API)
- `prism.scanner_config.marker` (private usage)
- `prism.scanner_plugins.parsers.comment_doc.marker_utils` (normalization)

---

## 2. Resolution Chain: How Does It Flow Through Codebase?

### 2.1 Retrieval Pattern: `_resolve_marker_prefix(di)`

**File**: `src/prism/scanner_core/task_extract_adapters.py` (lines 211-226)

```python
def _resolve_marker_prefix(di: object | None) -> str:
    """Resolve marker_prefix from prepared_policy_bundle in DI context."""
    scan_options = scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        raise ValueError(
            "prepared_policy_bundle must be available in scan_options to resolve marker prefix"
        )
    bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(bundle, dict):
        raise ValueError(
            "prepared_policy_bundle must be available in scan_options to resolve marker prefix"
        )
    bundle_prefix = bundle.get("comment_doc_marker_prefix")
    if not isinstance(bundle_prefix, str):
        raise ValueError(
            "prepared_policy_bundle must provide comment_doc_marker_prefix to resolve marker prefix"
        )
    return bundle_prefix
```

**Fail-Closed**: Raises `ValueError` if bundle unavailable or prefix missing  
**No Fallback**: No silent DEFAULT_DOC_MARKER_PREFIX fallback after bundle stage

### 2.2 Public Adapter Functions

**File**: `src/prism/scanner_core/task_extract_adapters.py` (lines 231-253)

```python
def extract_task_annotations_for_file(
    raw_lines: list[str],
    *,
    include_task_index: bool = False,
    di: object | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    return _extract_task_annotations_for_file(
        raw_lines,
        marker_prefix=_resolve_marker_prefix(di),  # <-- DI-resolved
        include_task_index=include_task_index,
        di=di,
    )

def collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    return _collect_task_handler_catalog(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=_resolve_marker_prefix(di),  # <-- DI-resolved
        di=di,
    )
```

**Pattern**: All public scanner_core functions that need marker_prefix call `_resolve_marker_prefix(di)` internally

### 2.3 Plugin Access Path: Feature Detection

**File**: `src/prism/scanner_plugins/ansible/feature_detection.py` (lines 42-52)

```python
def _resolve_marker_prefix(options: dict[str, object]) -> str:
    """Resolve marker_prefix from prepared_policy_bundle in options."""
    bundle = options.get("prepared_policy_bundle")
    if not isinstance(bundle, dict):
        raise ValueError(
            "prepared_policy_bundle must be available in extract options"
        )
    prefix = bundle.get("comment_doc_marker_prefix")
    if prefix is None or not isinstance(prefix, str):
        raise ValueError(
            "prepared_policy_bundle.comment_doc_marker_prefix must be set "
            "(policy bundle may be incomplete or corrupted)"
        )
    return prefix
```

**Usage in Feature Detector** (line 129):

```python
marker_prefix = self._resolve_marker_prefix(options)
```

### 2.4 Plugin Access Path: Task Annotation Parsing

**File**: `src/prism/scanner_plugins/parsers/comment_doc/annotation_parsing.py` (lines 74-80)

```python
def parse_comment_doc_annotations(
    raw_lines: list[str],
    *,
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
    # ... other params ...
) -> list[TaskAnnotation]:
    """Parse comment-doc annotations from raw lines."""
    marker_line_re = get_marker_line_re(marker_prefix)
    # ... parsing logic ...
```

**Entry**: Caller (task_extract_adapters) passes marker_prefix explicitly  
**Default**: Used only for direct plugin calls (not hot path)

---

## 3. Current Ownership: Who Owns Marker-Prefix?

### 3.1 Ownership Matrix

| Domain | Owner | Responsibility | Read-Only? |
|--------|-------|---|---|
| **Config/Default** | `scanner_config.section` | Define DEFAULT_DOC_MARKER_PREFIX constant | ✅ Yes |
| **Ingress Validation** | `scan_request` | Accept from API/CLI callers | ✅ Yes (pass-through) |
| **Bundle Assembly** | `bundle_resolver.ensure_prepared_policy_bundle()` | Write to bundle, normalize, fallback | ✅ WRITE POINT |
| **Runtime Resolution** | `task_extract_adapters._resolve_marker_prefix(di)` | Retrieve from bundle, fail-closed | ✅ Yes |
| **Plugin Access** | `scanner_plugins.{ansible,parsers,*}` | Call task_extract_adapters or feature_detector | ✅ Yes |
| **README Rendering** | `scanner_readme` | **DOES NOT ACCESS** marker-prefix (see §4) | N/A |

### 3.2 Ownership Principle

**Single Write, Distributed Read**:
- `bundle_resolver.ensure_prepared_policy_bundle()` is **the only place** marker-prefix enters the bundle
- After that, all consumers call standardized resolution functions
- No module modifies the bundle value after creation

---

## 4. Boundary Violations: Any Downstream Modifications?

### 4.1 Scanner-Readme Isolation ✅

**File**: `src/prism/scanner_readme/render.py` (lines 24-50)

- ✅ Does **NOT** access `scan_options` or `prepared_policy_bundle`
- ✅ Does **NOT** modify marker-prefix
- ✅ Uses separate `legacy_merge_marker_prefixes()` method from renderer plugin
- ✅ This is for **README merge markers**, not comment_doc_marker_prefix

**Evidence**: No imports from `scanner_plugins.bundle_resolver` or `task_extract_adapters`

### 4.2 Plugin Layer Isolation ✅

- ✅ Plugins call standardized `_resolve_marker_prefix()` functions
- ✅ No direct bundle writes observed
- ✅ All uses are read-only parameter passing

### 4.3 Extract Layer Isolation ✅

**File**: `src/prism/scanner_extract/task_line_parsing.py` (lines 133-155)

```python
def _normalize_marker_prefix(marker_prefix: str | None, di: object | None = None) -> str:
    """Normalize marker_prefix through policy plugin."""
    return MarkerPrefixNormalizerMixin().normalize_marker_prefix(marker_prefix)
```

- ✅ Normalization is policy-injected (via plugin), not stored
- ✅ No writes to bundle

### 4.4 Conclusion: No Violations

**Status**: ✅ CLEAN  

All boundary checks pass. No unauthorized modifications detected.

---

## 5. Plugin Access: How Do Plugins Get Marker-Prefix?

### 5.1 Access Patterns

#### Pattern A: DI-Based (Scanner-Core Hot Path)

```python
# task_extract_adapters.py (public API)
def extract_task_annotations_for_file(..., di=None):
    return _extract_task_annotations_for_file(
        ...,
        marker_prefix=_resolve_marker_prefix(di),  # <-- resolve from DI
        ...
    )
```

**When to use**: Called from scanner_core's public entry points

#### Pattern B: Options-Based (Ansible Feature Detector)

```python
# ansible/feature_detection.py
marker_prefix = self._resolve_marker_prefix(options)
```

**When to use**: Inside plugin implementation with direct access to prepared_policy_bundle

#### Pattern C: Direct Parameter (Plugin Functions)

```python
# annotation_parsing.py
def parse_comment_doc_annotations(
    raw_lines: list[str],
    *,
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,  # explicit param
):
```

**When to use**: Low-level parsing functions called with explicit marker_prefix

### 5.2 Consistency Matrix

| Plugin | Access Method | File | Pattern |
|--------|---|---|---|
| Task Annotation | `_resolve_marker_prefix(di)` | scanner_core/task_extract_adapters.py | A |
| Feature Detection | `self._resolve_marker_prefix(options)` | scanner_plugins/ansible/feature_detection.py | B |
| Role Notes Parser | Explicit param | scanner_plugins/parsers/comment_doc/role_notes_parser.py | C |
| Comment-Doc Annotation | Explicit param | scanner_plugins/parsers/comment_doc/annotation_parsing.py | C |

**Conclusion**: All patterns retrieve from same source (prepared_policy_bundle). Consistency high.

---

## 6. Cache/Override: Any Caching or Override Patterns?

### 6.1 Caching Detected

**File**: `src/prism/scanner_plugins/parsers/comment_doc/marker_utils.py` (line 15)

```python
_MARKER_LINE_RE_CACHE_SIZE = 128
```

**Function**: `get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX)`

- ✅ Caches **compiled regex patterns**, not the prefix itself
- ✅ Each unique marker_prefix gets its own regex cache entry
- ✅ **Not a boundary violation** — cache key is the prefix value, not a store override

### 6.2 Override Patterns Analyzed

#### No Direct Overrides ✓

No pattern found where marker_prefix is overridden after bundle_resolver stage.

#### Policy-Injected Normalization (Not an Override)

```python
# marker_utils.py
def normalize_marker_prefix(marker_prefix: str | None) -> str:
    """Normalize marker_prefix through configurable policy."""
    if not isinstance(marker_prefix, str):
        return DEFAULT_DOC_MARKER_PREFIX
    prefix = marker_prefix.strip()
    if not prefix or " " in prefix:  # Reject empty or spaces
        return DEFAULT_DOC_MARKER_PREFIX
    return prefix.lower()
```

- Normalization is **deterministic** (not a configurable override)
- Applied **once** during bundle assembly
- Result is **stored immutably** in bundle

### 6.3 Conclusion: Cache/Override Analysis

| Pattern | Type | Status | Impact |
|---------|------|--------|--------|
| Regex compilation cache | Performance cache | ✅ Safe | No state mutation |
| Marker-prefix overrides | Direct write | ✅ None found | Clean ownership |
| Policy-injected normalization | Deterministic | ✅ Correct | Applied once, stored |

---

## 7. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ INGRESS LAYER (API/CLI)                                             │
│                                                                     │
│  scan_request.build_run_scan_options_canonical()                  │
│    ↓                                                                │
│  scan_options["comment_doc_marker_prefix"] ← Caller passes        │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ BUNDLE ASSEMBLY (scanner_plugins/bundle_resolver.py)              │
│                                                                     │
│  ensure_prepared_policy_bundle():                                 │
│    raw_prefix = scan_options.get("comment_doc_marker_prefix")    │
│    [fallback to policy_context.comment_doc.marker.prefix]        │
│    [fallback to DEFAULT_DOC_MARKER_PREFIX]                       │
│    normalized = normalize_marker_prefix(raw_prefix)              │
│    bundle["comment_doc_marker_prefix"] = normalized  ← WRITE     │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ↓ [READ-ONLY BOUNDARY]
┌─────────────────────────────────────────────────────────────────────┐
│ RUNTIME RESOLUTION                                                  │
│                                                                     │
│  scanner_core/task_extract_adapters._resolve_marker_prefix(di):  │
│    bundle = scan_options.get("prepared_policy_bundle")           │
│    prefix = bundle.get("comment_doc_marker_prefix")  ← READ      │
│    return prefix (fail-closed if missing)                        │
└────────────────────┬──────────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         ↓           ↓           ↓
    Task Ann.    Feature Det.   Extract
    (Core)       (Plugin)       (Layer)
    
    All call:
    _resolve_marker_prefix(di)
    
    Or directly accept as param from above
```

---

## 8. Validation Checklist

- [x] Single write point identified: `bundle_resolver.ensure_prepared_policy_bundle()` (line 155-157)
- [x] All consumers use standardized resolution: `_resolve_marker_prefix(di)` or explicit param
- [x] No unauthorized writes to bundle detected
- [x] No modifications after bundle assembly
- [x] Scanner-readme isolation verified (does not access marker-prefix)
- [x] Normalization applied once, result immutable
- [x] Fallback chain documented (ingress → policy_context → default)
- [x] Plugin access patterns consistent
- [x] Regex caching analyzed (safe, no state mutation)
- [x] Fail-closed on missing bundle or prefix

---

## 9. Summary Table

| Aspect | Status | Finding |
|--------|--------|---------|
| **Origins** | ✅ Clean | Single ingress, standardized fallback chain |
| **Write Points** | ✅ Single | `bundle_resolver.ensure_prepared_policy_bundle()` only |
| **Ownership** | ✅ Clear | `prepared_policy_bundle["comment_doc_marker_prefix"]` |
| **Resolution** | ✅ Standardized | `_resolve_marker_prefix(di)` + explicit params |
| **Plugin Access** | ✅ Consistent | All use standardized functions |
| **Boundary Violations** | ✅ None | All modules respect read-only after bundle |
| **Cache/Override** | ✅ Safe | Regex cache only, no prefix overrides |
| **Scanner-Readme Isolation** | ✅ Clean | Does not access marker-prefix at all |

---

## 10. Recommendation: MP1 Canonical Contract

Based on this audit, marker-prefix ownership is ready for MP1 formalization (see artifact 3: `marker-prefix-flow-specification.yaml`).

**No immediate action required** — current implementation is clean and follows best practices.

**Future-proofing**: Consider adding integration test to verify bundle_resolver is the only write point to `comment_doc_marker_prefix`.
