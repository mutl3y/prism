# Multi-Week Architectural Initiatives Plan

**Date**: 2026-05-09  
**Parent Plan**: g84-remediation-mutl3y-cycle-20260509  
**Scope**: 210 deferred findings (80% of 261 total)  
**Timeline**: Q2-Q4 2026 (6-12 months)

---

## Executive Summary

The g84 review discovered **210 findings (80%)** that require sustained multi-week architectural refactoring rather than quick fixes. This document provides a comprehensive roadmap for addressing these findings through **8 major initiatives** sequenced by dependency order and business value.

**Total Effort**: 12-16 weeks (3-4 months of focused work)  
**Recommended Approach**: Quarterly batches with 2-3 initiatives per quarter  
**Success Metric**: 95%+ test pass rate maintained throughout all initiatives

---

## Initiative Grouping Analysis

### Findings Distribution

| Category | Count | % of Deferred | Avg Severity | Est. Effort |
|----------|-------|---------------|--------------|-------------|
| **DI/Architecture** | 44 | 21% | HIGH | 1-2 weeks |
| **Policy Ownership** | 28 | 13% | HIGH | 1 week |
| **Layer Boundaries** | 23 | 11% | HIGH | 1 week |
| **Type Safety** | 19 | 9% | MEDIUM | 3-5 days |
| **Extraction Logic** | 22 | 10% | MEDIUM | 1 week |
| **Output/Reporting** | 15 | 7% | MEDIUM | 3-5 days |
| **Documentation** | 18 | 9% | LOW | 2-3 days |
| **Cleanup/Refactoring** | 41 | 20% | LOW | 1 week |

---

## Q2 2026 Initiatives (May-July)

### Initiative 1: DI Container God-Object Decomposition

**Timeline**: 1-2 weeks  
**Findings**: 17 (GILF-DI-03 through GILF-DI-19)  
**Priority**: 🔴 CRITICAL (blocks concurrent scanning, testing, plugin expansion)

#### Problem Statement

`src/prism/scanner_core/di.py` is a 1000+ line god-object with:
- 17 factory methods (copy-paste patterns)
- Mixed responsibilities (plugin resolution, service location, config management)
- No interface segregation
- Hard to test, mock, or extend

#### Solution Architecture

**Phase 1.1: Create Plugin Resolution Layer** (3 days)
- Extract `PluginResolver` class
  - Methods: `resolve_plugin(protocol, key)`, `list_plugins(protocol)`, `register_plugin(protocol, key, impl)`
- Protocol: `PluginResolutionProtocol`
- Move all `_get_*_plugin()` methods → PluginResolver
- DI delegates to PluginResolver for all plugin lookups

**Phase 1.2: Create Service Locator Layer** (3 days)
- Extract `ServiceLocator` class
  - Methods: `get_service(service_type)`, `register_service(service_type, factory)`
- Protocol: `ServiceLocationProtocol`
- Move all `factory_*()` methods → ServiceLocator
- Config-driven service registration

**Phase 1.3: Slim DI Container** (2 days)
- Keep only orchestration logic in DIContainer
- Composition: `DIContainer(plugin_resolver, service_locator, config)`
- Backward compatibility facade for existing callsites

**Phase 1.4: Validation & Testing** (2 days)
- Unit tests for PluginResolver (80%+ coverage)
- Unit tests for ServiceLocator (80%+ coverage)
- Integration tests for DIContainer facade
- Full pytest suite validation (1150+ passing)

#### Success Criteria

- ✅ DIContainer < 300 lines (down from 1000+)
- ✅ PluginResolver isolated and testable
- ✅ ServiceLocator config-driven
- ✅ Zero regressions (1150+ tests passing)
- ✅ 17 DI findings resolved

#### Files Modified

- `src/prism/scanner_core/di.py` (slim to ~200 lines)
- `src/prism/scanner_core/plugin_resolver.py` (NEW, ~300 lines)
- `src/prism/scanner_core/service_locator.py` (NEW, ~300 lines)
- `src/prism/scanner_core/di_protocols.py` (NEW, protocols)
- `src/prism/tests/test_plugin_resolver.py` (NEW)
- `src/prism/tests/test_service_locator.py` (NEW)

