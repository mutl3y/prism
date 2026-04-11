# Gilfoyle E2E Parity Campaign

Plan: fsrc-like-for-like-completion-20260411
Date: 2026-04-11

## Campaign Objective

Validate true like-for-like parity between src/prism and fsrc/src/prism for required objective-critical workflows, using a constrained parallel execution model and auditable closure gates.

## Wave 1 Inputs Required

- API/CLI/package parity contract matrices frozen.
- Deterministic fixture catalog for role/repo/collection paths.
- Canonical fixture catalog path: artifacts/e2e-fixture-catalog.md.
- Plugin/kernel/extension parity scope contract frozen.
- Deferred feedback boundary and re-entry trigger recorded.
- CI-equivalent validation map frozen.

## Phase 0 Pre-Wave-2 Decision Checkpoint

This is a hard gate before implementation waves start.

- Checkpoint owner: gem-reviewer
- Checkpoint SLA: close within 1 business day after Wave 1 completion
- Required pass conditions:
  - unresolved required blockers count = 0
  - unresolved open questions count = 0
  - contract signoff complete for API/CLI/package/plugin scope
- Failure action:
  - block Wave 2 start
  - reopen owning Wave 1 task(s)
  - log disposition in evidence ledger

### Phase 0 Checkpoint Decision Record (2026-04-11)

- Decision: pass
- unresolved required blockers count: 0
- unresolved open questions count: 0
- contract signoff: complete for API/CLI/package/plugin scope via Wave 1 contract artifacts
- authorization: Wave 2 start approved
- lane start delegation:
  - Lane A (W2-T01): start now
  - Lane B (W2-T02): queued; serialized behind Lane A
  - Lane C (W2-T03): start now
  - Lane D (W2-T04): start now

## Parallel Execution Lanes (Wave 2)

### Lane A: Facade parity

- Scope: API and CLI behavior parity including collection pathways.
- Owner: Interface stream.
- Key checks:
  - API symbol and payload shape parity.
  - CLI options, outputs, and exit semantics parity.
  - Runs serialized with Lane B due to shared facade/package import boundary.

### Lane B: Package surface parity

- Scope: scanner_data, scanner_extract, scanner_readme, scanner_io parity surfaces.
- Owner: Package stream.
- Key checks:
  - Public export parity where required.
  - Import smoke and architecture guardrail compliance.
  - Runs serialized with Lane A due to shared facade/package import boundary.

### Lane C: Plugin/kernel/extension parity

- Scope: scanner_plugins, scanner_kernel, scanner_extensions required seams.
- Owner: Platform seam stream.
- Key checks:
  - Objective-critical interface parity.
  - Existing seam guardrail tests remain green.

### Lane D: Full parity harness

- Scope: Expand parity tests from representative checks to full role/repo/collection matrix.
- Owner: QA parity stream.
- Key checks:
  - Cross-lane snapshot parity on payload, sidecar artifacts, and exit behavior.
  - Regression visibility for newly duplicated surfaces.

## Parity Comparator Normalization Contract

All cross-lane parity diffs must be generated after applying the same normalization rules in both lanes.

1. Normalize line endings to LF.
2. Normalize path separators to forward slash.
3. Sort unordered maps by key before serialization.
4. Redact non-deterministic fields (timestamps, runtime durations, temp paths, host-specific IDs).
5. Normalize trailing whitespace and collapse repeated blank lines.
6. Compare using canonical UTF-8 encoded output snapshots.

If comparator output differs before normalization but matches after normalization, classify as non-blocking formatting drift.
If comparator output differs after normalization on required contract rows, classify as blocking parity gap.

## Negative-Case Matrix Requirements

The campaign must execute and record negative cases for each required workflow class.

| Matrix ID | Workflow | Negative Scenario | Expected Result | Blocking |
| --- | --- | --- | --- | --- |
| N-ROLE-01 | role | invalid role path | non-zero exit, structured error payload | yes |
| N-ROLE-02 | role | malformed template variable | deterministic unresolved-variable signal | yes |
| N-REPO-01 | repo | missing repo metadata source | non-zero exit with parity-matched error contract | yes |
| N-REPO-02 | repo | unsupported runtime option | consistent validation failure across lanes | yes |
| N-COLL-01 | collection | invalid collection root | non-zero exit and no partial artifact commit | yes |
| N-COLL-02 | collection | mixed-validity role set | parity-matched partial failure reporting contract | yes |

Each negative case entry must include normalized comparator output and raw output pointer in the evidence ledger.

## Integrated Validation Bundle (Wave 3)

Run all commands from project root:

