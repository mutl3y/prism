# Phase 7 Ledger Updater Prompt

Use this only when Phase 7 is large enough to justify delegation.
Default Phase 7 bookkeeping stays local.

```text
Role: <AGENT_NAME>, named ledger maintainer.

Inputs:
  - findings.yaml for this cycle
  - docs/plan/<PLAN_ID>/mutl3y-artifacts/model-usage-ledger.yaml
  - docs/plan/<PLAN_ID>/mutl3y-artifacts/model-scorecard.yaml
  - phase artifacts containing learning candidates
  - cycle metadata (gN, focus axis, gate result, duration)
  - docs/plan/.mutl3y-lessons/digest.yaml
  - docs/plan/.mutl3y-lessons/model-usage-rollup.yaml

Tasks:
  1. Verify missed-finding feedback and gate-escape learning artifacts exist
    when the cycle evidence requires them.
  2. Resolve `<SKILL_ROOT>` to the actual directory that contains this skill.
    Use `.github/skills/mutl3y-review-workflow` when the skill is vendored into
    the repo; otherwise use the shared-workspace skill path.
  3. Run:
    ```text
    python3 <SKILL_ROOT>/scripts/update_learning_memory.py compile \
     --repo-root . \
     --plan-dir docs/plan/<PLAN_ID> \
     --plan-id <PLAN_ID> \
     --cycle <gN> \
     --focus-axis <axis> \
     --gate-result <GREEN|ACCEPTED>
    ```
  4. Record each ledger row through
    `python3 <SKILL_ROOT>/scripts/record_model_usage.py ...`
    `--validate-log .mutl3y-gate/ledger-validate.log`.
    Do not freehand-write ledger rows.
  5. If the repository provides `scripts/record_execution_trace.py`, record the
    confirmed Phase 7 checkpoint through
    `python3 scripts/record_execution_trace.py ...`
    `--validate-log docs/plan/<PLAN_ID>/.mutl3y-gate/trace-write.log`
    after ledger validation passes.
  6. Do not freehand-write the trace in delegated bookkeeping runs.
  7. If validation fails, stop and report `STALL`; do not continue Phase 7
    bookkeeping with malformed YAML.
  8. Use spaces only in YAML output. Tabs are forbidden.
  9. Refresh import-graph.json if source mtimes require it.
  10. Refresh architecture-graph.json if source mtimes or deep-review triggers
    require it.
  11. Reconcile `findings.yaml` with all landed fixes since the last barrier or
    probe; close fixed findings and attach fresh `closed_evidence` before
    reporting cycle completion.
  12. Verify digest.yaml includes active lesson IDs, do-not-re-flag summaries,
    next focus axis, and route-health notes without copying full raw ledgers.
  13. After learning compilation, write or refresh a retained Phase 7 closure
    summary that compresses wave-level artifacts and records safe cleanup
    candidates for transient or duplicate artifacts.
  14. If the repository provides a completed-plan cleanup helper, run it after
    the closure summary update so pure wave scaffolding is pruned from
    completed plans before reporting cycle completion.
  15. If the repository provides a plan-archive helper, archive completed
    workflow-run plan directories out of the active `docs/plan` root once
    closure evidence is retained and no active resume pointer still depends
    on that directory remaining top-level.

Output:
  - agent name
  - compiler summary
  - ledger files touched
  - ledger validation log path
  - trace helper log path, if used
  - findings reconciled
  - any duplicate-lesson warnings
  - promoted learning candidate count
  - closure summary path
  - stale lesson or route-health entries removed from digest
  - artifact cleanup actions or candidates
  - cleanup helper result, if used
  - archive helper result, if used
```
