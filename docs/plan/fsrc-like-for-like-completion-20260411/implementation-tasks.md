# FSRC Like-for-Like Completion Implementation Tasks

## Plan ID

- fsrc-like-for-like-completion-20260411

## Goal

- Keep the same completion objective while making execution safer and closure-auditable.
- Optimize for constrained safe parallelism in early waves.

## Execution Status

| Task ID | Status | Updated On | Evidence |
| --- | --- | --- | --- |
| W1-T01 | completed | 2026-04-11 | artifacts/api-symbol-parity-contract.md; artifacts/cli-command-option-exit-parity-contract.md; artifacts/package-export-parity-contract.md |
| W1-T02 | completed | 2026-04-11 | artifacts/e2e-fixture-catalog.md; artifacts/gilfoyle-e2e-parity-campaign.md |
| W1-T03 | completed | 2026-04-11 | artifacts/plugin-kernel-extension-parity-scope-contract.md |
| W1-T04 | completed | 2026-04-11 | artifacts/deferred-feedback-boundary-contract.md |
| W1-T05 | completed | 2026-04-11 | artifacts/ci-equivalent-validation-map.md |
| W1-T06 | completed | 2026-04-11 | artifacts/gilfoyle-e2e-parity-campaign.md#phase-0-checkpoint-decision-record-2026-04-11 |
| W2-T01 | completed | 2026-04-11 | artifacts/api-symbol-parity-contract.md; artifacts/cli-command-option-exit-parity-contract.md; focused parity command #1 passed |
| W2-T02 | completed | 2026-04-11 | artifacts/package-export-parity-contract.md (PKG-02..PKG-05 pass); fsrc/src/prism/tests/test_fsrc_package_export_parity.py; src/prism/tests/test_package_import_smoke.py; fsrc/src/prism/tests/test_fsrc_package_import_smoke.py; guardrail suites |
| W2-T03 | completed | 2026-04-11 | artifacts/plugin-kernel-extension-parity-scope-contract.md (W2-T03 implementation closure) |
| W2-T04 | completed | 2026-04-11 | artifacts/gilfoyle-e2e-parity-campaign.md (W2-T04 acceptance closure matrix + normalized diff summaries + raw pointers); docs/plan/prism-next-fsrc-build-20260408/artifacts/wave6_closure_evidence.yaml |
| W3-T01 | completed | 2026-04-11 | Stage 1 focused bundle and Stage 2 integrated bundle passed on retry; blocker W3-T01-B01 resolved with reruns green (`pytest -q`, parity pytest bundle, `tox -r -e smoke-src-lane,smoke-fsrc-lane`, `ruff check src/prism fsrc/src`, `black --check src/prism fsrc/src`, `tox -e typecheck`). Follow-on blocker W3-T01-B02 resolved for fsrc-like-for-like parity gaps: scanner_extract compatibility exports now match src behavior/signatures and fsrc CLI top-level help/unknown-first-arg semantics now match src (`pytest -q fsrc/src/prism/tests/test_fsrc_scanner_extract_shim_parity.py --confcutdir=fsrc/src/prism/tests`, `pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_repo_parity.py -k "top_level_help or unknown_first_arg" --confcutdir=fsrc/src/prism/tests`, `ruff check` and `black --check` on changed files). Follow-on blocker W3-T01-B03 resolved for stale fsrc API/CLI entrypoint tests under canonical CLI dispatch contract: role-path invocations are now explicit and role dispatch patch target now matches runtime (`api.scan_role`) with reruns green (`pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py --confcutdir=fsrc/src/prism/tests`, parity pytest bundle, `ruff check src/prism fsrc/src`, `black --check src/prism fsrc/src`, `tox -e typecheck`). |

## Task Board