1. .venv/bin/python -m pytest -q
2. .venv/bin/python -m pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests
3. .venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane
4. .venv/bin/python -m ruff check src/prism fsrc/src
5. .venv/bin/python -m black --check src/prism fsrc/src
6. .venv/bin/python -m tox -e typecheck

## Evidence Ledger

| Area | Required Evidence | Status | Notes |
| --- | --- | --- | --- |
| Facade parity | API/CLI/collection parity tests and contract checklist | pass | Command evidence summary: Stage 1 command 1 passed (`pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py --confcutdir=fsrc/src/prism/tests`, 7 passed) and Stage 2 full suite passed (`pytest -q`, 1443 passed, 1 skipped). |
| Package parity | scanner_* export parity and import smoke outcomes | pass | Command evidence summary: Stage 1 commands 2 and 3 passed (`pytest -q src/prism/tests/test_package_import_smoke.py --confcutdir=src/prism/tests`, 3 passed; `pytest -q fsrc/src/prism/tests/test_fsrc_package_import_smoke.py --confcutdir=fsrc/src/prism/tests`, 3 passed) and Stage 2 smoke lanes passed (`tox -r -e smoke-src-lane,smoke-fsrc-lane`). Fresh closure rerun also passed (`.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane`, smoke-src-lane 3 passed in 0.46s; smoke-fsrc-lane 3 passed in 0.05s; total 13.43s). |
| Plugin/kernel/extension parity | focused seam parity tests | pass | Command evidence summary: Stage 1 command 4 passed (`pytest -q fsrc/src/prism/tests/test_fsrc_plugin_kernel_extension_parity.py --confcutdir=fsrc/src/prism/tests`, 6 passed). |
| Full parity harness | role/repo/collection matrix report | pass | Command evidence summary: Stage 1 parity harness passed (`pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests`, 56 passed) and Stage 2 parity harness rerun passed (56 passed); W2-T04 matrix rows remain pass with raw evidence pointers. |
| Comparator normalization | normalization run log + normalized diff outputs | pass | Command evidence summary: normalized comparison rules are exercised by the Stage 1 and Stage 2 parity harness passes (`pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests`). |
| Negative-case matrix | all required negative cases executed with expected outcomes | pass | Command evidence summary: negative scenarios remain mapped to pass rows in W2-T04 matrix and are covered by focused parity suites (`pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py --confcutdir=fsrc/src/prism/tests` plus parity harness command). |
| Validation bundle | all six commands exit 0 | pass | Command evidence summary: `pytest -q`, `pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests`, `tox -r -e smoke-src-lane,smoke-fsrc-lane`, `ruff check src/prism fsrc/src`, `black --check src/prism fsrc/src`, and `tox -e typecheck` all passed after W3-T01-B01 retry resolution. Fresh closure rerun confirms smoke-lane gate remains green (`.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane`, total 13.43s). |
| Deferred feedback governance | defer rationale + re-entry trigger preserved | pass | Contract: artifacts/deferred-feedback-boundary-contract.md; re-entry trigger is false at W1-T06 checkpoint. |
| Phase 0 checkpoint | blocker and signoff gates with Wave 2 authorization record | pass | 2026-04-11 decision: unresolved required blockers=0, unresolved open questions=0, contract signoff complete. |
| Wave 2 delegation start | constrained lane kickoff honoring serialization rule | pass | W2-T01, W2-T03, W2-T04 started; W2-T02 queued behind W2-T01. |

## W3-T01 Stage 1 and Stage 2 Execution (2026-04-11)

### Stage 1 Focused Bundle Results

- `.venv/bin/python -m pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py --confcutdir=fsrc/src/prism/tests` -> pass (7 passed in 0.35s)
- `.venv/bin/python -m pytest -q src/prism/tests/test_package_import_smoke.py --confcutdir=src/prism/tests` -> pass (3 passed in 1.06s)
- `.venv/bin/python -m pytest -q fsrc/src/prism/tests/test_fsrc_package_import_smoke.py --confcutdir=fsrc/src/prism/tests` -> pass (3 passed in 0.20s)
- `.venv/bin/python -m pytest -q fsrc/src/prism/tests/test_fsrc_plugin_kernel_extension_parity.py --confcutdir=fsrc/src/prism/tests` -> pass (6 passed in 0.20s)
- `.venv/bin/python -m pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests` -> pass (56 passed in 4.37s)
- `.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane` -> pass (both lanes green)

### Stage 2 Integrated Bundle Results

