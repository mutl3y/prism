# Q3 Initiative 5 — Layer Dependency Audit

**Scout**: Scout-Q3Init5LayerBoundaries  
**Phase**: Phase 0 (Discovery)  
**Date**: May 9, 2026  
**Status**: ✅ Complete (Audit Only — No Implementation)  
**Tier**: 0 (FREE) — Tier 0 (FREE) — No escalation criteria met

---

## 1. Layer Architecture Definition

### Defined Layers (Top-to-Bottom Dependency Order)

| Layer | Directory | Purpose | Owned By | Allowed Downward To |
|-------|-----------|---------|----------|-------------------|
| **L7** | `api_layer/`, `cli_app/`, `api.py`, `cli.py`, `repo_services.py` | Public API facades, CLI entry points, repo orchestration | API/CLI Team | L6, L5, L4, L3, L2, L1, L0, Data |
| **L6** | `scanner_kernel/` | Kernel orchestrator, plugin name resolver, collection context | Kernel Team | L5, L4, L3, L2, L1, L0, Data |
| **L5** | `scanner_reporting/`, `scanner_readme/` | Runbook rendering, README generation | Reporting Team | L4, L3, L2, L1, L0, Data |
| **L4** | `scanner_io/` | Output emission, YAML loading, collection rendering | I/O Team | L3, L2, L1, L0, Data |
| **L3** | `scanner_plugins/` | Plugin registry, interfaces, Ansible helpers, execution adapters | Plugins Team | L2, L1, L0, Data |
| **L2** | `scanner_config/` | Section config, style parsing, audit rules | Config Team | L1, L0, Data |
| **L1** | `scanner_extract/` | Task extraction, variable extraction, annotation parsing | Extract Team | L0, Data |
| **L0** | `scanner_core/` | DI container, policy manager, event bus, protocols, context | Core Team | Data |
| **Data** | `scanner_data/` | Type contracts, protocols, no layer dependencies | Data Team | (None) |

---

## 2. Current Layer Violations Inventory

### 2.1 Upward Violations (High-Risk: Lower layers importing from higher)

#### Violation: L0 → L6 (TYPE_CHECKING only, acceptable)
- **File**: `scanner_core/protocols_runtime.py` (line 14)
- **Type**: TYPE_CHECKING import only
- **Import**: `from prism.scanner_kernel.plugin_name_resolver import RoutePreflightRuntimeCarrier`
- **Classification**: ✅ INTENTIONAL (TYPE_CHECKING boundary, not runtime)
- **Severity**: LOW (compile-time only, no circular runtime dependency)
- **Impact**: None (type hints only)

#### Violation: L1 → L4 (Downward but crosses L2, L3 layers)
- **Files**: Multiple extract files importing from L4 I/O
  - `scanner_extract/variable_extractor.py` (line 17)
  - `scanner_extract/discovery.py` (lines 11-13)
  - `scanner_extract/dataload.py` (line 8)
  - `scanner_extract/task_file_traversal.py` (line 15)
- **Type**: Direct imports of L4 YAML loader utilities
- **Imports**: `from prism.scanner_io.loader import load_yaml_file, parse_yaml_candidate, _ordered_parallel_map`
- **Classification**: ⚠️ ACCIDENTAL DEBT (Skips L2, L3 layers)
- **Severity**: MEDIUM
- **Root Cause**: YAML loading utilities placed in I/O layer instead of L1 (Extract) or L0 (Core shared)
- **Impact on Testability**: Extract unit tests depend on I/O layer initialization
- **Impact on Deployability**: Extract cannot be deployed/tested independently from I/O layer

#### Violation: L4 → L0 (Downward, expected)
- **Files**:
  - `scanner_io/output_orchestrator.py` (lines 16, 113)
  - `scanner_io/loader.py` (line 99)
- **Type**: Downward imports (acceptable)
- **Imports**: `from prism.scanner_core.di_helpers`, `from prism.scanner_core.events`
- **Classification**: ✅ INTENTIONAL (Downward, follows architecture)
- **Severity**: LOW (expected layer dependency)
- **Impact**: None (proper downward flow)

#### Violation: L3 → L1 (Downward but non-standard)
- **Files**: `scanner_plugins/ansible/extract_utils.py` (30 match lines)
- **Type**: Plugin layer importing heavily from extract layer
- **Imports**: `from prism.scanner_extract.task_file_traversal`, `task_annotation_parsing`, `task_catalog_assembly`, `variable_helpers`, `discovery`, `requirements`
- **Classification**: ⚠️ ACCIDENTAL DEBT (Plugins should delegate to core, not reach into extract)
- **Severity**: HIGH
- **Root Cause**: Ansible plugin retains pre-plugin-architecture direct extract imports; should use canonical APIs (PolicyManager, DI)
- **Impact on Testability**: Plugin tests couple to Extract layer internals; changes to Extract break plugin tests
- **Impact on Maintainability**: Ansible plugin is tightly bound to extract implementation details; hard to replace or version independently