| Task ID | Wave | Priority | Status | Task | Depends On | Acceptance Criteria | Primary Artifacts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W1-T01 | Wave 1 | High | Completed | Freeze API/CLI/package parity contracts | None | Contract matrices for API symbols, CLI options/exit semantics, and scanner_* exports are complete and approved | plan.yaml contracts section, parity contract tables |
| W1-T02 | Wave 1 | High | Completed | Build deterministic fixture catalog for full parity campaign | None | Role/repo/collection fixtures and expected outputs are documented and stable | artifacts/e2e-fixture-catalog.md, artifacts/gilfoyle-e2e-parity-campaign.md |
| W1-T03 | Wave 1 | Medium | Completed | Freeze plugin/kernel/extension parity scope contract | None | Objective-critical ownership and interface parity requirements are explicit | plan.yaml, artifacts/plugin-kernel-extension-parity-scope-contract.md |
| W1-T04 | Wave 1 | Medium | Completed | Record deferred-feedback boundary and re-entry trigger contract | None | Defer policy, trigger, and checkpoint are documented for closure governance | plan.yaml, campaign artifact decision section |
| W1-T05 | Wave 1 | Medium | Completed | Freeze CI-equivalent validation map for parity closure | None | Focused and full validation command bundles are fixed for all streams | artifacts/ci-equivalent-validation-map.md; artifacts/gilfoyle-e2e-parity-campaign.md |
| W1-T06 | Phase 0 | High | Completed | Execute pre-Wave-2 decision checkpoint | W1-T01, W1-T02, W1-T03, W1-T04, W1-T05 | Unresolved required blockers = 0, open questions = 0, contract signoff complete | artifacts/gilfoyle-e2e-parity-campaign.md checkpoint decision record |
| W2-T01 | Wave 2 | High | Completed | Implement facade parity stream (API/CLI including collection) | W1-T01, W1-T02, W1-T06 | fsrc API/CLI behaviors match source contracts for required flows | fsrc/src/prism/api.py, fsrc/src/prism/cli.py, parity tests |
| W2-T02 | Wave 2 | High | Completed | Implement package surface parity stream for scanner_* families | W1-T01, W1-T06 | Required scanner_* export/module surfaces are aligned with source contracts | fsrc/src/prism/scanner_*/__init__.py, import smoke tests, package export parity contract |
| W2-T03 | Wave 2 | High | Completed | Implement plugin/kernel/extension objective-critical parity stream | W1-T03, W1-T06 | Objective-critical plugin/kernel/extension seams are parity-complete and test-backed | fsrc/src/prism/scanner_plugins, scanner_kernel, scanner_extensions |
| W2-T04 | Wave 2 | Medium | Completed | Expand full parity harness and cross-lane snapshots | W1-T02, W1-T05, W1-T06 | Full role/repo/collection parity matrix replaces representative-only checks | artifacts/gilfoyle-e2e-parity-campaign.md; src/prism/tests/test_fsrc_scanner_parity.py; fsrc/src/prism/tests |
| W3-T01 | Wave 3 | High | Completed | Execute Gilfoyle E2E parity campaign and collect integrated evidence | W2-T01, W2-T02, W2-T03, W2-T04 | Campaign evidence demonstrates objective-complete parity with no unresolved required deltas | artifacts/gilfoyle-e2e-parity-campaign.md#W3-T01-stage-1-and-stage-2-execution-2026-04-11 |
| W3-T02 | Wave 3 | Medium | Completed | Produce closure evidence and risk disposition bundle | W3-T01 | Closure package includes residual risks and deferred-scope compliance | artifacts/gilfoyle-e2e-parity-campaign.md#w3-t02-closure-evidence-and-risk-disposition-bundle-2026-04-11 |
| W3-T03 | Wave 3 | Medium | Completed | Final go or no-go recommendation for like-for-like completion | W3-T01, W3-T02 | Recommendation includes explicit decision and blocker statement | artifacts/gilfoyle-e2e-parity-campaign.md#w3-t03-final-recommendation-go-no-open-blockers-2026-04-11 |

## Task Status Updates