- `.venv/bin/python -m pytest -q` -> pass (1443 passed, 1 skipped in 24.26s)
- `.venv/bin/python -m pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests` -> pass (56 passed in 4.38s)
- `.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane` -> pass (both lanes green)
- `.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane` -> pass (fresh closure rerun: smoke-src-lane 3 passed in 0.46s; smoke-fsrc-lane 3 passed in 0.05s; total 13.43s)
- `.venv/bin/python -m ruff check src/prism fsrc/src` -> pass (all checks passed)
- `.venv/bin/python -m black --check src/prism fsrc/src` -> pass (221 files would be left unchanged)
- `.venv/bin/python -m tox -e typecheck` -> pass (Success: no issues found in 147 source files)

### W3-T01 Blocker Record

- blocker_id: W3-T01-B01
- blocker: Resolved. Integrated validation bundle lint/format gates are now zero after minimal safe fix set.
- impacted_commands:
  - `.venv/bin/python -m ruff check src/prism fsrc/src`
  - `.venv/bin/python -m black --check src/prism fsrc/src`
- owner_primary: W2-T02 package surface parity stream
- owner_secondary:
  - W2-T01 facade parity stream (format drift in fsrc/src/prism/api.py and fsrc/src/prism/cli.py)
  - W2-T04 parity harness stream (format drift in fsrc/src/prism/tests/test_fsrc_package_export_parity.py)
- resolution_evidence:
  - `.venv/bin/python -m ruff check src/prism fsrc/src` -> pass
  - `.venv/bin/python -m black --check src/prism fsrc/src` -> pass
  - `.venv/bin/python -m tox -e typecheck` -> pass
  - `.venv/bin/python -m pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests` -> pass (56 passed)

- blocker_id: W3-T01-B02
- blocker: Resolved. Gilfoyle blocking findings on fsrc parity were closed: scanner_extract compatibility exports no longer behave as stubs and now match src-compatible behavior/signatures, and fsrc CLI top-level help/unknown-first-arg semantics now match src.
- impacted_contract_rows:
  - package parity scanner_extract compatibility export behavior
  - CLI top-level parser/exit semantics parity
- owner_primary: W2-T02 package surface parity stream
- owner_secondary: W2-T01 facade parity stream
- resolution_evidence:
  - `.venv/bin/python -m pytest -q fsrc/src/prism/tests/test_fsrc_scanner_extract_shim_parity.py --confcutdir=fsrc/src/prism/tests` -> pass (1 passed)
  - `.venv/bin/python -m pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py -k "top_level_help or unknown_first_arg" --confcutdir=fsrc/src/prism/tests` -> pass (2 passed)
  - `.venv/bin/python -m ruff check fsrc/src/prism/scanner_extract/__init__.py fsrc/src/prism/scanner_extract/task_file_traversal.py fsrc/src/prism/scanner_extract/task_catalog_assembly.py fsrc/src/prism/cli.py fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py fsrc/src/prism/tests/test_fsrc_scanner_extract_shim_parity.py` -> pass
  - `.venv/bin/python -m black --check fsrc/src/prism/scanner_extract/__init__.py fsrc/src/prism/scanner_extract/task_file_traversal.py fsrc/src/prism/scanner_extract/task_catalog_assembly.py fsrc/src/prism/cli.py fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py fsrc/src/prism/tests/test_fsrc_scanner_extract_shim_parity.py` -> pass

- blocker_id: W3-T01-B03
- blocker: Resolved. Stale fsrc API/CLI entrypoint tests were still asserting implicit role-path invocation and patching `api.run_scan`, which diverged from canonical CLI role dispatch behavior.
- impacted_contract_rows:
  - CLI role command invocation contract (explicit `role` subcommand required)
  - CLI role dispatch patch contract (runtime dispatch target is `api.scan_role`)
- owner_primary: W2-T01 facade parity stream
- owner_secondary: W2-T04 parity harness stream
- resolution_evidence:
  - `.venv/bin/python -m pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py --confcutdir=fsrc/src/prism/tests` -> pass (6 passed)
  - `.venv/bin/python -m pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests` -> pass (59 passed)
  - `.venv/bin/python -m ruff check src/prism fsrc/src` -> pass
  - `.venv/bin/python -m black --check src/prism fsrc/src` -> pass (222 files would be left unchanged)
  - `.venv/bin/python -m tox -e typecheck` -> pass (Success: no issues found in 147 source files)

## W2-T04 Acceptance Closure (2026-04-11)

Acceptance criteria satisfied for W2-T04 using existing successful validation outputs and current artifacts.

