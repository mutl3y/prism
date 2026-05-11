# Multiprocess Execution

This skill should use true batch launch behavior when the harness/runtime supports concurrent agents or separate terminal processes.

## Rule

For disjoint work, launch all workers first, then wait at one barrier.

Bad:

1. launch `Scout-Typing`
2. wait
3. launch `Scout-Ownership`
4. wait

Good:

1. launch `Scout-Typing`, `Scout-Ownership`, `Scout-ControlFlow`, `Scout-Graph`
2. continue lightweight foreman work if possible
3. wait once for the batch
4. merge artifacts

## Where To Use Multiprocess

- Phase 0 discovery scouts
- Phase 5 builders with disjoint file sets
- Phase 6 gate steps
- optional Phase 3 micro-swarm investigators

## Where Not To Use It

- foreman grading and decisions
- overlapping writer scopes
- tiny blocking tasks where process spin-up costs more than it saves
- bookkeeping unless closure work is unusually large

## Batch Barrier Model

Use explicit barriers between:

- graph refresh -> Phase 0 launch
- Phase 0 launch -> Phase 0 merge
- Phase 5 launch -> wave integration check
- Phase 6 launch -> final gate verdict

Within a barrier, do not serialize independent workers.

If `architecture-graph.json` is stale, rebuild it once before the Phase 0 scout batch.
Do not let each scout regenerate its own view independently.

## Process Hygiene

- one artifact path per worker
- one owned file set per writing worker
- one log file per validation process where practical
- stable agent names so process outputs are human-readable

Suggested artifact naming:

```text
docs/plan/<plan-id>/mutl3y-artifacts/phase0/Scout-Typing.yaml
docs/plan/<plan-id>/mutl3y-artifacts/phase5/Builder-Typing-summary.md
.mutl3y-gate/Gatekeeper-pytest.log
.mutl3y-gate/Gatekeeper-ruff.log
```

## Foreman Behavior

The foreman should:

- precompute disjoint scopes
- launch full batches
- avoid idle waiting when there is local merge/setup work available
- join once per batch
- re-slice only on conflict or failure
