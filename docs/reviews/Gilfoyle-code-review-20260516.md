# Gilfoyle Code Review: Prism Scanner Codebase

**Date:** 2026-05-16
**Scope:** `/raid5/source/test/prism/src/prism`
**Reviewer:** Gilfoyle (Code Review Mode)

---

## Architecture Overview

The codebase follows a layered architecture with these main packages:

| Layer | Package | Responsibility |
|-------|---------|---------------|
| **API** | `api.py`, `cli.py`, `cli_app/` | Public entrypoints |
| **Core** | `scanner_core/` | DI, execution context, feature detection, variable discovery |
| **Kernel** | `scanner_kernel/` | Plugin routing, scan-phase orchestration |
| **Extract** | `scanner_extract/` | Task parsing, annotation extraction, file traversal |
| **Plugins** | `scanner_plugins/` | Platform-specific implementations (Ansible, K8s, Terraform stubs) |
| **Data** | `scanner_data/` | TypedDict contracts, builders |
| **IO** | `scanner_io/` | Output emission, loading |
| **Reporting** | `scanner_reporting/`, `scanner_readme/` | Runbook/CSV rendering |

## What's Actually Good

1. **TypedDict contracts are centralized** in `scanner_data/contracts_request.py` and `scanner_data/contracts_output.py`. Single source of truth for data shapes prevents drift.
2. **DI container uses deferred imports** in factory methods to break circular dependencies. `TYPE_CHECKING` guard imports are properly separated.
3. **Error taxonomy** in `errors.py` is structured with codes, categories, layers, and recoverability. `PrismRuntimeError` dataclass is a solid error contract.
4. **Plugin registry** uses a dataclass-based state container (`_PluginRegistryState`) with frozen slots.
5. **Event bus** in `events.py` correctly catches and logs listener exceptions so telemetry never breaks production semantics.

## Findings

### FIND-01: Empty Subclass Facades in `api.py`

```python
class DIContainer(_BaseDIContainer):
    """Package-owned run-scan DI seam for public facade overrides."""

class FeatureDetector(_BaseFeatureDetector):
    """Package-owned feature-detector seam for public facade overrides."""

class ScannerContext(_BaseScannerContext):
    """Package-owned scanner-context seam for public facade overrides."""
```

Three empty subclasses with zero overrides. Pure indirection that makes stack traces harder to read and import graphs harder to follow. The `_resolve_run_scan_runtime_classes()` function returns these as a tuple for runtime class resolution that could have been direct imports.

**Severity:** MEDIUM — No runtime harm, but adds cognitive overhead and maintenance burden.

---

### FIND-02: Policy-Backed Proxy Pattern on Hot Paths (`scanner_extract/task_line_parsing.py`)

`_PolicyBackedCollectionProxy` and `_PolicyBackedRegexProxy` dynamically resolve policy attributes at every single access:

```python
def _current_value(self) -> object:
    return getattr(
        require_prepared_policy(None, "task_line_parsing", "task_line_parsing"),
        self._policy_attr_name,
    )
```

Every `__iter__`, `__contains__`, `__len__`, `__repr__` call goes through a DI container lookup. `_PolicyBackedRegexProxy` re-resolves the regex pattern from DI on every `match()`, `search()`, and `fullmatch()` call. This is a **runtime resolution hot path** that will cause measurable performance degradation.

**Severity:** HIGH — Runtime overhead on every task-line parse operation.

---

### FIND-03: Hand-Rolled Deep Clone (`scanner_core/di.py`)

```python
def _clone_container_structure(value: object) -> object:
    if isinstance(value, dict):
        return {key: _clone_container_structure(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_container_structure(item) for item in value]
    # ... handles 5 container types
    return value
```

Reimplements `copy.deepcopy()` without handling custom objects, circular references, or other edge cases the standard library handles. If performance is the concern, use a more efficient serialization library.

**Severity:** MEDIUM — Functional for current use cases but fragile and redundant.

---

### FIND-04: Repeated `require_prepared_policy` Call Sites