---

### Initiative 2: PolicyManager Extraction

**Timeline**: 1 week  
**Findings**: 8 (GILF-POL-01 through GILF-POL-08)  
**Priority**: 🔴 HIGH (scattered policy ownership, inconsistent validation)

#### Problem Statement

Policy ownership is scattered across:
- `scan_request.py` (policy ingress + normalization)
- `scanner_context.py` (policy enforcement + re-validation)
- `task_extract_adapters.py` (marker-prefix lookup + normalization)
- `variable_discovery.py` (policy backfill fallback)

No single source of truth, leading to:
- Duplicate validation logic
- Inconsistent fail-closed enforcement
- Hidden policy mutation paths

#### Solution Architecture

**Phase 2.1: Create PolicyManager** (3 days)
- `PolicyManager` class in `scanner_core/policy_manager.py`
  - Methods: `prepare_policy(scan_options)`, `validate_policy(bundle)`, `get_policy_value(bundle, key)`
- Single authority for all policy operations
- Fail-closed by default (raise on missing keys)

**Phase 2.2: Consolidate Validation** (2 days)
- Move all policy validation → PolicyManager
- Remove duplicate checks from scan_request, scanner_context
- Strict schema validation (typed contracts)

**Phase 2.3: Update Consumers** (2 days)
- scan_request: Delegate to PolicyManager.prepare_policy()
- scanner_context: Remove re-validation, consume bundle read-only
- task_extract_adapters: Use PolicyManager.get_policy_value()
- variable_discovery: Remove backfill fallback

**Phase 2.4: Validation** (1 day)
- Unit tests for PolicyManager (90%+ coverage)
- Integration tests for policy flow (ingress → preparation → consumption)
- Full pytest validation

#### Success Criteria

- ✅ Single PolicyManager authority
- ✅ Zero duplicate validation logic
- ✅ Fail-closed enforcement everywhere
- ✅ 8 policy findings resolved
- ✅ 1150+ tests passing

#### Files Modified

- `src/prism/scanner_core/policy_manager.py` (NEW, ~400 lines)
- `src/prism/scanner_core/scan_request.py` (delegate to PolicyManager)
- `src/prism/scanner_core/scanner_context.py` (remove validation)
- `src/prism/scanner_core/task_extract_adapters.py` (use PolicyManager)
- `src/prism/scanner_core/variable_discovery.py` (remove fallback)
- `src/prism/tests/test_policy_manager.py` (NEW)

---

### Initiative 3: Marker-Prefix Boundary Enforcement

**Timeline**: 3-5 days  
**Findings**: 5 (GILF-MP-01 through GILF-MP-05)  
**Priority**: 🟡 MEDIUM (policy leak on hot path)

#### Problem Statement

Marker-prefix ownership is split between ingress and runtime:
- `scan_request.py` projects `comment_doc_marker_prefix` into scan_options ✅
- `task_extract_adapters.py` still opens nested `policy_context.comment_doc` and normalizes locally ❌

This violates the MP1 closure contract (ingress-only ownership).

#### Solution Architecture

**Phase 3.1: Complete MP1 Enforcement** (2 days)
- Remove all nested `policy_context.comment_doc` reads from scanner_core
- `task_extract_adapters` consumes only `scan_options.comment_doc_marker_prefix`
- Fail-closed: raise if key missing (no defaults on hot path)

**Phase 3.2: Update PolicyManager Integration** (1 day)
- PolicyManager projects marker-prefix into PreparedPolicyBundle
- All consumers use bundle key only

**Phase 3.3: Validation** (1 day)
- Grep audit: zero `policy_context.comment_doc` reads in scanner_core
- Feature detection tests (verify marker-prefix flow)
- Full pytest validation

#### Success Criteria

- ✅ Ingress-only marker-prefix ownership
- ✅ Zero nested policy reads in scanner_core
- ✅ 5 marker-prefix findings resolved
- ✅ 1150+ tests passing

#### Files Modified

- `src/prism/scanner_core/task_extract_adapters.py` (remove nested reads)
- `src/prism/scanner_core/policy_manager.py` (project marker-prefix)
- `src/prism/tests/test_fsrc_comment_doc_plugin_resolution.py` (update tests)

