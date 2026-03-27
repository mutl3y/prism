---
layout: default
title: Modernization Plan
---

Phased plan for reducing maintenance risk in Prism without destabilizing scanner behavior.

## Progress Update (2026-03-26)

Completed modernization slices (Phase 1 in progress):

- extracted shared repo helper and service flows from CLI into `repo_services`
- aligned API and CLI on shared preflight, style-guide, and sparse-checkout orchestration
- moved non-lightweight checkout orchestration into shared service paths
- moved lightweight style-readme orchestration into shared service paths
- unified metadata normalization for style path and `scanner_report_relpath`
- fixed Windows-separator relpath normalization and added regression coverage
- expanded focused regressions for dry-run and non-dry-run JSON normalization plus API parity

### Current Validation

- latest full-suite validation: `671 passed`
- focused regression coverage now includes scanner-report relpath normalization and JSON normalization parity paths

### Next Slice

- begin Phase 2 scanner orchestration decomposition with a narrow first lane: extract scan-request normalization into a dedicated module while preserving current public behavior and focused regression gates

## Progress Note (2026-03-26, Phase 2 kickoff slice)

Completed a narrow, mergeable scan-request normalization extraction slice:

- extracted shared repo scan result normalization helper into `repo_services` as `_normalize_repo_scan_result_payload`
- preserved API compatibility wrapper behavior by routing `_normalize_repo_style_guide_path` through the shared helper
- preserved CLI behavior and output shape by routing `_normalize_repo_json_payload` through the shared helper
- added focused unit tests for dict and JSON-string payload normalization plus malformed/non-object pass-through cases

Validation for this slice:

- focused: repo-services + repo CLI/API normalization tests
- full suite: executed after focused validation

## Progress Note (2026-03-26, Phase 2 scan-request normalization slice)

Completed a narrow scan-orchestration extraction focused on request option shaping:

- extracted scan-request option-map shaping and detailed-catalog normalization into `src/prism/scanner_submodules/scan_request.py`
- preserved scanner public interfaces and internal seam names by keeping `scanner.py` wrappers (`_build_run_scan_options`, `_resolve_detailed_catalog_flag`) and routing them to the new module
- added focused seam tests in `src/prism/tests/test_scan_request.py` covering helper behavior and wrapper parity

Validation for this slice:

- focused: `pytest -q src/prism/tests/test_scan_request.py src/prism/tests/test_scan.py -k "build_run_scan_options or resolve_detailed_catalog_flag"`
- full suite: `PYTHONPATH=src .venv/bin/python -m pytest -q` (680 passed)

## Progress Note (2026-03-26, Phase 2 scan-context/payload shaping slice)

Completed a narrow scan-orchestration extraction focused on context and payload shaping:

- extracted scan context/payload shaping helpers into `src/prism/scanner_submodules/scan_context.py`
- preserved scanner compatibility seams by keeping wrapper signatures in `src/prism/scanner.py` and delegating to the new submodule
- added focused parity tests in `src/prism/tests/test_scan_context.py` for extracted helper output shape and wrapper delegation behavior

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_context.py src/prism/tests/test_scan_request.py -k "scan_context or run_scan_payload or scan_output_payload or finalize_scan_context or build_run_scan_options or resolve_detailed_catalog_flag"` (11 passed)
- full suite: task `tests: full` (686 passed)

## Progress Note (2026-03-26, Phase 2 scan-metrics/uncertainty shaping slice)

Completed a narrow scan-orchestration extraction focused on metrics and uncertainty shaping:

- extracted scanner metrics/uncertainty helpers into `src/prism/scanner_submodules/scan_metrics.py`
- preserved scanner compatibility seams by keeping wrapper signatures in `src/prism/scanner.py` and delegating to the new submodule
- added focused parity tests in `src/prism/tests/test_scan_metrics.py` for helper output shaping and wrapper delegation behavior

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_metrics.py src/prism/tests/test_scan.py -k "scan_metrics or extract_scanner_counters or build_referenced_variable_uncertainty_reason"`
- full suite: task `tests: full` (690 passed)

## Progress Note (2026-03-26, Phase 2 scan output sidecar orchestration slice)

Completed a narrow scan-orchestration extraction focused on sidecar output emission:

- extracted scanner report/runbook sidecar orchestration and path shaping into `src/prism/scanner_submodules/scan_output_emission.py`
- preserved scanner compatibility seams by keeping wrapper signatures in `src/prism/scanner.py` and delegating to the new submodule
- added focused parity tests in `src/prism/tests/test_scan_output_emission.py` for path shaping, sidecar payload handling, file writes, and wrapper delegation behavior

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_output_emission.py src/prism/tests/test_render_readme.py -k "scan_output_emission or write_concise_scanner_report_if_enabled or write_optional_runbook_outputs or run_scan_writes_runbook_output_file or run_scan_writes_runbook_csv_output_file or scanner_report"` (11 passed)
- full suite: task `tests: full` (697 passed)

### Anti-Stall Checkpoint (2026-03-26 role/collection slice)

- completed slices count (Phase 2): 5
- next 2 queued slices:
  - extract role/collection discovery and path handling into a dedicated submodule with parity tests
  - extract primary output rendering/write orchestration into a dedicated submodule with parity tests
- current full-suite status: green (`697 passed`)

## Progress Note (2026-03-26, Phase 2 role/collection discovery and path-handling slice)

Completed a narrow scan-orchestration extraction focused on role/collection discovery and path handling:

- extracted role identity resolution and role metadata/requirements/variable path-discovery helpers into `src/prism/scanner_submodules/scan_discovery.py`
- preserved scanner compatibility seams by keeping wrapper signatures in `src/prism/scanner.py` and delegating to the new submodule
- added focused parity tests in `src/prism/tests/test_scan_discovery.py` covering extracted helper behavior and wrapper delegation stability

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_discovery.py src/prism/tests/test_scan.py -k "scan_discovery or load_meta or load_requirements or load_variables or resolve_scan_identity"`
- full suite: task `tests: full`