| Task ID | Status | Updated | Evidence |
| --- | --- | --- | --- |
| W1-T01 | completed | 2026-04-11 | artifacts/api-symbol-parity-contract.md; artifacts/cli-command-option-exit-parity-contract.md; artifacts/package-export-parity-contract.md |
| W1-T02 | completed | 2026-04-11 | artifacts/e2e-fixture-catalog.md |
| W1-T03 | completed | 2026-04-11 | artifacts/plugin-kernel-extension-parity-scope-contract.md |
| W1-T04 | completed | 2026-04-11 | artifacts/deferred-feedback-boundary-contract.md |
| W1-T05 | completed | 2026-04-11 | artifacts/ci-equivalent-validation-map.md |
| W1-T06 | completed | 2026-04-11 | checkpoint gates passed; artifacts/gilfoyle-e2e-parity-campaign.md checkpoint decision record |
| W2-T01 | completed | 2026-04-11 | blocked rows API-02/API-03/API-06 and CLI-03/CLI-08/CLI-09 moved to pass; focused parity tests passed |
| W2-T02 | completed | 2026-04-11 | required scanner_* export parity rows PKG-02..PKG-05 moved to pass; focused package parity/import smoke/guardrail suites passed |
| W2-T03 | completed | 2026-04-11 | fsrc extension semver caret lower-bound parity fixed; focused parity + ownership guardrail suites passed |
| W2-T04 | completed | 2026-04-11 | acceptance criteria met via campaign matrix completion rows; normalized diff summaries and raw evidence pointers recorded for role/repo/collection positive+negative scenarios |
| W3-T01 | completed | 2026-04-11 | Stage 1 and Stage 2 completed with all integrated gates green; blocker W3-T01-B01 resolved and reruns pass for `pytest -q`, parity pytest (`src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests`), `tox -r -e smoke-src-lane,smoke-fsrc-lane`, `ruff check src/prism fsrc/src`, `black --check src/prism fsrc/src`, and `tox -e typecheck`. Follow-on blocker W3-T01-B02 resolved: scanner_extract compatibility shim behavior/signature parity restored and CLI top-level parser semantics aligned to src; focused regression and lint/format commands are recorded in the execution status row. Follow-on blocker W3-T01-B03 resolved: stale fsrc API/CLI entrypoint tests were aligned to canonical role dispatch contract (`role` subcommand + `api.scan_role` patch target) and validation reruns are green (`pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py --confcutdir=fsrc/src/prism/tests`, `pytest -q src/prism/tests/test_fsrc_scanner_parity.py fsrc/src/prism/tests --confcutdir=src/prism/tests`, `ruff check src/prism fsrc/src`, `black --check src/prism fsrc/src`, `tox -e typecheck`). SCM closure-audit blocker resolved: `fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py` is now staged in git (`git add`), and focused confirmation rerun remains green (`pytest -q fsrc/src/prism/tests/test_fsrc_api_cli_entrypoints.py --confcutdir=fsrc/src/prism/tests`, 6 passed). Fresh closure smoke rerun passed (`.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane`: smoke-src-lane 3 passed in 0.46s; smoke-fsrc-lane 3 passed in 0.05s; total 13.43s). |
| W3-T02 | completed | 2026-04-11 | Closure bundle completed in campaign artifact with evidence summary, complete blocker ledger, residual-risk table with owner+mitigation, and explicit deferred-scope compliance statement; no unresolved required blockers omitted. |
| W3-T03 | completed | 2026-04-11 | Final recommendation recorded as Decision: Go and Blockers: none open, with explicit traceability to evidence ledger rows for integrated validation bundle (all required commands pass) and fresh closure smoke rerun (`.venv/bin/python -m tox -r -e smoke-src-lane,smoke-fsrc-lane`: smoke-src-lane 3 passed in 0.46s; smoke-fsrc-lane 3 passed in 0.05s; total 13.43s). |

## Wave 2 Delegation Start (2026-04-11)

- Delegated W2-T01 to gem-implementer and authorized immediate start (lane A).
- Delegated W2-T02 to gem-implementer with queued start, serialized behind W2-T01.
- Delegated W2-T03 to gem-implementer and authorized immediate start (lane C).
- Delegated W2-T04 to gem-reviewer and authorized immediate start (lane D).
- Enforced plan constraint: W2-T01 and W2-T02 remain serialized due to shared facade/package import boundary.

## Phase 0 Checkpoint Rules

- Wave 2 cannot start until W1-T06 is marked complete.
- W1-T06 completion requires:
  - unresolved required blockers count = 0
  - unresolved open questions count = 0
  - API/CLI/package/plugin contracts signed off
- If any checkpoint criterion fails, reopen the owning Wave 1 task and keep status as blocked.

## Parallelism Design

- Wave 1 has five preparatory tasks that run in parallel and one checkpoint task (W1-T06) that gates implementation start.
- Wave 2 uses constrained parallelism:
  - W2-T01 and W2-T02 are serialized due to shared facade/package import boundary.
  - W2-T03 and W2-T04 can run in parallel with either W2-T01 or W2-T02.
- Wave 3 converges into integrated campaign execution, closure evidence, and final recommendation.

## Ownership Boundaries

- W2-T01 owns facade behavior parity in fsrc API/CLI files.
- W2-T02 owns scanner_* package surface/export parity.
- W2-T03 owns plugin/kernel/extension objective-critical seams.
- W2-T04 owns parity harness and evidence normalization outputs.
- Cross-boundary edits require owner acknowledgement in task notes before merge.

## Delivery Rules

- No Wave 2 stream starts before required Wave 1 contracts are frozen and Phase 0 checkpoint passes.
- Any required parity gap discovered in Wave 3 reopens the owning Wave 2 stream using triage protocol below.
- Closure requires integrated evidence, not isolated stream-level green checks.

## Reopened Parity Gap Triage Protocol

1. Record gap ID, failing command or test, impacted contract row, and lane owner.
1. Classify severity as critical (required contract), medium (non-required parity drift), or low (diagnostic mismatch only).
1. Reopen owning task (W2-T01, W2-T02, W2-T03, or W2-T04) and set W3-T01 to blocked when severity is critical.
1. Freeze merges for the impacted ownership boundary and activate rollback protocol from plan.yaml immediately if guardrails fail.
1. Run focused rerun for failing lane first, then run dependent cross-lane checks when comparator output indicates shared-surface impact.
1. Mark re-entry only when reopened gap status is resolved, required contract row status is pass, and evidence ledger is updated with before/after outcomes and owner signoff.
1. Resume W3-T01 only after all critical reopened gaps are resolved; if two consecutive reopen events occur on the same contract row, escalate to W1-T06 checkpoint reassessment.
