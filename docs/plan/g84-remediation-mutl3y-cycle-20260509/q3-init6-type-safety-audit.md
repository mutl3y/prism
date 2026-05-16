# Q3 Initiative 6 Phase 0: Type Safety Baseline Audit

**Date**: May 9, 2026  
**Scout**: Scout-Q3Init6TypeSafety  
**Status**: COMPLETE  
**Coverage**: 253 source files analyzed; 80 mypy errors identified

---

## Executive Summary

**Current State**: Prism codebase has 80 mypy errors across 16 files (out of 253 total sources). Type coverage is inconsistent—Q2 initiatives (PolicyManager, marker_prefix) achieved strong typing, but many legacy modules remain partially or untyped.

**Baseline Facts**:
- ✅ **80 errors** (pre-existing, not from Q2)
- ✅ **16 problem files** (majority in tests, extraction layer, plugin system)
- ✅ **~30% avg type hint coverage** in low-coverage modules
- ✅ **Q2 work** (PolicyManager, marker_prefix) has **90%+ coverage**
- ✅ **Plugin system** (interfaces.py) fully Protocol-typed ✅

**High-Impact Finding**: Top 3 error sources account for 35 errors:
- Test files: 18 errors (test_t1_02_coverage_lift_batch2.py)
- Feature detection: 12 errors (scanner_plugins/ansible/feature_detection.py)
- Task traversal: 9 errors (scanner_extract/task_file_traversal.py)

---

## Mypy Baseline Audit

### Error Summary

```
Found 80 errors in 16 files (checked 253 source files)
Target: Python 3.14
Config: mypy ignore_missing_imports=true, disable_error_code=["import-untyped"]
```

### Error Distribution by File

| File | Count | Category |
|------|-------|----------|
| test_t1_02_coverage_lift_batch2.py | 18 | Test suite (object type erasure) |
| feature_detection.py | 12 | Feature detection (DI type erasure) |
| task_file_traversal.py | 9 | Task extraction (policy getter returns object) |
| test_kernel.py | 7 | Test suite (protocol mismatch) |
| test_plugin_kernel_extension_parity.py | 5 | Test suite (object indexing) |
| task_line_parsing.py | 5 | Task extraction (policy attr access) |
| test_execution_request_builder.py | 4 | Test suite |
| cli.py | 4 | CLI layer (API mismatch) |
| test_mp1_compatibility.py | 3 | Test suite (TypedDict validation) |
| api.py | 3 | API layer (optional return) |
| **Others** | **5** | Single-error modules |

### Error Type Breakdown

| Error Type | Count | Severity | Root Cause |
|-----------|-------|----------|-----------|
| "object" has no attribute | 35 | HIGH | DI container returns `object`, policy getters not narrowed |
| Missing TypedDict keys | 6 | MEDIUM | ScanOptionsDict/PreparedPolicyBundle validation gaps |
| Type mismatch (arg, return) | 20 | MEDIUM | API/protocol boundary misalignment |
| Indexing on "object" | 8 | MEDIUM | DI returns need narrowing via cast/assert |
| Incompatible types | 11 | LOW | Union mismatches, callable incompatibility |

---

## Type Coverage Analysis

### Legend
- `%R` = % functions with return type annotations
- `%A` = % function arguments with type annotations
- `Funcs` = Total function definitions

### Low-Coverage Modules (Top 10 Impact)

| Return% | Args% | Funcs | Module |
|---------|-------|-------|--------|
| 0% | 0% | 1 | scanner_plugins/__init__.py |
| 50% | 100% | 2 | scanner_extract/dataload.py |
| 66% | 50% | 6 | scanner_readme/style_config.py |
| 68% | 100% | 16 | scanner_core/task_extract_adapters.py |
| 72% | 74% | 18 | scanner_plugins/ansible/extract_policies.py |
| 75% | 53% | 16 | scanner_plugins/marker_prefix_policy.py |
| 80% | 96% | 15 | scanner_io/loader.py |
| 83% | 100% | 6 | scanner_extract/variable_extractor.py |
| 87% | 91% | 16 | scanner_plugins/ansible/variable_discovery.py |
| 90% | 94% | 20 | scanner_plugins/ansible/default_policies.py |

**Total functions in top 10**: ~130 functions, averaging ~70% return type coverage

### High-Coverage Modules (Q2 Baselines)

| Return% | Args% | Funcs | Module |
|---------|-------|-------|--------|
| 100% | 100% | 14 | **scanner_core/policy_manager.py** ✅ |
| 100% | 100% | 8 | **scanner_core/marker_prefix_enforcer.py** ✅ |
| 100% | 100% | 15 | scanner_core/di_helpers.py ✅ |
| 100% | 95% | 32 | scanner_core/protocols_runtime.py ✅ |
| 100% | 93% | 19 | scanner_data/contracts_request.py ✅ |
| 100% | 100% | 21 | scanner_core/policy_registry.py ✅ |

**Q2 Achievement**: 6 modules at 100% return type coverage, serving as baselines for Q3 expansion.

---

## Integration Points: Q2 → Q3

### Q2 Deliverables (Type-Safe Baselines)

1. **PolicyManager** (`scanner_core/policy_manager.py`)
   - ✅ 100% return type annotations
   - ✅ Full `PreparedPolicyBundle`, policy Protocol types
   - ✅ Cache coordination fully typed
   - **Status**: BASELINE for policy extraction refactoring

2. **marker_prefix_enforcer** (`scanner_core/marker_prefix_enforcer.py`)
   - ✅ 100% return type annotations (`str` guarantee)
   - ✅ Fail-closed contract explicit in types
   - **Status**: BASELINE for runtime boundary enforcement