The `require_prepared_policy` function is called from every function in task_line_parsing.py, task_annotation_parsing.py, task_file_traversal.py, and `yaml_parsing.py`. Each call site passes the same pattern with redundant arguments. The `_task_line_policy_attr` helper extracted in g14 is a band-aid — the real fix is to resolve the policy once and pass it through.

**Severity:** MEDIUM — Code duplication and repeated DI lookups.

---

### FIND-05: `CacheKeyProtocol` Convention Mismatch (`scanner_data/contracts_request.py`)

`CacheKeyProtocol` establishes a `__cache_key__` dunder method that Python's standard library doesn't support. You can't use it with `dict` or `frozenset` without wrapping every object. This abstraction sounds elegant in design documents but becomes a maintenance burden in practice.

**Severity:** LOW — Design concern, not a runtime issue.

---

### FIND-06: Hardcoded `IGNORED_IDENTIFIERS` (`scanner_plugins/ansible/variable_discovery.py`)

A 60+ entry hardcoded frozenset of Ansible-specific identifiers with no categorization, no comments explaining why each entry is ignored, and no mechanism for extension. Should be data-driven (config file or database) to support multi-platform expansion.

**Severity:** MEDIUM — Blocks clean multi-platform extension.

---

### FIND-07: Redundant Locking in Event Bus (`scanner_core/events.py`)

Uses both `ContextVar` for context isolation and `threading.Lock` for thread safety. `ContextVar` already provides per-context isolation. The lock is unnecessary if listeners are registered at startup and never modified. If they CAN be modified at runtime, a lock won't solve the underlying design problem.

**Severity:** LOW — Minor overhead, but indicates unclear concurrency model.

---

### FIND-08: Overly Permissive Type Alias (repo_services.py)

```python
RepoScanPayload = RunScanOutputPayload | dict[str, Any] | str
```

Admits a properly typed TypedDict, an untyped dict, or a string. The `str` case is particularly concerning — when does a scan payload become a string? The type system should prevent this ambiguity, not encode it.

**Severity:** MEDIUM — Type safety gap that could mask runtime errors.

---

### FIND-09: Inconsistent Naming Conventions (cli.py)

```python
_EXIT_CODE_GENERIC_ERROR = 2
_EXIT_CODE_NOT_FOUND = 3
EXIT_CODE_AUDIT_VIOLATIONS = 8  # Missing leading underscore
```

Some exit code constants have the `_` prefix, some don't. Nobody's enforcing naming conventions with a linter rule.

**Severity:** LOW — Cosmetic, but indicates missing lint configuration.

---

### FIND-10: Runtime Protocol Validation (`scanner_kernel/orchestrator.py`)

`_validate_process_scan_pipeline_plugin_signature()` validates plugin method signatures at runtime. The whole point of Protocols is that mypy verifies them at compile time. Runtime validation means static type checking isn't catching errors — either mypy config is too permissive or Protocol definitions are too loose.

**Severity:** MEDIUM — Indicates static analysis gaps.

---

### FIND-11: Test Coverage Gaps

Missing dedicated tests for:
- task_line_parsing.py proxy behavior under concurrent access
- scanner_context.py error boundary behavior with malformed inputs
- execution_request_builder.py platform key resolution edge cases
- output_orchestrator.py with malformed payloads

The `error-boundary-audit-baseline.json` baseline file is brittle and hard to maintain.

**Severity:** MEDIUM — Gaps in test coverage for critical paths.

---

## Summary

This codebase is the product of a very thorough, multi-wave refactoring effort. The architecture is sound in principle — plugin-based, DI-driven, contract-first. But the implementation has accumulated technical debt:

1. **Runtime overhead** from policy-backed proxy patterns on hot paths
2. **Unnecessary indirection** through empty subclass facades and runtime class resolution
3. **Hand-rolled utilities** where standard library functions would suffice
4. **Type system weaknesses** with union types that admit untyped data
5. **Inconsistent conventions** in naming and structure

The codebase is like a house renovated by 15 different contractors — each did good work in isolation, but the overall result has redundant walls, triple-layered drywall, and light switches that control nothing.