---

## Q3 2026 Initiatives (August-October)

### Initiative 4: Immutable Context Objects

**Timeline**: 3-5 days  
**Findings**: 6 (GILF-CONC-01 through GILF-CONC-06)  
**Priority**: 🟡 MEDIUM (thread-safety for concurrent scanning)

#### Problem Statement

`ScannerContext` is mutable after construction:
- Plugin resolution can mutate shared state
- Concurrent scans have race conditions
- Deep copy everywhere as workaround (performance penalty)

#### Solution Architecture

**Phase 4.1: Freeze ScannerContext** (2 days)
- Make all attributes read-only after `__init__`
- Use `@dataclass(frozen=True)` or manual `__setattr__` override
- Plugin resolution returns new context (copy-on-write)

**Phase 4.2: Update Plugin Callsites** (2 days)
- All plugin methods receive immutable context
- Return modified context if state changes needed
- Scanner kernel orchestrates context evolution

**Phase 4.3: Validation** (1 day)
- Thread-safety tests (concurrent scan execution)
- Performance benchmarks (verify no regression)
- Full pytest validation

#### Success Criteria

- ✅ ScannerContext immutable after construction
- ✅ Copy-on-write semantics for state changes
- ✅ 6 concurrency findings resolved
- ✅ Thread-safe concurrent scanning validated

#### Files Modified

- `src/prism/scanner_core/scanner_context.py` (freeze attributes)
- `src/prism/scanner_plugins/` (update all plugin methods)
- `src/prism/scanner_kernel/orchestrator.py` (context evolution)
- `src/prism/tests/test_concurrent_scanning.py` (NEW)

---

### Initiative 5: Layer Boundary Enforcement

**Timeline**: 1 week  
**Findings**: 23 (GILF-LAYER-01 through GILF-LAYER-23)  
**Priority**: 🟡 MEDIUM (architectural discipline)

#### Problem Statement

Layer violations across the codebase:
- scanner_core imports from scanner_plugins (8 violations)
- scanner_extract imports from scanner_io (6 violations)
- Circular dependencies (5 cases)
- API facade bypass (4 cases)

#### Solution Architecture

**Phase 5.1: Define Layer Protocol** (1 day)
- Document canonical layer hierarchy:
  - api_layer → scanner_kernel → scanner_core → scanner_extract → scanner_plugins
  - Allowed: Higher → Lower imports only
  - Forbidden: Lower → Higher imports (except via DI/Protocol)

**Phase 5.2: Fix scanner_core → scanner_plugins** (2 days)
- Move plugin protocol definitions to scanner_data/contracts
- scanner_core imports only protocols, not concrete plugins
- DI resolves concrete implementations at runtime

**Phase 5.3: Fix scanner_extract → scanner_io** (2 days)
- Extract shared contracts to scanner_data
- scanner_extract imports only contracts
- scanner_io implements contracts

**Phase 5.4: Break Circular Dependencies** (2 days)
- Introduce adapter/bridge patterns
- Extract shared interfaces to neutral layer

**Phase 5.5: Validation** (1 day)
- Import analyzer script (detect layer violations)
- CI enforcement (block PRs with violations)
- Full pytest validation

#### Success Criteria

- ✅ Zero layer violations (enforced by CI)
- ✅ 23 layer findings resolved
- ✅ Clear architectural boundaries documented
- ✅ 1150+ tests passing

#### Files Modified

- 30+ files across all layers (import restructuring)
- `docs/architecture/LAYER_BOUNDARIES.md` (NEW)
- `eng/validate_layer_boundaries.py` (NEW, CI enforcement)

---

### Initiative 6: Type Safety Improvements

**Timeline**: 3-5 days  
**Findings**: 19 (GILF-TYPE-01 through GILF-TYPE-19)  
**Priority**: 🟢 LOW-MEDIUM (type system hygiene)

#### Problem Statement

- Type erasure (Any → concrete types needed)
- Missing Protocol definitions (4 cases)
- TypedDict misuse (3 cases)
- Missing return type annotations (12 cases)