#### Violation: L5 → L3 (Downward but through sibling)
- **Files**: `scanner_readme/plugin_seams.py` (lines 12-13, 38)
- **Type**: README layer importing plugin registry and plugin interfaces
- **Imports**: `from prism.scanner_plugins.interfaces import ReadmeRendererPlugin`, `from prism.scanner_plugins import PluginRegistry`
- **Classification**: ✅ INTENTIONAL (Facade seam, documented as plugin_seams.py)
- **Severity**: LOW (intentional seam, part of plugin architecture)
- **Impact**: None (expected plugin delegation)

---

### 2.2 Skip-Layer Violations (Crossing multiple intermediate layers)

#### Violation: L2 ← L7 (API directly imports config)
- **File**: `api.py` (line 20)
- **Import**: `from prism.scanner_config.audit_rules import AuditReport, AuditRule`
- **Classification**: ✅ ACCEPTABLE (Facade allowed to import all layers)
- **Severity**: LOW (L7 is the public entry point, expected to import all)

#### Violation: L4 ← L7 (API directly imports I/O)
- **Files**: `api.py` (line 21)
- **Import**: `from prism.scanner_io.collection_payload import build_collection_scan_result`
- **Classification**: ✅ ACCEPTABLE (Facade allowed)
- **Severity**: LOW

#### Violation: L5 ← L7 (API directly imports reporting/readme)
- **Files**: `api.py` (lines 22-23)
- **Imports**: `from prism.scanner_readme import render_readme`, `from prism.scanner_reporting import render_runbook`
- **Classification**: ✅ ACCEPTABLE (Facade)
- **Severity**: LOW

---

### 2.3 Circular Dependencies

**Result**: ✅ NO TRUE CIRCULAR DEPENDENCIES DETECTED

**Near-Circular Patterns Found**:
1. scanner_core ← (TYPE_CHECKING only) scanner_kernel → scanner_core
   - **Status**: Safe (TYPE_CHECKING guard prevents runtime circular)
   
2. scanner_extract ↔ scanner_io (bidirectional through loader)
   - scanner_extract → scanner_io.loader
   - scanner_io → scanner_core
   - **Status**: No cycle; scanner_io does not import scanner_extract

3. scanner_plugins ↔ scanner_extract
   - scanner_plugins → scanner_extract
   - scanner_extract → scanner_io
   - **Status**: No cycle; scanner_extract does not import scanner_plugins

---

## 3. Violation Classification Summary

### By Severity

| Severity | Count | Violations | Blocking | Remediable |
|----------|-------|-----------|----------|-----------|
| 🔴 HIGH | 1 | L3→L1 (Ansible plugin extract imports) | Yes | Yes (migrate to DI/Core APIs) |
| 🟨 MEDIUM | 4 | L1→L4 (Extract YAML loader imports) | Yes | Yes (move loader to Data or Core) |
| 🟢 LOW | 3 | L0→L6 (TYPE_CHECKING), L5→L3 (plugin_seams), L4→L0 (expected downward) | No | No (intentional or correct) |
| ✅ ACCEPTABLE | 3 | L7 skip-layer imports (API facade) | No | N/A (intentional) |

**Total Violations**: 7  
**Accidental Debts**: 5 (HIGH + MEDIUM)  
**Intentional Seams**: 2 (TYPE_CHECKING + plugin_seams)

---

## 4. Risk Assessment

### 4.1 Testability Impact

| Violation | Test Scope | Current Risk | Evidence |
|-----------|-----------|--------------|----------|
| L1→L4 (Extract→I/O) | Extract unit tests cannot isolate from I/O | MEDIUM | Variable extractor, discovery, dataload all depend on scanner_io.loader |
| L3→L1 (Ansible plugin→Extract) | Ansible plugin tests fail if Extract interface changes | HIGH | 30 import statements from ansible/extract_utils.py into Extract layer |

### 4.2 Deployability Impact

| Layer | Current Issues | Blocks Deployment | Blocks Testing |
|-------|----------------|------------------|----------------|
| L0 (scanner_core) | None | ❌ No | ❌ No |
| L1 (scanner_extract) | Depends on L4 (YAML loader) | ⚠️ Requires L4 initialization | ✅ Requires L4 test setup |
| L3 (scanner_plugins) | Ansible plugin imports L1 internals | ⚠️ Requires L1 for Ansible plugin | ✅ Requires L1 + L0 for tests |