### Anti-Stall Checkpoint

- completed slices count (Phase 2): 6
- remaining queued slice(s):
  - extract primary output rendering/write orchestration into a dedicated submodule with parity tests
- current full-suite status: green (validated after this slice)

## Progress Note (2026-03-26, Phase 2 primary output rendering/write orchestration slice)

Completed a narrow scan-orchestration extraction focused on primary output rendering/write:

- extracted primary output rendering/write orchestration helpers into `src/prism/scanner_submodules/scan_output_primary.py`
- preserved scanner compatibility seams by keeping wrapper signatures in `src/prism/scanner.py` and delegating to the new submodule
- added focused parity tests in `src/prism/tests/test_scan_output_primary.py` for extracted helper behavior and scanner wrapper delegation stability

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_output_primary.py src/prism/tests/test_scan_output_emission.py -k "scan_output_primary or render_and_write_scan_output or render_primary_scan_output or scan_output_emission"` (12 passed)
- full suite: `PYTHONPATH=src .venv/bin/python -m pytest -q` (709 passed)

### Anti-Stall Checkpoint (2026-03-26)

- completed slices count (Phase 2): 7
- remaining queued slice(s):
  - none (Phase 2 queue complete)
- next queued focus:
  - begin typed internal scan-output payload models for `run_scan` seams
  - evaluate extraction of residual scan-output emission coordinator (`_emit_scan_outputs`) into a thin orchestration helper
- current full-suite status: green (`709 passed`)

## Progress Note (2026-03-26, Phase 3 typed run_scan output seam slice)

Completed a narrow typed-model seam at run-scan output payload boundaries:

- introduced `RunScanOutputPayload` TypedDict in `src/prism/scanner_submodules/scan_context.py` to stabilize the internal payload contract used between `run_scan` orchestration, sidecar emission, and primary output rendering
- preserved scanner behavior and public interfaces by keeping wrapper seams intact in `src/prism/scanner.py` and applying type annotations only (no output-shape changes)
- updated `src/prism/scanner_submodules/scan_output_primary.py` to consume the typed payload at the seam without changing render/write behavior
- added focused contract tests in `src/prism/tests/test_scan_context.py` to verify TypedDict annotation parity for payload builders

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_context.py src/prism/tests/test_scan_output_primary.py -k "scan_output_payload or render_primary_scan_output or build_scan_output_payload or prepare_run_scan_payload"` (`7 passed, 5 deselected`)
- full suite: `.venv/bin/python -m pytest -q` (`710 passed`)

### Anti-Stall Checkpoint Refresh (2026-03-26)

- completed slices count (post-Phase 2): 8
- queue status: active, no blockers
- next 2 queued slices:
  - typed seam for scan-output sidecar coordinator inputs (`_emit_scan_outputs` argument object) while preserving wrapper signatures
  - typed seam for scanner report sidecar payload (`write_concise_scanner_report_if_enabled` contract) with parity tests
- current full-suite status: green (`710 passed`)

## Progress Note (2026-03-26, Phase 3 _emit_scan_outputs argument bundle slice)

Completed a narrow typed-bundle seam at the `_emit_scan_outputs` boundary:

- introduced `EmitScanOutputsArgs` TypedDict in `src/prism/scanner_submodules/scan_context.py` bundling all 15 `_emit_scan_outputs` call parameters into one typed object, eliminating positional-argument drift risk at the call site
- added `build_emit_scan_outputs_args` factory in `scan_context.py` that accepts a `RunScanOutputPayload` directly and flattens it together with the output-routing params into the bundle
- added `_build_emit_scan_outputs_args` wrapper in `scanner.py` delegating to the helper, consistent with existing wrapper conventions
- updated `_emit_scan_outputs` signature from 15 positional kwargs to `(args: EmitScanOutputsArgs)` and rewired all internal field accesses
- updated the single call site in `run_scan` to build the bundle via `_build_emit_scan_outputs_args` and pass it as one argument
- preserved all wrapper seams and public behavior; external interfaces unchanged

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_context.py -k "emit_scan_outputs or build_emit_scan_outputs"` (`3 passed, 7 deselected`)
- full suite: `.venv/bin/python -m pytest -q` (`713 passed`)

### Anti-Stall Checkpoint (2026-03-26, slice 9)

- completed slices count (Phase 3): 9
- queue status: active, no blockers
- next 2 queued slices:
  - typed seam for scanner report sidecar payload (`_write_concise_scanner_report_if_enabled` argument bundle) with parity tests
  - typed seam for runbook sidecar outputs (`_write_optional_runbook_outputs` argument bundle) with parity tests
- current full-suite status: green (`713 passed`)

## Progress Note (2026-03-26, Phase 3 ScanReportSidecarArgs typed seam slice)

Completed a narrow typed-bundle seam at the `_write_concise_scanner_report_if_enabled` boundary:

- introduced `ScanReportSidecarArgs` TypedDict in `src/prism/scanner_submodules/scan_context.py` bundling all 11 `_write_concise_scanner_report_if_enabled` call parameters (excluding the injected `build_scanner_report_markdown` callable), eliminating argument-drift risk between `_emit_scan_outputs` and the sidecar emission helper
- added `build_scan_report_sidecar_args` factory in `scan_context.py` that accepts a `RunScanOutputPayload` directly plus routing params, flattening them into the typed bundle
- added `_build_scan_report_sidecar_args` wrapper in `scanner.py` delegating to the helper, consistent with existing wrapper conventions
- updated `_emit_scan_outputs` to build the sidecar args via `_build_scan_report_sidecar_args` and unpack with `**` when calling `_write_concise_scanner_report_if_enabled`, shrinking the call site from 11 scattered kwargs to one structured bundle
- preserved all wrapper seams and public behavior; external interfaces unchanged

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_context.py src/prism/tests/test_scan_output_emission.py -k "scan_report_sidecar or build_scan_report_sidecar or emit_scan_outputs or write_concise_scanner_report"` (`9 passed, 11 deselected`)
- full suite: task `tests: full` (`716 passed`)