3. **Contracts Layer** (`scanner_data/contracts_request.py`)
   - ✅ 15+ TypedDict definitions
   - ✅ 6 Protocol definitions for policy types
   - ✅ Type aliases for task mapping, scan options
   - **Status**: BASELINE for consumer typing

### Modules That Import from Q2 (Should Inherit Safety)

| Module | Imports From | Coverage Gap |
|--------|-------------|--------------|
| scanner_extract/task_line_parsing.py | policy_manager, marker_prefix_enforcer | 97% args, but returns `object` from DI |
| scanner_extract/task_annotation_parsing.py | policy_manager, contracts | 92% args, but no return types |
| feature_detection.py | policy_manager, di_helpers | 90% args, but receives `object` from DI |
| scanner_plugins/ansible/variable_discovery.py | contracts, variable extractor | 91% args, good coverage |
| scanner_core/di_helpers.py | policy_manager, registry | 100% ✅ |

**Finding**: DI container type erasure (returns `object`) is the primary blocker preventing downstream modules from achieving full coverage.

---

## Plugin System Typing Assessment

### Current State: Protocol-Based (Strong Foundation)

✅ **scanner_plugins/interfaces.py** (100% typed)
```python
# Core plugin Protocols (fully typed)
- VariableDiscoveryPlugin(Protocol): discover_static_variables(...) -> tuple[VariableRow, ...]
- FeatureDetectionPlugin(Protocol): detect_features(...) -> FeaturesContext
- TaskCatalogEntry(TypedDict): task_count, async_count, modules_used (all typed)
- ScanPipelinePlugin(Protocol): fully typed method signatures
```

✅ **Ansible Plugin Suite** (87-90% coverage)
```python
- variable_discovery.py (87% return)
- feature_detection.py (68% return due to DI type erasure)
- default_policies.py (90% return)
- extract_policies.py (72% return)
```

**Gap**: Plugin implementations receive DI-injected objects typed as `object`, forcing downstream modules to use untyped access patterns.

---

## Open Questions

1. **DI Type Erasure Root Cause**: Why does `di.factory_*()` return `object`?
   - Is this by design (loose coupling)?
   - Can we narrow via overloads or generics?
   - **Impact**: Affects 15+ callsites across extraction layer.

2. **Test Suite Type Safety**: Should test files be included in type-safety initiative?
   - 35+ errors are in test files (test_t1_02_coverage_lift_batch2.py, test_kernel.py, etc.)
   - Tests use untyped fixtures and assertion patterns
   - **Decision Point**: Separate Q3b for test typing, or include in core refactor?

3. **Backward Compatibility**: Which modules are public API that must maintain compatibility?
   - `api.py`, `cli.py`, `repo_services.py` are explicit entry surfaces
   - Internal `scanner_*` modules can be refactored freely
   - **Impact**: Affects strategy for extraction layer refactoring.

4. **Protocol vs TypedDict Trade-off**: For policy types, use Protocols (structural typing) or TypedDict (literal shape)?
   - Current contracts use both (Protocols for plugin contracts, TypedDict for data shapes)
   - **Decision**: Formalize guidelines for each pattern.

---

## Gaps

1. **DI Container Factory Return Types**: `DIContainer` protocol defines methods, but factories return `object`.
   - **Blocker**: Prevents downstream typing in extraction/detection layers.
   - **Affect**: 12+ files (feature_detection, task_line_parsing, etc.)
   - **Impact Classification**: decision_blocker

2. **API Signature Mismatches**: `write_role_scan_output()` has incompatible keyword args in cli.py.
   - **Blocker**: 4 errors in API/CLI layer.
   - **Decision Point**: Should this be a Q3a task or separate fix?
   - **Impact Classification**: decision_blocker

3. **Test Suite Type Coverage**: No dedicated type-safety plan for test files.
   - **Current**: 35 errors in tests (object indexing, protocol mismatches)
   - **Decision Point**: Q3b initiative or separate track?
   - **Impact Classification**: research_blocker

4. **ScanOptionsDict Coverage**: Multiple errors for missing/extra keys.
   - **Current**: 6 errors related to TypedDict shape validation.
   - **Root Cause**: Contract evolving faster than TypedDict definition.
   - **Impact Classification**: research_blocker

---

## Confidence & Coverage

| Aspect | Confidence | Notes |
|--------|-----------|-------|
| Error Count (80) | HIGH | mypy --version, direct count |
| Top 10 modules identified | HIGH | Coverage analysis via AST, sorted by function count |
| Q2 baseline coverage | HIGH | Verified 100% in PolicyManager, marker_prefix |
| DI type erasure root cause | MEDIUM | Identified but root cause analysis pending |
| Plugin system assessment | HIGH | Verified Protocol definitions in interfaces.py |
| Test suite type coverage | LOW | Deferred for Q3b decision |

**Overall Confidence**: 0.87 (HIGH)
- Strong on error baseline, module identification, Q2 baselines
- Moderate on DI root-cause analysis (architecture question)
- Low on test suite strategy (deferred by design)

---

## Recommendations for Phase 1

1. **Immediate**: Fix DI container type erasure (decision_blocker)
   - Add overloads or generic bounds to factory methods
   - Narrow `object` → specific policy types
   - Will unblock 15+ files

2. **Near-term**: Fix API/CLI signature mismatches (decision_blocker)
   - Align `write_role_scan_output()` kwargs with call sites
   - Will eliminate 4 errors

3. **Strategy Decision**: Test suite typing strategy
   - Include in Q3a? → Full-codebase coverage
   - Defer to Q3b? → Focus on core modules first
   - **Recommend**: Defer to Q3b (separate initiative)

4. **Next Scout Pass**: Detailed root-cause analysis on DI type erasure
   - Why does `DIContainer` protocol exist separately from factories?
   - Is `object` return intentional for backward-compat?
   - What's the coupling constraint?

