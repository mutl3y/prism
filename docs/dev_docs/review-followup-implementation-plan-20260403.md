---
layout: default
title: Review Follow-Up Implementation Plan
---

Trackable implementation plan derived from the recent broad Prism review and calibrated to the current package-owned architecture.

## Objective

Turn the review feedback into a practical implementation lane that:

- finishes the remaining scanner-facade ownership cleanup without breaking the stable public facade
- hardens reliability and diagnostics where the codebase is still brittle
- adds measured performance work instead of speculative optimization
- improves test and security hygiene in the places most likely to matter at scale

## Planning Note

This plan intentionally adjusts several raw review suggestions to match Prism's current architecture.

- `prism.scanner_analysis` has already been renamed to `prism.scanner_reporting`
- the goal is not to delete `prism.scanner` as a public facade, but to finish retiring non-essential ownership from it
- runtime validation should start with targeted contract hotspots, not a wholesale `pydantic` migration
- async I/O, multiprocessing, and ML-style `prism-learn` integration should follow profiling and contract stabilization, not precede them

## Recommendation Disposition

### Adopt Now

- finish canonical ownership cleanup in `prism.scanner`
- add targeted runtime contract guards in critical builders and request/result boundaries
- add profiling and benchmark visibility for scanner hot paths
- improve structured diagnostics for malformed inputs and degraded scans
- expand parser and contract stress testing
- strengthen secret-detection and dependency-hygiene coverage

### Adopt Later

- multiprocessing or distributed scan execution
- broader plugin/extension ecosystem work
- deeper `prism-learn` feedback-loop automation

### Do Not Adopt As Written

- do not fully remove `prism.scanner` as a public facade; keep it small and stable
- do not introduce a repo-wide `pydantic` rewrite unless targeted validation proves insufficient
- do not add async or parallelism before measured profiling identifies real bottlenecks

## Success Criteria

- `prism.scanner` owns only stable public entrypoints and thin compatibility seams
- critical request, payload, and variable-row boundaries have runtime validation at construction time
- performance work is driven by measured hot paths with baselines checked into the repo
- malformed YAML/Jinja and degraded scan modes produce structured, actionable diagnostics
- parser and contract tests cover more adversarial and edge-case inputs
- active docs stay aligned with the implemented package-owned architecture

## Current Execution Snapshot

- W1.1 first slice complete: duplicated runtime-policy orchestration was moved behind a canonical helper in `prism.scanner_core.scan_runtime`, reducing facade-owned execution flow in `prism.scanner`
- W1.1 second slice complete: scanner-report rendering now binds directly to the public `prism.scanner_readme.render_guide_section_body` seam, retiring an extra private README rendering helper from `prism.scanner`
- W1.1 third slice complete: two scanner facade forwarding helpers now use late-bound canonical bindings instead of private wrapper functions, trimming `prism.scanner` helper ownership while preserving monkeypatch-friendly seam behavior in the test contract
- W1.3 first slice complete: active docs now state explicitly that stable top-level facades are not the default extension targets
- W1.2 first slice complete: builder-level runtime validation now guards key payload/list/dict shapes in `prism.scanner_data.contracts_output` and `prism.scanner_data.contracts_variables`
- W1.2 second slice complete: request-boundary validation now rejects malformed path fields, bool flags, string-list options, and per-scan `policy_context` payloads before runtime orchestration proceeds, with canonical ownership kept in `prism.scanner_data.contracts_request` so `prism.scanner_core.scan_request` stays within guardrail budgets
- W1.2 third slice complete: `RunScanOutputPayload` validation is now shared between the builder owner and `prism.scanner_core.output_orchestrator`, so output/render orchestration rejects malformed payload dicts before metadata cloning and file emission
- W1.2 fourth slice complete: `VariableDiscovery` now validates constructor-time request option shapes through the canonical request-contract owner, rejecting malformed role paths, bool flags, and string-list option fields before discovery orchestration starts
- W1.2 fifth slice complete: output orchestrator construction and explicit runbook-sidecar emission now validate option/path/metadata shapes through shared output-contract validators before render or file-write flows begin
- W1.2 sixth slice complete: `FeatureDetector` constructor validation now flows through the canonical request-contract owner, rejecting malformed role paths and exclude-pattern shapes before feature analysis begins
- W2.1 first slice complete: `scripts/profile_role_scan.py` now provides a repeatable local timing/profile harness for stable role fixtures, and `docs/dev_docs/scan-performance-baseline-20260404.md` records the first measured baseline plus an initial YAML-loading hotspot summary
- W2.2 first slice complete: task-file traversal now uses a stat-keyed in-process YAML cache, focused tests cover cache reuse/invalidation, and the updated baseline doc records a 12-36% timing improvement across representative fixtures with reduced YAML hot-path dominance
- W2.3 first slice complete: public API and JSON output payloads now expose normalized `warnings` records derived from degraded-scan metadata, YAML parse failures, and config warning collectors
- W3.1 first slice complete: parser/Jinja/contract seams now have generated malformed-input coverage in `test_task_parser.py`, `test_scanner_internals.py`, and `test_contracts.py`
- W3.2 first slice complete: exclude-path normalization now drops unsafe absolute/parent-traversal patterns, secret detection recognizes additional common credential families, and dependency review is automated through `.github/workflows/dependency-hygiene.yml` plus `docs/dev_docs/dependency-hygiene.md`
- Closure gate complete: `pytest -q`, `ruff check src/prism`, `black --check src/prism`, and `tox -e typecheck` all passed together on 2026-04-04