### Anti-Stall Checkpoint (2026-03-26, slice 10)

- completed slices count (Phase 3): 10
- queue status: active, no blockers
- next 2 queued slices:
  - typed seam for runbook sidecar outputs (`_write_optional_runbook_outputs` argument bundle `RunbookSidecarArgs`) with parity tests
  - typed seam / thin coordinator extraction for `_emit_scan_outputs` itself (move from scanner.py into scan_output_emission or a new scan_emit module) with parity tests
- current full-suite status: green (`716 passed`)

## Progress Note (2026-03-26, Phase 3 RunbookSidecarArgs typed seam slice)

Completed a narrow typed-bundle seam at the `_write_optional_runbook_outputs` boundary:

- introduced `RunbookSidecarArgs` TypedDict in `src/prism/scanner_submodules/scan_context.py` for runbook sidecar routing fields
- added `build_runbook_sidecar_args` factory in `scan_context.py` that flattens runbook path options and payload metadata into one typed bundle
- preserved scanner compatibility seams by keeping `_build_runbook_sidecar_args` in `src/prism/scanner.py` and delegating to the new helper
- ensured the runbook sidecar call path remains stable through the extracted `scan_output_emission` coordinator
- added parity coverage in `src/prism/tests/test_scan_context.py` for TypedDict contract, helper output shape, and wrapper delegation behavior

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_context.py -k "runbook_sidecar_args or build_runbook_sidecar_args"` (`4 passed, 14 deselected`)
- full suite: task `tests: full` (`724 passed`)

### Anti-Stall Queue Refresh (2026-03-26, slice 11)

- completed slices count (Phase 3): 11
- queue status: active, no blockers
- next queued slices:
  - mypy incremental gate expansion for extracted seam modules and `src/prism/repo_services.py`
  - typed tightening follow-up in extracted seam modules to keep mypy gate green without broad scanner typing churn
- current full-suite status: green (`724 passed`)

## Progress Note (2026-03-26, Phase 3 mypy incremental gate expansion slice)

Completed the incremental static-type gate expansion for extracted seam modules:

- extended `testenv:typecheck` in `tox.ini` to include extracted seam modules and `src/prism/repo_services.py`
- repaired and normalized `.pre-commit-config.yaml` hook structure for `mypy-seams` so it executes consistently
- aligned pre-commit scope with tox scope for the same extracted modules
- added `--disable-error-code=import-untyped` to this scoped gate to avoid broad external-stub churn while preserving seam-level type validation
- fixed `emit_scan_outputs` return normalization in `src/prism/scanner_submodules/scan_output_emission.py` by decoding bytes results to UTF-8 string at the seam boundary

Validation for this slice:

- focused: `.venv/bin/python -m mypy --ignore-missing-imports --disable-error-code=import-untyped --follow-imports=silent src/prism/scanner_submodules/scan_context.py src/prism/scanner_submodules/scan_request.py src/prism/scanner_submodules/scan_output_emission.py src/prism/scanner_submodules/scan_output_primary.py src/prism/scanner_submodules/scan_metrics.py src/prism/scanner_submodules/scan_discovery.py src/prism/repo_services.py` (`Success: no issues found in 7 source files`)
- focused: `.venv/bin/pre-commit run mypy-seams --all-files` (`Passed`)
- full suite: task `tests: full` (`724 passed`)

### Anti-Stall Queue Refresh (2026-03-26, slice 12)

- completed slices count (Phase 3): 12
- queue status: active, no blockers
- next queued slices:
  - tighten mypy typing for scanner-report counters seam (`scanner_report.py`) to prepare broader module inclusion
  - expand incremental type gate only after scanner-report typing errors are resolved
- current full-suite status: green (`724 passed`)

## Progress Note (2026-03-26, Phase 3 scanner-report counters seam + gate expansion slice)

Completed the next feasible Phase 3 typing slice focused on scanner report counter aggregation seams:

- tightened scanner counter typing in `src/prism/scanner_submodules/scanner_report.py` with explicit `ScannerCounters` TypedDict contract and typed row/counter aggregation inputs
- preserved scanner behavior/public interfaces by keeping the same counter keys and markdown rendering flow; only internal typing and narrow casts were added
- aligned adjacent seam wrapper typing in `src/prism/scanner_submodules/scan_metrics.py` to return the same typed counter contract
- added focused regression in `src/prism/tests/test_scan_metrics.py` to assert provenance-category mapping shape and unresolved-noise aggregation parity
- expanded incremental type gate scope to include `src/prism/scanner_submodules/scanner_report.py` in both `tox.ini` and `.pre-commit-config.yaml` after seam stability was verified

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_metrics.py src/prism/tests/test_scan.py -k "extract_scanner_counters or scanner_report_markdown"` (`11 passed, 148 deselected`)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 8 source files`)
- full suite: task `tests: full` (`725 passed`)

### Anti-Stall Queue Refresh (2026-03-26, slice 13)

- completed slices count (Phase 3): 13
- queue status: active, no blockers
- next queued slices:
  - evaluate the next adjacent typed seam in scanner-report rendering inputs (typed metadata/readme-section contract) without widening behavior scope
  - consider incremental type-gate expansion to one additional stable module only after focused seam typing lands cleanly
- current full-suite status: green (`725 passed`)

## Progress Note (2026-03-26, Phase 3 scanner-report rendering-input contract slice)

Completed the next queued Phase 3 typed seam focused on scanner-report rendering inputs:

- tightened scanner-report rendering input contracts in `src/prism/scanner_submodules/scanner_report.py` with explicit `ScannerReportMetadata` and `ReadmeSectionRenderInput` TypedDicts
- added a narrow `ReadmeSectionBodyRenderer` callable alias and `build_readme_section_render_input` helper to stabilize metadata/readme-section payload shaping before section rendering
- preserved scanner behavior and public interfaces by keeping markdown composition flow and output content unchanged; this slice is typing-only at the seam
- added focused parity tests in `src/prism/tests/test_scan_metrics.py` to assert TypedDict annotation shape and readme-section input builder payload parity

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_metrics.py src/prism/tests/test_scan.py -k "scanner_report_markdown or extract_scanner_counters or scanner_report_typed_render_input_contract or build_readme_section_render_input"` (`13 passed, 148 deselected`)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 8 source files`)
- full suite: `.venv/bin/python -m pytest -q` (`727 passed`)

### Anti-Stall Queue Refresh (2026-03-26, slice 14)

- completed slices count (Phase 3): 14
- queue status: active, no blockers
- next queued slices:
  - consider incremental type-gate expansion to one additional stable module only after focused seam typing lands cleanly
  - evaluate next low-risk typed seam in scanner-report/rendering-adjacent paths only if type gate remains stable
- current full-suite status: green (`727 passed`)

## Progress Note (2026-03-26, Phase 3 final-output payload typed seam + cautious gate expansion slice)

Completed the next low-risk Phase 3 typed seam adjacent to scanner-report/rendering paths:

- introduced `FinalOutputPayload` TypedDict and `build_final_output_payload` helper in `src/prism/scanner_submodules/output.py` to stabilize payload shaping for `render_final_output`
- updated `src/prism/scanner_submodules/scan_output_primary.py` to build and pass the typed payload contract at the render seam (behavior-preserving, no output-shape changes)
- added focused contract tests in `src/prism/tests/test_scan_output_primary.py` for TypedDict annotation and payload-builder parity
- cautiously expanded incremental mypy gate by one module after focused tests were green: added `src/prism/scanner_submodules/output.py` to both `tox.ini` and `.pre-commit-config.yaml`

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_output_primary.py src/prism/tests/test_scan_output_emission.py -k "final_output_payload or render_and_write_scan_output or render_primary_scan_output or scan_output_primary"` (`6 passed, 10 deselected`)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 9 source files`)
- full suite: `.venv/bin/python -m pytest -q` (`728 passed`)

### Anti-Stall Queue Refresh (2026-03-26, slice 15)

- completed slices count (Phase 3): 15
- queue status: active, no blockers
- next queued slices:
  - typed seam for scanner report issue-list row rendering (explicit row contract + helper) with focused markdown-parity tests
  - evaluate one additional cautious mypy gate expansion candidate only after the above seam remains stable
- current full-suite status: green (`728 passed`)

## Progress Note (2026-03-26, Phase 3 scanner-report issue-list row typed seam + cautious gate expansion slice)

Completed the next queued Phase 3 typed seam focused on scanner-report issue-list row rendering:

- introduced `ScannerReportIssueListRow` TypedDict and explicit helpers in `src/prism/scanner_submodules/scanner_report.py`:
  - `build_scanner_report_issue_list_row`
  - `render_scanner_report_issue_list_row`
- preserved existing markdown behavior by routing unresolved/ambiguous row bullet composition through the helper while keeping identical fallback text (`Unknown source.`, `Multiple possible sources.`)
- added focused seam/contract tests in `src/prism/tests/test_scan_metrics.py`
- added focused markdown parity coverage in `src/prism/tests/test_scan.py` for explicit-reason and fallback-reason row rendering

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan.py src/prism/tests/test_scan_metrics.py -k "scanner_report_markdown or scanner_report_issue_list_row or scanner_report_typed_render_input_contract_annotations or extract_scanner_counters"` (`14 passed, 149 deselected`)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 9 source files`)
- full suite: `.venv/bin/python -m pytest -q` (`730 passed`)

Optional cautious type-gate expansion (kept):

- probed expansion candidate with direct mypy run including `src/prism/scanner_submodules/runbook.py` (`Success: no issues found in 10 source files`)
- expanded incremental type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include `src/prism/scanner_submodules/runbook.py`
- re-validated with `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 10 source files`)

### Anti-Stall Queue Refresh (2026-03-26, slice 16)

- completed slices count (Phase 3): 16
- queue status: active, no blockers
- next queued slices:
  - typed seam for scanner-report YAML-parse-failure row rendering (explicit row contract + helper) with focused markdown-parity tests
  - evaluate one additional cautious mypy gate expansion candidate only after the above seam remains stable
- current full-suite status: green (`730 passed`)

## Progress Note (2026-03-26, Phase 3 scanner-report YAML-parse-failure row typed seam + cautious gate expansion slice)

Completed the next queued Phase 3 typed seam focused on scanner-report YAML parse-failure row rendering:

- introduced `ScannerReportYamlParseFailureRow` TypedDict and explicit helpers in `src/prism/scanner_submodules/scanner_report.py`:
  - `build_scanner_report_yaml_parse_failure_row`
  - `render_scanner_report_yaml_parse_failure_row`
- preserved markdown behavior by routing YAML parse-failure row composition through the helper while keeping identical fallback output (`parse error`) and location shaping (`file[:line:column]`)
- added focused seam/contract tests in `src/prism/tests/test_scan_metrics.py`
- added focused markdown parity coverage in `src/prism/tests/test_scan.py` for mixed explicit/fallback parse-failure rows

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan.py src/prism/tests/test_scan_metrics.py -k "scanner_report_markdown or scanner_report_yaml_parse_failure_row or yaml_parse_failure_rows_keep_parity or scanner_report_typed_render_input_contract_annotations or scanner_report_issue_list_row"` (`9 passed, 156 deselected`)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 10 source files`)
- full suite: `.venv/bin/python -m pytest -q` (`732 passed`)

Optional cautious type-gate expansion (kept):

- probed expansion candidate with direct mypy run including `src/prism/scanner_submodules/readme_config.py` (`Success: no issues found in 1 source file`)
- expanded incremental type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include `src/prism/scanner_submodules/readme_config.py`
- re-validated with `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 11 source files`)

### Anti-Stall Queue Refresh (2026-03-26, slice 17)

- completed slices count (Phase 3): 17
- queue status: active, no blockers
- next queued slices:
  - evaluate next low-risk typed seam in scanner-report rendering-adjacent paths (section-row or metadata-normalization seam) with focused parity tests
  - consider one additional cautious mypy gate expansion candidate only if the next seam remains stable
- current full-suite status: green (`732 passed`)

## Progress Note (2026-03-26, Phase 3 scanner-report section-render typed seam slice)

Completed the next queued Phase 3 typed seam focused on scanner-report section rendering:

- introduced `ScannerReportSectionRenderInput` TypedDict and explicit helpers in `src/prism/scanner_submodules/scanner_report.py`:
  - `build_scanner_report_section_render_input`
  - `render_scanner_report_section`
- preserved markdown behavior by routing section heading/body line composition through the helper while keeping identical section title underline and spacing output
- added focused seam/contract tests in `src/prism/tests/test_scan_metrics.py` for TypedDict annotation shape and section-row render parity

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_metrics.py src/prism/tests/test_scan.py -k "scanner_report_section_render or scanner_report_markdown"`
- type gate: `.venv/bin/python -m tox -e typecheck`
- full suite: `.venv/bin/python -m pytest -q`

