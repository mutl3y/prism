# Final 9-Wave Workoff Addendum

Plan: g84-remediation-mutl3y-cycle-20260509  
Purpose: Minimal execution control sheet for the remaining implementation waves  
Date: 2026-05-10

## Operating Rules

1. Execute waves in order unless an explicit unblock note allows parallelization.
2. Do not mark a wave complete without exit gate evidence.
3. Create one closure artifact per wave in this folder.
4. Update one canonical progress tracker only after gate pass.

Canonical tracker: `q2-initiatives-tracking.yaml`

## Global Validation Gate

Run after each wave:

```bash
cd /raid5/source/test/prism
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src/prism
.venv/bin/python -m black --check src/prism
.venv/bin/python -m mypy src/prism
```

Pass criteria:

1. No new regressions against baseline wave start.
2. No new boundary violations.
3. No unresolved critical errors in wave scope.

## Wave Plan

### Wave 1 of 9: API Collection Compatibility Surface

Objective: Restore collection API compatibility seams expected by tests and external callsites.

Scope:

1. `src/prism/api.py`
2. `src/prism/api_layer/collection.py`

Entry gate: Baseline failures captured in `tests/test_collection_contract.py`.

Exit gate:

1. `tests/test_collection_contract.py` green.
2. `tests/test_api_cli_entrypoints.py` remains green.

Closure artifact: `wave-1-api-compat-closure.md`

### Wave 2 of 9: Task Extract Adapters Contract Restoration

Objective: Restore expected adapter symbols and compatibility wrappers.

Scope: `src/prism/scanner_core/task_extract_adapters.py`

Entry gate: Baseline failures in `tests/test_comment_doc_plugin_resolution.py` and `tests/test_scanner_core_small_surfaces.py`.

Exit gate:

1. `tests/test_comment_doc_plugin_resolution.py` green.
2. `tests/test_scanner_core_small_surfaces.py` green.

Closure artifact: `wave-2-adapters-closure.md`

### Wave 3 of 9: Loader and Dataload Contract Repair

Objective: Reconcile `scanner_io` and `scanner_extract` loader symbol contracts.

Scope:

1. `src/prism/scanner_io/loader.py`
2. `src/prism/scanner_extract/dataload.py`

Entry gate: Baseline failures in `tests/test_dataload.py` and `tests/test_t1_02_coverage_lift_batch3.py`.

Exit gate:

1. `tests/test_dataload.py` green.
2. `tests/test_t1_02_coverage_lift_batch3.py` green.

Closure artifact: `wave-3-loader-dataload-closure.md`

### Wave 4 of 9: MP1 Enforcement Contract Hardening

Objective: Close all MP1 closure-gate failures.

Scope:

1. `src/prism/scanner_core/marker_prefix_enforcer.py`
2. `src/prism/scanner_core/task_extract_adapters.py`
3. `src/prism/scanner_plugins/marker_prefix_policy.py`

Entry gate: Baseline failures in `tests/test_mp1_enforcement.py` and `tests/test_mp1_compatibility.py`.

Exit gate:

1. `tests/test_mp1_enforcement.py` green.
2. `tests/test_mp1_compatibility.py` green.
3. MP1 compliance docs updated if policy behavior changed.

Closure artifact: `wave-4-mp1-closure.md`

### Wave 5 of 9: Plugin-Extract Boundary Enforcement

Objective: Remove or isolate prohibited `scanner_plugins -> scanner_extract` imports.

Scope:

1. `src/prism/scanner_plugins/ansible/extract_adapter.py`
2. `src/prism/scanner_plugins/ansible/extract_utils.py`

Entry gate: Baseline failures in `tests/test_plugin_extract_boundary.py`.

Exit gate:

1. `tests/test_plugin_extract_boundary.py` green.
2. No new circular dependency warnings introduced.

Closure artifact: `wave-5-plugin-boundary-closure.md`

### Wave 6 of 9: Feature Detector Hot Path Marker Prefix Alignment

Objective: Reconcile feature detector hot-path assumptions with canonical marker-prefix flow.

Scope:

1. `src/prism/scanner_core/feature_detector.py`
2. `src/prism/scanner_core/task_extract_adapters.py`

Entry gate: Baseline failure in `tests/test_feature_detector.py`.

Exit gate:

1. `tests/test_feature_detector.py` green.
2. No regressions in task catalog assembly tests.

Closure artifact: `wave-6-feature-hotpath-closure.md`

### Wave 7 of 9: Sequential Scan Isolation and Request Integrity

Objective: Restore per-request isolation semantics in sequential and multi-role scans.

Scope:

1. `src/prism/scanner_core/di.py`
2. `src/prism/scanner_core/scan_request.py`

Entry gate: Baseline failure in `tests/test_real_world_scans.py`.

Exit gate:

1. `tests/test_real_world_scans.py` green.
2. Scan-options mutation and isolation checks green.

Closure artifact: `wave-7-scan-isolation-closure.md`

### Wave 8 of 9: Parity and Error Envelope Contract Reconciliation

Objective: Resolve parity mismatch for scanner context error envelope shape.

Scope:

1. `src/prism/scanner_core/scanner_context.py`
2. Tests asserting parity envelope contract

Entry gate: Baseline parity mismatch in `tests/test_scanner_parity.py`.

Exit gate:

1. `tests/test_scanner_parity.py` green.
2. Contract decision documented if payload shape changed.

Closure artifact: `wave-8-parity-envelope-closure.md`

### Wave 9 of 9: Error Boundary Audit Closure

Objective: Eliminate new raw raises at module boundaries or rebaseline with explicit approval.

Scope:

1. `src/prism/scanner_core/marker_prefix_contract.py`
2. `scripts/audit_error_boundaries.py` outputs

Entry gate: Baseline failure in `tests/test_t3_04_error_boundary_audit.py`.

Exit gate:

1. `tests/test_t3_04_error_boundary_audit.py` green.
2. If baseline update is required, include explicit approval record.

Closure artifact: `wave-9-boundary-audit-closure.md`

## Final Program Closure Gate

Run after Wave 9 only:

```bash
cd /raid5/source/test/prism
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src/prism
.venv/bin/python -m black --check src/prism
.venv/bin/python -m mypy src/prism
```

Final close criteria:

1. MP1 closure-gate tests fully green.
2. Boundary enforcement tests green.
3. Full suite stable.
4. Final closure report generated.

Final closure artifact: `FINAL_9_WAVE_CLOSURE_REPORT.md`
