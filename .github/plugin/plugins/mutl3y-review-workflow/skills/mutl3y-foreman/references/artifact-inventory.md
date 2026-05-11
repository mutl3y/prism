# Artifact Inventory

Use this when you need the minimum repo-backed artifact set for a phase or
barrier.

Missing required artifacts are a `STALL`, not a bookkeeping detail.

## Minimal Artifact Inventory

- Before Phase 0 narration or scout dispatch:
  - `mutl3y-artifacts/phase0/phase-start-audit.yaml`
- Before leaving Phase 0:
  - `mutl3y-artifacts/phase0/learning-context.yaml`
  - four scout artifacts
- Before leaving any phase that used subagents:
  - `mutl3y-artifacts/model-usage-ledger.yaml`
  - `mutl3y-artifacts/model-scorecard.yaml`
  - `.mutl3y-gate/ledger-validate.log`
- Before leaving any real or interruption-prone checkpoint boundary:
  - `mutl3y-artifacts/execution-trace.yaml`
- Before leaving Phase 1:
  - one compact grading artifact
- Before leaving Phase 2:
  - `findings.yaml`
  - `plan.yaml` with synced `resumption_pointer`
- Before Phase 5 wave narration or builder dispatch:
  - `mutl3y-artifacts/phase5/wave-<N>-start-audit.yaml`
- Before leaving each Phase 5 wave barrier:
  - one wave plan artifact
  - one summary artifact per dispatched builder
- Before leaving Phase 6:
  - repo-local gate logs under `.mutl3y-gate/` and/or a repo-local gate
    summary artifact
- Before leaving Phase 7:
  - any required scout-coverage patch, gate-escape learning artifact, and
    learning compiler outputs when the cycle reached those triggers

If the cycle state implies one of these artifacts should exist and it does not,
emit `STALL`, recover the missing evidence, and only then continue.