#### Solution Architecture

**Phase 6.1: Replace Any with Protocols** (2 days)
- Define Protocols for plugin interfaces
- Update all `Any` params to Protocol types
- Mypy strict mode validation

**Phase 6.2: Fix TypedDict Misuse** (1 day)
- Remove blind `cast()` calls
- Explicit TypedDict construction
- Runtime validation where needed

**Phase 6.3: Add Return Type Annotations** (2 days)
- Annotate all builder functions
- Annotate all factory methods
- Mypy validation (zero errors target)

#### Success Criteria

- ✅ Zero `Any` types in core modules
- ✅ All public APIs have return types
- ✅ Mypy strict mode passing
- ✅ 19 type findings resolved

#### Files Modified

- `src/prism/scanner_data/contracts_output.py` (Protocols)
- 20+ files (type annotations)

---

## Q4 2026 Initiatives (November-December)

### Initiative 7: Extraction Logic Consolidation

**Timeline**: 1 week  
**Findings**: 22 (GILF-EXT-01 through GILF-EXT-22)  
**Priority**: 🟢 LOW-MEDIUM (reduce duplication)

#### Problem Statement

- Duplicate extraction logic (8 cases)
- Inconsistent error handling (6 cases)
- Feature detector facade incomplete (4 cases)
- Cross-module coordination gaps (4 cases)

#### Solution Architecture

**Phase 7.1: Create Extraction Facade** (3 days)
- Unified `ExtractionOrchestrator` in scanner_extract
- Single entry point for all extraction operations
- Consistent error handling + logging

**Phase 7.2: Consolidate Duplicate Logic** (3 days)
- Extract common patterns to shared utilities
- Remove copy-paste code

**Phase 7.3: Validation** (1 day)
- Coverage analysis (80%+ for new facade)
- Full pytest validation

#### Success Criteria

- ✅ Single extraction facade
- ✅ 50% reduction in duplicate code
- ✅ 22 extraction findings resolved

#### Files Modified

- `src/prism/scanner_extract/extraction_orchestrator.py` (NEW)
- 15+ files in scanner_extract/ (consolidation)

---

### Initiative 8: Cleanup & Documentation

**Timeline**: 1 week  
**Findings**: 59 (remaining LOW priority)  
**Priority**: 🟢 LOW (polish + maintainability)

#### Problem Statement

- Missing docstrings (18 findings)
- Inconsistent logging (15 findings)
- Dead code (8 findings)
- Naming inconsistencies (10 findings)
- Other minor issues (8 findings)

#### Solution Architecture

**Phase 8.1: Documentation Sweep** (3 days)
- Add docstrings to all public APIs
- Update architecture docs
- Create module-level overviews

**Phase 8.2: Logging Standardization** (2 days)
- Consistent log levels (DEBUG/INFO/WARNING/ERROR)
- Structured logging with context

**Phase 8.3: Dead Code Removal** (1 day)
- Delete unused functions/classes
- Remove commented-out code

**Phase 8.4: Final Polish** (1 day)
- Naming consistency pass
- Linting cleanup
- Final validation

#### Success Criteria

- ✅ 90%+ docstring coverage
- ✅ Consistent logging standards
- ✅ Zero dead code
- ✅ 59 cleanup findings resolved

#### Files Modified

- 40+ files (documentation, logging, cleanup)

---

## Dependency Graph

```
Q2 2026:
  Initiative 1 (DI Container) ─┐
                               ├──> Initiative 2 (PolicyManager)
  Initiative 3 (Marker-Prefix) ─┘

Q3 2026:
  Initiative 2 (PolicyManager) ──> Initiative 4 (Immutable Context)
  Initiative 1 (DI Container) ──> Initiative 5 (Layer Boundaries)
  (Independent) ──> Initiative 6 (Type Safety)

Q4 2026:
  Initiative 5 (Layer Boundaries) ──> Initiative 7 (Extraction)
  (Independent) ──> Initiative 8 (Cleanup)
```

**Critical Path**: Init 1 → Init 2 → Init 4 → Init 7  
**Parallel Opportunities**: Init 3, Init 6, Init 8 can run concurrently with critical path