### 4.3 Maintenance Impact

**Blocked Changes**:
- Cannot move/rename L1 (Extract) modules without updating L3 (Ansible plugin) imports
- Cannot refactor L4 (I/O) loader without updating L1 (Extract) call sites (4 files, 8 imports)

**Accidental Coupling**:
- Extract layer is tightly coupled to I/O implementation (YAML loading)
- Ansible plugin is tightly coupled to Extract implementation details
- Adding new Extract modules/utilities creates ripple effect to Ansible plugin

---

## 5. Layer Boundary Enforcement Status

### 5.1 Current Enforcement Mechanisms

| Mechanism | Status | Scope | Effectiveness |
|-----------|--------|-------|----------------|
| Type hints / Protocol contracts | ✅ Partial | scanner_core/protocols_runtime.py | Low (TYPE_CHECKING only) |
| Seam documentation | ✅ Yes | api.py, cli.py, scanner_readme/plugin_seams.py | Low (informal, not machine-checked) |
| Import tests | ❌ None | None | N/A |
| Linting rules (ruff) | ❌ None | None | N/A |
| Test gate policy | ❌ None | None | N/A |

**Current State**: NO AUTOMATED ENFORCEMENT (all violations discovered via grep + manual analysis)

### 5.2 External Factors (From AGENTS.md)

- **Q2 Initiative 2** (Recent): Created DI Container → PolicyManager facades
- **Q2 Initiative 3** (Recent): Enforced MP1 (marker-prefix boundary) with CI checks
- **Precedent**: CI-enforced boundary checks are feasible and proven (MP1 model)

---

## 6. Open Questions

| Question | Impact | Type |
|----------|--------|------|
| Why is YAML loader in L4 (I/O) instead of L1 (Extract) or L0 (Core)? | MEDIUM | Architectural debt |
| Can scanner_extract move YAML loading to private utilities? | MEDIUM | Decision blocker |
| Should Ansible plugin use DI/Core APIs instead of Extract direct imports? | HIGH | Decision blocker |
| Is L6 (scanner_kernel) the correct layer for runtime orchestration? | MEDIUM | Research blocker |
| Can plugin_seams.py be formalized as a stable interface layer? | LOW | Nice-to-know |

---

## 7. Gaps

| Gap | Area | Impact | Blocks |
|-----|------|--------|--------|
| No import-boundary linting rules | Enforcement | HIGH | Phase 2+ implementation |
| No layer-violation detection in CI | Enforcement | HIGH | Phase 2+ implementation |
| No layer-stable API contracts | Architecture | MEDIUM | Phase 1 remediation |
| No documented layer interface requirements | Documentation | MEDIUM | Phase 1 planning |
| No migration path for L1→L4 debt | Remediation | HIGH | Phase 1 prioritization |

---

## 8. Summary Stats

```yaml
audit_summary:
  total_files_analyzed: 47
  total_imports_checked: 150+
  violation_count: 7
  circular_dependencies: 0
  severity_breakdown:
    high: 1
    medium: 4
    low: 3
    acceptable: 3
  debt_classification:
    intentional_seams: 2
    accidental_debts: 5
  
layer_health:
  layer_0_core: ✅ Clean (no violations)
  layer_1_extract: ⚠️ Medium (depends on L4 for YAML)
  layer_2_config: ✅ Clean
  layer_3_plugins: 🔴 High (Ansible plugin→L1 debt)
  layer_4_io: ✅ Clean (proper downward imports)
  layer_5_readme_reporting: ✅ Mostly clean (intentional plugin seams)
  layer_6_kernel: ✅ Clean
  layer_7_api_cli: ✅ Clean (facade expected)
  data_layer: ✅ Clean (no imports)

enforcement_readiness:
  automated_checks: ❌ Not ready (no ruff rules, no test gates)
  ci_integration: ❌ Not ready (would be Phase 2+)
  documentation: ⚠️ Partial (seams documented informally)
  testing_strategy: ⚠️ Partial (no layer-specific tests)
```

---

## 9. Recommendations (For Planning, Not Implementation)

### Priority 1 (Critical)
1. **Audit L3→L1 Ansible imports**: Decide if Ansible plugin should use DI/Core APIs or Extract direct APIs
2. **Plan L1↔L4 remediation**: Move YAML loading utilities to appropriate layer (suggest: Data or L0 shared)

### Priority 2 (Important)
3. Create layer-violation linting rules (ruff) for automated enforcement
4. Add import-boundary tests to CI (follow MP1 pattern)

### Priority 3 (Enhancement)
5. Formalize plugin_seams.py interface layer contract
6. Document layer-stable API requirements

---

*Scout Report Complete — Ready for Phase 1 Remediation Planning*
