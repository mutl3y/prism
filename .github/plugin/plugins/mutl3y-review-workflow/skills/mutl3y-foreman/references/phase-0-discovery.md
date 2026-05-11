# Phase 0 Discovery

Purpose:

- Produce the initial discovery artifact set for the cycle.
- Establish the current focus axis and the first artifact-backed view of repo state.

Source of truth:

- `plan.yaml` when resuming
- `findings.yaml` when continuing an existing cycle
- `mutl3y-artifacts/phase0/phase-start-audit.yaml`

Load now:

- `iteration-cadence.md`
- `context-degradation-playbook.md`
- `scout-scan-patterns.md`
- `parallel-execution.md`
- `multiprocess-execution.md`
- `phase-0-sweep-prompt.md`
- `phase-start-audit-template.yaml`

Use companion entrypoint:

- `../../agents/mutl3y-scout.agent.md`

Rules:

- Discovery is always subagent-first.
- Refresh the shared architecture graph before dispatch when source mtimes
  or plan metadata require it.
- Launch `Scout-Typing`, `Scout-Ownership`, `Scout-ControlFlow`, and
  `Scout-Graph` in one multiprocess batch.
- Each scout reads only the minimal category reference set, the cached
  graph slice it needs, and the current digest inputs.
- Each scout writes raw observations to disk and returns only a compact
  summary in this format:
  - `<lane>_findings_written: N (critical: N, high: N, medium: N, low: N)`
  - `top_findings: <id>, <id>, <id>`
- If the first scout batch surfaces a clear focus area or any
  High/Medium candidate, run a bounded widening pass in the same cycle
  before grading.
- If continuing a long or interruption-prone cycle, refresh an anchored
  compaction summary before scout dispatch when the prior compact state no
  longer reflects the latest retained artifacts.
- If resuming or continuing a cycle and there are tracked, modified Python
  files in the working tree (dirty tracked `.py` files), do not dispatch
  scouts or start Phase 0 work until the `resume-dirty-tree` gate has run
  and its outcome is recorded in the Phase 0 start-audit artifact. See
  [gate-commands.md](./gate-commands.md) for the repo gate snippet and
  required commands.
- Extend `learning-context.yaml` with compact context-health notes when
  degradation triggers fired before or during discovery.

Barrier:

- Verify all expected scout artifacts exist on disk.
- Write `mutl3y-artifacts/phase0/learning-context.yaml` before leaving Phase 0.
- For real or interruption-prone runs, write or update
  `mutl3y-artifacts/execution-trace.yaml` with the confirmed P0
  checkpoint before leaving the barrier. Use a repo-local trace writer
  with validation logging when the repository provides one.
- Emit the phase-transition status line only after the barrier checks pass.

Outcomes:

- `P0 complete -> P1`
- `repeat P0`
- `STALL`
- `BLOCKED`