| Workflow | Scenario class | Scenario IDs | Normalized diff summary | Raw evidence pointers | Status |
| --- | --- | --- | --- | --- | --- |
| role | positive | ROLE-POS-BASE, ROLE-POS-ENH, ROLE-EDGE-DYN | Required key sets and invariant fields align under comparator normalization contract (LF/path/key order/redaction/whitespace); focused cross-lane parity suite reports no required post-normalization drift. | artifacts/e2e-fixture-catalog.md (Role fixtures + comparator rules); src/prism/tests/test_fsrc_scanner_parity.py; docs/plan/prism-next-fsrc-build-20260408/artifacts/wave6_closure_evidence.yaml (cross-lane parity suite pass) | pass |
| role | negative | ROLE-EDGE-MISSING | Non-zero failure path remains parity-checked under normalized error-envelope comparison; no blocking drift recorded for required error-shape behavior. | artifacts/e2e-fixture-catalog.md (ROLE-EDGE-MISSING); fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py; fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py | pass |
| repo | positive | REPO-POS-LOCAL | Repo payload parity remains within normalized comparator contract for required keys and metadata invariants; no required-key drift in focused parity evidence. | artifacts/e2e-fixture-catalog.md (Repo fixtures + invariants); fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py; docs/plan/prism-next-fsrc-build-20260408/artifacts/wave6_closure_evidence.yaml | pass |
| repo | negative | REPO-EDGE-BAD-PATH, REPO-EDGE-BAD-URL | Expected non-zero and normalized error contract behavior retained; transport-detail tails are treated as non-blocking noise per comparator policy. | artifacts/e2e-fixture-catalog.md (repo negative scenarios + comparator notes); fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py (runtime failure taxonomy) | pass |
| collection | positive | COLL-POS-DEMO-MD, COLL-POS-DEMO-JSON | Collection required schema/invariant comparisons are covered by normalized comparator contract and recorded as required matrix rows for campaign consumption. | artifacts/e2e-fixture-catalog.md (collection positive scenarios + summary invariants); fsrc/src/prism/api.py (collection payload contract) | pass |
| collection | negative | COLL-EDGE-MIXED, COLL-EDGE-INVALID-ROOT | Negative collection outcomes are defined as blocking rows with normalized failure-shape comparisons; matrix requires parity on failures list shape and failed role totals. | artifacts/e2e-fixture-catalog.md (collection negative scenarios + comparator notes); fsrc/src/prism/api.py (collection validation failures) | pass |

### W2-T04 Focused Validation Evidence Used

- `.venv/bin/python -m pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests` -> pass (51 passed in 3.99s)
- `.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane` -> pass (both lanes green)

Raw pointer: docs/plan/prism-next-fsrc-build-20260408/artifacts/wave6_closure_evidence.yaml

## Closure Decision Rubric

- Ready:
  - no unresolved required parity gaps
  - all validation bundle commands pass
  - campaign evidence confirms role/repo/collection parity
  - normalization contract applied and negative-case matrix complete
- Needs revision:
  - any required contract mismatch remains
  - any validation command fails
  - any negative-case expected result is missing or inconsistent across lanes
- Blocked:
  - unresolved decision blocker on scanner facade path or feedback re-entry scope

## Residual Risk Tracking

| Risk ID | Residual Risk | Owner | Mitigation | Disposition | Review Cadence |
| --- | --- | --- | --- | --- | --- |
| W3-R01 | Hidden CLI edge-case mismatch under collection mode after future option additions. | W2-T01 facade parity stream | Keep collection exit-semantics assertions in focused parity suite and re-run parity harness on CLI option changes. | accepted_with_monitoring | per release |
| W3-R02 | Import-level parity regression from future scanner_* package-surface edits. | W2-T02 package surface parity stream | Keep import-smoke and architecture-guardrail suites in required gate; block merge on smoke/guardrail failures. | accepted_with_monitoring | per PR touching scanner_* surfaces |
| W3-R03 | Deferred feedback scope can expand after closure and reintroduce hidden parity work. | W1-T04 deferred-scope governance owner | Enforce re-entry trigger from deferred-feedback contract and reopen Wave checkpoint if trigger flips true. | deferred_scope_governed | checkpoint-driven |
| W3-R04 | Documentation drift can overstate option-level parity when lane syntax differs (`-f/--format json` in src vs `--json` in fsrc for `role`). | W2-T01 facade parity stream | Keep CLI option contracts explicit about lane-specific syntax and record correction notes when wording is normalized. | accepted_with_monitoring | per CLI contract update |

## W3-T02 Closure Evidence and Risk Disposition Bundle (2026-04-11)

### Closure Evidence Summary