### Anti-Stall Queue Refresh (2026-03-26, slice 18)

- completed slices count (Phase 3): 18
- queue status: active, no blockers
- next queued slices:
  - typed seam for scanner-report metadata normalization (coercion helper for optional metadata fields) with focused parity tests
  - evaluate one additional cautious mypy gate expansion candidate only if metadata-normalization seam remains stable
- current full-suite status: green (re-validated in this slice)

## Progress Note (2026-03-26, Phase 3 scanner-report metadata-normalization typed seam + cautious gate expansion slice)

Completed the next queued Phase 3 typed seam focused on scanner-report metadata normalization:

- introduced `NormalizedScannerReportMetadata` TypedDict and `coerce_optional_scanner_report_metadata_fields` helper in `src/prism/scanner_submodules/scanner_report.py`
- preserved markdown behavior by routing optional metadata fields (`scanner_counters`, `variable_insights`, `features`, `yaml_parse_failures`) through typed coercion to stable container defaults before rendering
- updated `build_scanner_report_markdown` to consume normalized metadata fields while preserving output shape and ordering
- added focused seam/contract tests in `src/prism/tests/test_scan_metrics.py` for TypedDict annotation coverage and optional-field coercion parity

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_metrics.py src/prism/tests/test_scan.py -k "scanner_report or metadata_coercion or scanner_report_markdown"` (`13 passed, 155 deselected`)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 11 source files`)
- full suite: `.venv/bin/python -m pytest -q` (`735 passed`)