## Wave 1: Facade And Contract Hardening

### W1.1 Retire remaining non-essential scanner facade ownership

Status: `complete`

Scope:

- review the remaining internal composition and helper seams in `src/prism/scanner.py`
- move any still-owned request/context assembly or reporting glue into canonical owners under `prism.scanner_core`, `prism.scanner_config`, `prism.scanner_reporting`, and `prism.scanner_readme`
- keep `prism.scanner` as the stable public entrypoint, but not the default home for new behavior

Primary targets:

- [`scanner.py`](/raid5/source/test/prism/src/prism/scanner.py)
- [`scan_request.py`](/raid5/source/test/prism/src/prism/scanner_core/scan_request.py)
- [`scan_runtime.py`](/raid5/source/test/prism/src/prism/scanner_core/scan_runtime.py)
- [`output_orchestrator.py`](/raid5/source/test/prism/src/prism/scanner_core/output_orchestrator.py)

Acceptance criteria:

- no new canonical runtime logic is introduced in `prism.scanner`
- scanner architecture guardrails still pass
- facade exports remain stable for user-facing scan entrypoints

Verification:

```bash
.venv/bin/python -m pytest -q src/prism/tests/test_scanner_architecture_guardrails.py src/prism/tests/test_scanner_decoupling_guardrails.py
.venv/bin/python -m ruff check src/prism/scanner.py src/prism/scanner_core
.venv/bin/python -m black --check src/prism/scanner.py src/prism/scanner_core
```

### W1.2 Add targeted runtime validation at critical contract boundaries

Status: `complete`

Scope:

- identify the highest-risk mutation and shape boundaries first
- add focused validation in builders and contract-construction seams instead of broad framework churn
- start with request normalization, variable-row construction, and public result payloads

Primary targets:

- [`builders.py`](/raid5/source/test/prism/src/prism/scanner_data/builders.py)
- [`scan_request.py`](/raid5/source/test/prism/src/prism/scanner_core/scan_request.py)
- [`contracts_request.py`](/raid5/source/test/prism/src/prism/scanner_data/contracts_request.py)
- [`contracts_output.py`](/raid5/source/test/prism/src/prism/scanner_data/contracts_output.py)
- [`variable_discovery.py`](/raid5/source/test/prism/src/prism/scanner_core/variable_discovery.py)

Recommended approach:

- prefer lightweight explicit validators or builder-time assertions
- reserve `dataclass` or `pydantic` adoption for clearly bounded hotspots if manual validation becomes noisy

Acceptance criteria:

- critical payload builders reject malformed or incomplete shapes deterministically
- validation failures produce stable, debuggable error text
- mypy remains green without introducing duplicate type systems everywhere

Verification:

```bash
.venv/bin/python -m pytest -q src/prism/tests/test_contracts.py src/prism/tests/test_scan_payload_builder.py src/prism/tests/test_variable_row_builder.py
.venv/bin/python -m tox -e typecheck
```

### W1.3 Record the final facade rule in active docs

Status: `complete`

Scope:

- document that top-level facades remain stable public seams but are no longer default extension targets
- align this with the package-owned capability map now that `prism.scanner_reporting` exists

Primary targets:

- [`architecture.md`](/raid5/source/test/prism/docs/dev_docs/architecture.md)
- [`package-capabilities.md`](/raid5/source/test/prism/docs/dev_docs/package-capabilities.md)

Acceptance criteria:

- docs clearly distinguish public facade stability from canonical ownership
- docs no longer imply that retiring the facade means deleting the public module

## Wave 2: Measured Performance And Diagnostics

### W2.1 Add profiling and baseline telemetry for scanner hot paths

Status: `complete`

Scope:

- add a repeatable profiling harness for representative role scans
- capture baseline timings for YAML loading, Jinja parsing, variable extraction, and output generation
- store the baseline and workflow in tracked docs or scripts

Primary targets:

- [`variable_extractor.py`](/raid5/source/test/prism/src/prism/scanner_extract/variable_extractor.py)
- [`task_parser.py`](/raid5/source/test/prism/src/prism/scanner_extract/task_parser.py)
- [`metrics.py`](/raid5/source/test/prism/src/prism/scanner_reporting/metrics.py)
- [`render.py`](/raid5/source/test/prism/src/prism/scanner_readme/render.py)

Acceptance criteria:

- the team can run one repeatable benchmark/profile command locally
- at least one baseline artifact or documented benchmark table exists
- performance work is prioritized from measured evidence, not guesses

Verification:

```bash
python3 -m cProfile -o /tmp/prism-profile.out -m prism.cli role <fixture-role> -o /tmp/README.md
```

### W2.2 Optimize only the measured hotspots

Status: `complete`

Scope:

- apply targeted caching or de-duplication where profiling proves repeat work
- evaluate Jinja AST parse reuse, repeated file reads, and redundant traversal work
- avoid async or multiprocessing unless the measured bottleneck clearly warrants it

Acceptance criteria:

- optimization PRs cite measured before/after evidence
- no architecture boundary regressions are introduced for speed alone

### W2.3 Improve structured degraded-scan diagnostics

Status: `complete`

Scope:

- expand stable error codes and warning surfaces for malformed YAML, parse failures, and best-effort skips
- ensure degraded scans explain what was skipped and why
- make output actionable for both human users and downstream consumers such as `prism-learn`

Primary targets:

- [`errors.py`](/raid5/source/test/prism/src/prism/errors.py)
- [`loader.py`](/raid5/source/test/prism/src/prism/scanner_io/loader.py)
- [`readme.py`](/raid5/source/test/prism/src/prism/scanner_config/readme.py)
- [`api_layer/common.py`](/raid5/source/test/prism/src/prism/api_layer/common.py)

Acceptance criteria:

- degraded scans expose stable warning/error records instead of silent best-effort loss
- API and CLI layers can present those diagnostics consistently

Verification:

```bash
.venv/bin/python -m pytest -q src/prism/tests/test_errors.py src/prism/tests/test_api.py src/prism/tests/test_output.py
```

## Wave 3: Test And Security Hygiene

### W3.1 Add adversarial parser and contract testing

Status: `complete`

Scope:

- add property-based or fuzz-style tests around YAML/Jinja parsing and contract construction
- stress malformed templates, edge-case YAML, oversized inputs, and unexpected field shapes
- reduce reliance on file-heavy integration tests for unit-level parser logic

Primary targets:

- [`test_task_parser.py`](/raid5/source/test/prism/src/prism/tests/test_task_parser.py)
- [`test_scanner_internals.py`](/raid5/source/test/prism/src/prism/tests/test_scanner_internals.py)
- [`test_contracts.py`](/raid5/source/test/prism/src/prism/tests/test_contracts.py)

Acceptance criteria:

- at least one property-based or generated-input suite exists for parser/contract hotspots
- unit-level tests cover malformed inputs more broadly than the current curated fixtures

### W3.2 Harden secret detection and input-safety checks

Status: `complete`

Scope:

- review secret-detection patterns for common credential families and vault-like markers
- verify path handling and file selection logic reject unsafe or unintended traversal patterns
- add dependency-vulnerability scanning or documented dependency-review workflow

Primary targets:

- [`variable_extractor.py`](/raid5/source/test/prism/src/prism/scanner_extract/variable_extractor.py)
- [`patterns.py`](/raid5/source/test/prism/src/prism/scanner_config/patterns.py)
- GitHub workflow coverage under `.github/workflows/`

Acceptance criteria:

- secret detection covers the most important missing credential families
- dependency hygiene has an explicit automated or documented review step

## Wave 4: Deferred Scale And Ecosystem Work

These items are intentionally deferred until Waves 1-3 land with evidence.

### W4.1 Parallel and large-repo scaling

Status: `deferred`

- collection/repo scan parallelization
- multiprocessing for role batches
- broader cache design for large repository scans

### W4.2 Prism-learn feedback-loop expansion

Status: `deferred`

- explicit compatibility contract review between Prism outputs and `prism-learn`
- structured downstream validation of Prism output changes
- future automation for learned pattern improvements only after core contracts and diagnostics are stable

## Suggested Execution Order

1. W1.1 facade ownership cleanup
2. W1.2 targeted runtime validation
3. W1.3 doc alignment
4. W2.1 profiling baseline
5. W2.3 diagnostics hardening
6. W2.2 hotspot optimization
7. W3.1 adversarial testing
8. W3.2 security and dependency hygiene

## Closure Gate

Treat the plan as complete only when all of the following are green together:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src/prism
.venv/bin/python -m black --check src/prism
.venv/bin/python -m tox -e typecheck
```