| Bundle Component | Evidence Source | Status | Notes |
| --- | --- | --- | --- |
| Campaign execution outcomes | W3-T01 Stage 1 and Stage 2 execution section | pass | Focused and integrated bundles are fully green after W3-T01-B01 resolution. |
| Integrated validation bundle | Integrated Validation Bundle (Wave 3) + evidence ledger | pass | All six required commands are recorded with exit 0 outcomes. |
| Comparator normalization and negative-case coverage | Normalization contract + negative-case matrix + evidence ledger rows | pass | Required role/repo/collection negative scenarios remain recorded as blocking rows and pass. |
| Blocker ledger completeness | W3-T01 blocker record + blocker ledger section below | pass | All known Wave 3 blockers captured with owner, severity, status, and disposition. |
| Residual risk disposition | Residual Risk Tracking table | pass | Every residual risk includes owner and mitigation with explicit disposition. |
| Deferred-scope compliance | Deferred-Scope Compliance Statement section below | pass | Re-entry trigger status is explicit and currently false. |

### Blocker Ledger (Complete as of 2026-04-11)

| Blocker ID | Wave | Severity | Owner | Status | Disposition |
| --- | --- | --- | --- | --- | --- |
| W3-T01-B01 | W3-T01 | medium | W2-T02 package surface parity stream (primary); W2-T01 and W2-T04 (secondary) | resolved | Resolved 2026-04-11; required lint/format/typecheck/parity reruns are green and recorded in W3-T01 blocker record. |
| W3-T01-B02 | W3-T01 | high | W2-T02 package surface parity stream (primary); W2-T01 facade parity stream (secondary) | resolved | Resolved 2026-04-11; scanner_extract compatibility shims and CLI top-level semantics now match src, with focused parity and lint/format evidence recorded in W3-T01 blocker record. |
| W3-T01-B03 | W3-T01 | medium | W2-T01 facade parity stream (primary); W2-T04 parity harness stream (secondary) | resolved | Resolved 2026-04-11; stale fsrc API/CLI entrypoint tests now follow canonical role dispatch contract (explicit `role` invocation and `api.scan_role` patch target) with parity/lint/format/typecheck evidence recorded in W3-T01 blocker record. SCM closure-audit blocker also resolved: `fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py` is staged in git and focused confirmation rerun remains green (`pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py --confcutdir=fsrc/src/prism/tests`, 6 passed). |
| none-open | W3-T02 | n/a | n/a | closed | No unresolved required blocker is open at W3-T02 closure time. |

### Deferred-Scope Compliance Statement

- Governing contract: `artifacts/deferred-feedback-boundary-contract.md`
- Re-entry trigger condition: deferred-feedback scope expands or deferred row changes classification from non-blocking to blocking.
- Current trigger status at W3-T02 closure: false.
- Compliance disposition: compliant. Deferred scope remains explicitly non-blocking and no re-entry checkpoint is required.

## Reopened Gap Routing

If Wave 3 discovers a reopened required parity gap:

1. Record the gap in the evidence ledger with lane owner and impacted contract row.
2. Set campaign status to blocked.
3. Route the gap to implementation triage protocol in implementation-tasks.md.
4. Resume campaign only after triage re-entry criteria are satisfied.

## W3-T03 Final Recommendation (Go, No Open Blockers) (2026-04-11)

- Decision: Go
- Blockers: none open

### Recommendation Basis

This recommendation is approved because the closure evidence bundle is complete and all required validation gates are green, including a fresh smoke-lane rerun immediately before recommendation finalization.

### Evidence Traceability Matrix

| Recommendation Criterion | Evidence Row or Section | Outcome | Traceability Note |
| --- | --- | --- | --- |
| Unresolved required blockers are closed | W3-T02 Blocker Ledger, row `none-open` | pass | Explicitly records no unresolved required blocker at closure time. |
| Integrated validation bundle is fully green | Evidence Ledger row `Validation bundle` | pass | All six required commands are recorded with exit 0 outcomes. |
| Fresh smoke-lane confirmation rerun is green | Evidence Ledger row `Validation bundle` and row `Package parity` | pass | Fresh rerun recorded: `.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane` with smoke-src-lane 3 passed in 0.46s and smoke-fsrc-lane 3 passed in 0.05s (total 13.43s). |
| Campaign parity evidence remains objective-complete | W3-T01 Stage 1 and Stage 2 execution section + Evidence Ledger rows (`Facade parity`, `Package parity`, `Plugin/kernel/extension parity`, `Full parity harness`) | pass | Required role/repo/collection parity coverage and comparator-normalized checks remain pass. |

### Final Disposition

Like-for-like completion criteria are satisfied for this plan. Proceed with closure as complete.