Optional cautious type-gate expansion (kept):

- probed expansion candidate with direct mypy run including `src/prism/scanner_submodules/style_vars.py` (`Success: no issues found in 12 source files`)
- expanded incremental type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include `src/prism/scanner_submodules/style_vars.py`
- re-validated with `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 12 source files`)

### Anti-Stall Queue Refresh (2026-03-26, slice 19)

- completed slices count (Phase 3): 19
- queue status: active, no blockers
- next queued slices:
  - evaluate next low-risk typed seam in scanner-report rendering-adjacent paths (renderer-input/result normalization) with focused parity tests
  - consider one additional cautious mypy gate expansion candidate only if the next seam remains stable
- current full-suite status: green (`735 passed`)

## Progress Note (2026-03-26, Phase 3 renderer-input/result normalization seam slice)

Completed the next queued Phase 3 typed seam focused on scanner-report rendering-adjacent renderer-input/result normalization:

- introduced `SectionBodyRenderResult` TypedDict in `src/prism/scanner_submodules/scanner_report.py` as the typed result contract for section body renderer invocations (`body: str`, `has_content: bool`)
- added `normalize_section_body_render_result(raw: str) -> SectionBodyRenderResult` helper that strips the raw renderer string and computes `has_content`, replacing ad-hoc `.strip()` + `if not body` at the call site
- added `invoke_readme_section_renderer(render_input, renderer) -> SectionBodyRenderResult` helper that unpacks `ReadmeSectionRenderInput` to positional args, calls the renderer, and normalizes the result in one place
- updated the section-render loop inside `build_scanner_report_markdown` to use `invoke_readme_section_renderer` instead of manual positional unpacking + inline `.strip()`, shrinking the call site and centralizing normalization at the seam
- preserved markdown output shape and behavior end-to-end; no output-shape changes

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_metrics.py src/prism/tests/test_scan.py -k "section_body_render_result or invoke_readme_section_renderer or invoke_renderer_section_order or scanner_report_markdown or scanner_report_section"` (`12 passed, 161 deselected`)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 12 source files`)
- full suite: task `tests: full` (`740 passed`)

