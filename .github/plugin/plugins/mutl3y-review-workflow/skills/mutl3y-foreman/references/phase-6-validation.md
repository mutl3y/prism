# Phase 6 Validation

Purpose:

- Run the validation team and produce one aggregate gate verdict.
- Keep full-gate evidence on disk and only surface the failure slice
  needed for the next fix.

Source of truth:

- Builder summary artifacts from the current wave
- `.mutl3y-gate/` logs and summaries
- `mutl3y-artifacts/model-usage-ledger.yaml` and `model-scorecard.yaml`

Load now:

- `parallel-gate.md`
- `gate-commands.md`
- `parallel-execution.md`
- `context-degradation-playbook.md`

Use companion entrypoint:

- `../../agents/mutl3y-gatekeeper.agent.md`

Rules:

- `Gatekeeper` is mandatory for full or path-filtered gate execution.
- `Auditor-Regression` is mandatory when touched files include
  `scanner_core`, `api_layer`, DI helpers/factories, or plugin boundary
  paths.
- Keep logs in `.mutl3y-gate/` and surface only the lines needed for the next fix.
- Run independent gate steps concurrently when the environment allows it.
- If the narrow gate passed but the full gate fails, record a
  gate-escape learning candidate before leaving the phase.
- After any later repair lands, an older full-gate log becomes stale as a live
  remaining-failure queue until a new retained gate or retained focused status
  batch is written.
- If an aggregate-gate failure does not reproduce in the cheapest isolated or
  minimally-neighbored check, classify it as possible suite noise and do not
  promote it directly into a fix wave without one more discriminating repro.
- If the same failure slice must be re-read twice, or compact failure
  summaries are contradicted twice by retained logs, record a degradation
  event and restart triage from the smallest artifact-backed slice.
- For real or interruption-prone runs, write or update
  `mutl3y-artifacts/execution-trace.yaml` immediately after the gate
  verdict, including `failure_debug` when the outcome is not `OK`.
  Use a repo-local trace writer with validation logging when the
  repository provides one.

Outcomes:

- `P6 complete -> P7`
- `return to P5 for repair`
- `STALL`
- `BLOCKED`