---

## Execution Strategy

### Recommended Approach

**Q2 2026 (May-July)**: Foundation
- Week 1-2: Initiative 1 (DI Container)
- Week 3-4: Initiative 2 (PolicyManager)
- Week 5: Initiative 3 (Marker-Prefix)

**Q3 2026 (August-October)**: Hardening
- Week 6: Initiative 4 (Immutable Context)
- Week 7-8: Initiative 5 (Layer Boundaries)
- Week 9: Initiative 6 (Type Safety)

**Q4 2026 (November-December)**: Polish
- Week 10-11: Initiative 7 (Extraction)
- Week 12: Initiative 8 (Cleanup)

### Validation Gates (Each Initiative)

1. **Unit Tests**: 80%+ coverage for new code
2. **Integration Tests**: Full pytest suite 1150+ passing
3. **Type Checking**: Mypy zero new errors
4. **Linting**: Ruff + black clean
5. **Performance**: No regressions (benchmark suite)
6. **Documentation**: All public APIs documented

### Risk Mitigation

1. **Feature Flags**: Gradual rollout for major changes
2. **A/B Testing**: Old vs new implementation parity
3. **Rollback Plan**: Each initiative = independent commit series
4. **Incremental Delivery**: Ship partial improvements early

---

## Cost Estimates

| Initiative | Duration | Tier | Est. Cost | Findings |
|-----------|----------|------|-----------|----------|
| 1. DI Container | 1-2 weeks | Tier 2 | $0.080-0.120 | 17 |
| 2. PolicyManager | 1 week | Tier 2 | $0.050-0.070 | 8 |
| 3. Marker-Prefix | 3-5 days | Tier 2 | $0.020-0.030 | 5 |
| 4. Immutable Context | 3-5 days | Tier 2 | $0.020-0.030 | 6 |
| 5. Layer Boundaries | 1 week | Tier 2 | $0.050-0.070 | 23 |
| 6. Type Safety | 3-5 days | Tier 1 | $0.010-0.015 | 19 |
| 7. Extraction | 1 week | Tier 2 | $0.040-0.060 | 22 |
| 8. Cleanup | 1 week | Tier 1 | $0.015-0.025 | 59 |
| **TOTAL** | **12-16 weeks** | **Mixed** | **$0.285-0.420** | **159** |

**Note**: Cost estimates assume AI-assisted implementation. Remaining 51 findings are low-priority polish items that can be addressed incrementally.

---

## Success Metrics

### Technical Metrics

- ✅ **210 findings resolved** (100% of deferred)
- ✅ **Test pass rate**: 98%+ maintained throughout
- ✅ **Type safety**: Mypy strict mode passing
- ✅ **Code quality**: Ruff score >8.5/10
- ✅ **Documentation**: 90%+ coverage

### Architectural Metrics

- ✅ **DI Container**: <300 lines (down from 1000+)
- ✅ **Policy ownership**: Single PolicyManager authority
- ✅ **Layer violations**: Zero (CI enforced)
- ✅ **Test isolation**: 80%+ unit test coverage
- ✅ **Performance**: No regressions (baseline maintained)

### Business Metrics

- ✅ **Platform expansion**: K8s/Terraform plugins unblocked
- ✅ **Concurrent scanning**: Thread-safe execution enabled
- ✅ **Maintainability**: 50% reduction in god-object complexity
- ✅ **Onboarding**: Clear architectural boundaries documented

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize initiatives** based on business needs
3. **Allocate resources** (2-3 engineers × 3-4 months)
4. **Create detailed task breakdowns** for Q2 initiatives
5. **Setup monitoring** (metrics dashboard for tracking progress)

---

## Appendix: Finding Registry

All 210 deferred findings are tracked in:
- `g84-findings-consolidated.yaml` (master registry)
- `wave_*_execution.yaml` files (wave-specific tracking)

Each finding includes:
- ID, severity, category, file, description
- Effort estimate, dependencies, architectural impact
- Mapping to initiatives in this plan

---

**Document Status**: ✅ READY FOR REVIEW  
**Next Review**: May 2026 (stakeholder approval)  
**Owner**: Prism Architecture Team