Optional cautious type-gate expansion (kept):

- probed expansion candidate with direct mypy run including `src/prism/scanner_submodules/requirements.py` (`Success: no issues found in 1 source file`)
- expanded incremental type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include `src/prism/scanner_submodules/requirements.py`
- re-validated with `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 13 source files`)

### Anti-Stall Queue Refresh (2026-03-26, slice 20)

- completed slices count (Phase 3): 20
- queue status: active, no blockers
- next queued slices:
  - evaluate next low-risk typed seam in scanner-report or output-adjacent paths (e.g., typed result contract for `render_final_output` or annotation-counter shaping helpers) with focused parity tests
  - consider one additional cautious mypy gate expansion candidate only if the next seam remains stable
- current full-suite status: green (`740 passed`)

## Progress Note (2026-03-27, Phase 3 annotation-quality counter typed seam + gate expansion slice)

Completed the next queued Phase 3 typed seam focused on annotation-quality counter shaping:

- introduced `AnnotationQualityCounters` TypedDict in `src/prism/scanner_submodules/scanner_report.py` with `disabled_task_annotations: int` and `yaml_like_task_annotations: int`
- added `coerce_annotation_quality_counters_from_features(features: dict[str, Any]) -> AnnotationQualityCounters` helper centralizing the int-coercion logic previously scattered inline in `extract_scanner_counters`
- updated `extract_scanner_counters` to use the typed helper internally; no output-shape changes
- added focused seam/contract tests in `src/prism/tests/test_scan_metrics.py` for TypedDict annotation shape, coercion parity (missing keys, None values, string ints), and `extract_scanner_counters` regression

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan_metrics.py src/prism/tests/test_scan.py -k "annotation_quality or coerce_annotation_quality or extract_scanner_counters_annotation"` (16 passed)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 13 source files`)
- full suite: task `tests: full` (`746 passed`)

Optional cautious type-gate expansion (kept):

- probed `src/prism/scanner_submodules/doc_insights.py` — clean
- expanded type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include `doc_insights.py`
- re-validated with `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 14 source files`)

### Anti-Stall Queue Refresh (2026-03-27, slice 21)

- completed slices count (Phase 3): 21
- queue status: active, no blockers
- next queued slices:
  - evaluate `style_guide.py` for gate inclusion (it has mypy errors requiring type-annotation fixes)
  - evaluate remaining scanner_submodule files for typed seam opportunities
- current full-suite status: green (`746 passed`)

## Progress Note (2026-03-27, Phase 3 style_guide.py type-annotation fixes + gate expansion slice)

Completed the next Phase 3 typing slice focused on expanding the gate to `style_guide.py`:

- added `TypedDict` import and `_SectionTitleBucket` TypedDict in `src/prism/scanner_submodules/style_guide.py` to replace the `dict[str, object]` bucket annotation in `_build_section_title_stats`, resolving 7 type errors
- replaced `by_section_id.get("unknown", {}).get("count", 0)` with a temp-variable isinstance pattern to resolve the remaining `call-overload` error
- renamed `intro_lines` to `intro_lines_nb` in the `nested_bullets` branch to eliminate the `no-redef` error (duplicate name in sibling elif branches)
- preserved markdown parsing behavior end-to-end; no output-shape changes (32 style_guide-related tests pass)
- expanded type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include `style_guide.py`

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/ -k "style_guide or style_heading or style_section or parse_style_readme"` (32 passed)
- type gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 15 source files`)
- full suite: task `tests: full` (`746 passed`)

### Anti-Stall Queue Refresh (2026-03-27, slice 22)

- completed slices count (Phase 3): 22
- queue status: active, no blockers
- next queued slices:
  - fix remaining mypy errors in `task_parser.py` (5 errors: annotation list type and isinstance narrowing patterns) and add `task_parser.py` + `variable_extractor.py` to gate
  - consider probing `scanner.py` itself for gate inclusion
- current full-suite status: green (`746 passed`)

## Progress Note (2026-03-27, Phase 3 task_parser.py type fixes + gate expansion slice)

Completed the next Phase 3 typing slice focused on expanding the gate to `task_parser.py` and `variable_extractor.py`:

- widened `annotations: list[dict[str, str]]` to `list[dict[str, object]]` in the task catalog loop in `task_parser.py` to match the actual return type of `_extract_task_annotations_for_file` (resolves 2 arg-type errors)
- replaced double-call isinstance conditional expressions for `driver`, `verifier`, and `platforms_raw` with hoisted temp variables so mypy can narrow correctly (resolves 3 union-attr errors)
- `variable_extractor.py` was already clean, requiring no changes
- preserved scanner behavior end-to-end; 195 annotation/molecule/scanner_internals tests pass

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/ -k "task_parser or annotation or molecule or scanner_internals"` (195 passed)
- type gate (`task_parser.py` + `variable_extractor.py`): `Success: no issues found in 2 source files`
- expanded gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 17 source files`)
- full suite: task `tests: full` (`746 passed`)

### Anti-Stall Queue Refresh (2026-03-27, slice 23)

- completed slices count (Phase 3): 23
- queue status: active, no blockers
- next queued slices:
  - probe and fix `scanner.py` (2 errors: dict.get key type, return type annotation for `_collect_scan_identity_and_artifacts`) and add to gate
  - then probe remaining top-level modules (`api.py`, `cli.py`, etc.)
- current full-suite status: green (`746 passed`)

## Progress Note (2026-03-27, Phase 3 scanner.py type fixes + gate expansion slice)

Completed the next Phase 3 typing slice expanding the gate to `scanner.py`:

- replaced `section_title_overrides.get(section.get("id"))` with a temp-variable pattern to avoid passing `Any | None` as a `str` key (resolves `arg-type` error at dict.get call)
- corrected `_collect_scan_identity_and_artifacts` return type annotation from `tuple[str, ...]` to `tuple[Path, ...]` to match the actual `Path` return from `_resolve_scan_identity`
- preserved scanner behavior end-to-end; 304 scan/scanner_internals tests pass
- expanded type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include `scanner.py`

Validation for this slice:

- focused: `.venv/bin/python -m pytest -q src/prism/tests/test_scan.py src/prism/tests/test_scanner_internals.py` (304 passed)
- probe: `mypy ... src/prism/scanner.py` — `Success: no issues found in 1 source file`
- expanded gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 18 source files`)
- full suite: task `tests: full` (`746 passed`)

### Anti-Stall Queue Refresh (2026-03-27, slice 24)

- completed slices count (Phase 3): 24
- queue status: active, no blockers
- next queued slices:
  - probe remaining top-level modules for gate inclusion (api.py, cli.py, pattern_config.py, collection_plugins.py, feedback.py, init.py, _jinja_analyzer.py)
  - fix any minimal type errors found and add all clean modules to gate in one slice
- current full-suite status: green (`746 passed`)

## Progress Note (2026-03-27, Phase 3 full package gate expansion slice)

Completed the final Phase 3 gate expansion, achieving full mypy coverage of the entire prism package:

- fixed `cli.py` line 1306: `return int(exc.code)` where `exc.code` is `str | int | None` — replaced with `return int(exc.code) if exc.code is not None else 0`
- all other top-level modules (`api.py`, `pattern_config.py`, `collection_plugins.py`, `feedback.py`, `init.py`, `_jinja_analyzer.py`) were already clean
- expanded type gate scope in `tox.ini` and `.pre-commit-config.yaml` to include all 7 remaining top-level modules

Validation for this slice:

- probe: `mypy ... src/prism/{api,cli,pattern_config,collection_plugins,feedback,init,_jinja_analyzer}.py` — `Success: no issues found in 7 source files`
- expanded gate: `.venv/bin/python -m tox -e typecheck` (`Success: no issues found in 25 source files`)
- full suite: task `tests: full` (`746 passed`)

### Anti-Stall Queue Refresh (2026-03-27, slice 24 complete — Phase 3 gate queue exhausted)

- completed slices count (Phase 3): 25 (slices 20–24 this session)
- queue status: **Phase 3 mypy gate queue exhausted** — entire prism package now under incremental type gate

## Progress Note (2026-03-27, CI typecheck integration)

Integrated `tox -e typecheck` into the CI workflow so mypy runs on every push and pull request:

- added a `Run typecheck` step to `.github/workflows/prism.yml` in the `tests` job, placed after `Install dependencies` and before `Run tests`
- no new jobs, no matrix changes, no permission changes — minimal diff
- gate covers all 25 source files (full prism package) as established by Phase 3 slices above
- YAML syntax validated; `tox` is already present in `.[dev]` so no install changes required
- gate scope: 25 source files (all `scanner_submodules/*.py` + `scanner.py` + `api.py` + `cli.py` + `pattern_config.py` + `collection_plugins.py` + `feedback.py` + `init.py` + `_jinja_analyzer.py` + `repo_services.py`)
- remaining longer-term opportunities (not currently queued):
  - further tighten internal dict types in `scanner.py` (currently many `dict[str, Any]` payloads)
  - typed seam for `render_readme` callable alias in `scan_output_primary.py`
  - consider expanding `follow-imports` scope to catch cross-module type drift
- current full-suite status: green (`746 passed`)

## Phase 4 Completion Note (2026-03-27)

Documentation consolidation complete (Workstream 4 success criteria met):

- `docs/dev_docs/architecture.md`: added Scanner Submodule Layout table (7 new submodules + `repo_services.py`), Typed Seam Contracts inventory, and Mypy Gate section
- `docs/dev_docs/roadmap.md`: phases 1–3 marked complete with brief descriptions in Delivered Themes
- `old_docs/README.md`: legacy notice added at the top
- `docs/dev_docs/modernization-plan.md`: this completion note added

## Objectives

- shrink the core maintenance hotspots in the scanner and CLI paths
- separate library-facing code from CLI-only orchestration
- make scanner contracts more explicit through typed internal models
- strengthen validation gates so refactors fail fast
- clean up developer-facing documentation for the new internal boundaries

## Why This Plan Exists

Current complexity is concentrated in a small set of files:

- `src/prism/scanner.py`
- `src/prism/cli.py`
- `src/prism/api.py`
- `src/prism/scanner_submodules/task_parser.py`
- `src/prism/scanner_submodules/variable_extractor.py`

The codebase already shows the right direction through extracted modules such as `scanner_submodules/task_parser.py`, `scanner_submodules/readme_config.py`, and `scanner_submodules/variable_extractor.py`. The next step is to turn partial extraction into stable internal seams.

## Principles

- preserve current behavior first, then simplify internals behind tests
- move one responsibility at a time instead of attempting a full rewrite
- keep CLI concerns separate from reusable library services
- favor deterministic data contracts over large mutable dictionaries
- expand enforcement gradually so modernization does not stall delivery

## Non-Goals

- rewriting the scanner around a new framework
- changing Prism output formats as part of the first pass
- broad feature expansion unrelated to maintainability or correctness
- dropping current scanner heuristics before equivalent coverage exists

## Workstreams

## Workstream 1: Core Boundaries

Scope:

- define internal boundaries for repo intake, scan orchestration, config loading, and output rendering
- reduce direct coupling between `api.py`, `cli.py`, and `scanner.py`
- continue moving cohesive logic out of `scanner.py`

Primary files:

- `src/prism/scanner.py`
- `src/prism/cli.py`
- `src/prism/api.py`
- `src/prism/scanner_submodules/*.py`

Success criteria:

- API code no longer imports CLI-private helpers
- scanner orchestration delegates to smaller focused modules
- the main scan path has fewer responsibilities per file

## Workstream 2: Typed Internal Contracts

Scope:

- replace large ad hoc dictionaries passed through scan orchestration with explicit internal models
- introduce typed request and response structures at the seams between API, scanner, and renderers
- clarify which fields are required, derived, or optional

Primary files:

- `src/prism/api.py`
- `src/prism/scanner.py`
- `src/prism/scanner_submodules/output.py`
- `src/prism/scanner_submodules/scanner_report.py`

Success criteria:

- new internal seam objects are typed and documented
- refactors can remove dead keys and implicit contracts safely
- editor and CI feedback improve for scan-pipeline changes

## Workstream 3: Tooling And Validation

Scope:

- add a static type-check gate alongside existing test, lint, and formatting checks
- keep test coverage concentrated around the extracted seams
- make quick validation paths clear for incremental refactors

Primary files:

- `tox.ini`
- `.pre-commit-config.yaml`
- `.github/workflows/prism.yml`
- `src/prism/tests/test_scan.py`
- `src/prism/tests/test_scanner_internals.py`
- `src/prism/tests/test_api.py`

Success criteria:

- type checking runs in CI for targeted modules
- refactor slices have focused test selections documented
- full-suite validation remains part of the merge gate

## Workstream 4: Documentation And Repo Hygiene

Scope:

- document the intended module boundaries and service layers
- reduce ambiguity between current docs and legacy material
- keep modernization progress visible in developer docs

Primary files:

- `docs/dev_docs/architecture.md`
- `docs/dev_docs/roadmap.md`
- `docs/dev_docs/README.md`
- `old_docs/README.md`

Success criteria:

- current architecture docs reflect the actual seam layout
- active docs are clearly separated from legacy references
- future work can be tracked against this plan without duplicating context

## Phase Plan

## Phase 0: Baseline And Seam Mapping

Goals:

- record the current module responsibilities and coupling points
- identify the highest-risk helper flows in `scanner.py`, `cli.py`, and `api.py`
- define the first extraction sequence before changing behavior

Deliverables:

- seam map for scanner, API, CLI, and renderer boundaries
- list of CLI-private helpers currently used outside the CLI layer
- initial target set for typed models

Exit criteria:

- the first refactor slice is small enough to land without broad churn
- the regression test set for that slice is known in advance

## Phase 1: API And CLI Separation

Goals:

- move repository-fetch, sparse-clone, temp-workspace, and similar non-CLI services into shared modules
- stop treating `cli.py` as a dependency source for the public API

Deliverables:

- shared service module for repo intake and workspace management
- `api.py` imports only stable internal services rather than CLI-private helpers
- focused tests covering the extracted service behavior

Exit criteria:

- CLI and API call the same lower-level service layer
- API functionality remains unchanged at the public interface

## Phase 2: Scanner Orchestration Decomposition

Goals:

- reduce the size and responsibility count of `scanner.py`
- move cohesive logic into submodules with explicit responsibilities

Candidate extraction lanes:

- scan request normalization
- role/collection discovery and path handling
- scanner counters and uncertainty aggregation
- output payload assembly

Deliverables:

- smaller orchestration entry points in `scanner.py`
- extracted modules with narrow public surfaces
- tests moved or added at the new seam boundaries

Exit criteria:

- `scanner.py` is primarily an orchestrator, not a catch-all implementation file
- new functionality is added in submodules by default

## Phase 3: Typed Models And Static Analysis Gate

Goals:

- introduce typed models around scan inputs, scan results, and report payloads
- add a type-check gate for the newly stabilized modules first

Deliverables:

- internal data structures for scan requests and results
- `mypy` or `pyright` integrated into local validation and CI
- documentation for the typed seam contracts

Exit criteria:

- at least the modernized seam modules are type-checked in CI
- dict-shaped implicit contracts are reduced on the main execution path

## Phase 4: Documentation Consolidation And Cleanup

Goals:

- update architecture and contributor docs to reflect the new structure
- reduce confusion caused by legacy docs and stale implementation assumptions

Deliverables:

- refreshed architecture narrative in developer docs
- roadmap updates reflecting completed modernization slices
- explicit note on what remains in `old_docs`

Exit criteria:

- contributors can follow the current internal structure from docs alone
- obsolete guidance is either archived or clearly marked as legacy

## Validation Strategy

- keep focused tests for each slice close to the changed seam
- run the full pytest suite before merging structural changes
- add type-check enforcement incrementally, starting with newly extracted modules
- avoid combining behavior changes with structural moves in the same patch where possible

## Risks And Controls

- risk: broad exception handling hides regressions
  control: add targeted tests around extracted services before moving error handling

- risk: large dict payloads make refactors brittle
  control: introduce typed wrappers at the boundaries before deeper internal changes

- risk: refactor churn overwhelms review
  control: limit each slice to one responsibility and keep public behavior fixed

- risk: docs drift from implementation during phased work
  control: update `architecture.md` and `roadmap.md` whenever a phase closes

## Recommended First Slice

Start with API and CLI separation.

Reason:

- it improves the public library boundary without forcing immediate scanner rewrites
- it creates a reusable service layer that later scanner and repo-intake work can share
- it is easier to validate than a large scanner decomposition pass

Initial target files:

- `src/prism/api.py`
- `src/prism/cli.py`
- new shared service module under `src/prism/`
- `src/prism/tests/test_api.py`
- `src/prism/tests/test_cli_repo.py`

## Tracking

Update this plan when a phase starts, when scope changes materially, or when a phase is complete and ready to move into the completed plans archive.
