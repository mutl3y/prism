# Workflow Improvement Plan 2026-05-03

Purpose:

- turn the context-engineering review into a bounded documentation patch
- improve the live Mutl3y workflow without bloating the always-loaded control plane
- keep new guidance phase-local wherever possible

## Scope

This patch integrates five concrete upgrades into the workflow:

1. workflow outcome evaluation beyond footprint-only checks
2. memory hygiene rules for stale, superseded, and conflicting lessons
3. context degradation detection and recovery rules
4. anchored compaction rules for long or interrupted cycles
5. Phase 7 closure-control gating for cadence, God Mode, continuation,
   commit, and pause decisions

## Planned File Changes

Add new references:

- `references/workflow-evaluation.md`
- `references/memory-hygiene.md`
- `references/context-degradation-playbook.md`
- `references/anchored-compaction.md`
- `references/closure-control-gate.md`

Update existing workflow entrypoints:

- `SKILL.md`
- `references/phase-context-manager.md`
- `references/phase-0-discovery.md`
- `references/phase-6-validation.md`
- `references/phase-7-close-and-learn.md`
- `references/foreman-prompt.md`
- `references/foreman-execution-guardrails.md`
- `references/parallel-execution.md`
- `.github/agents/mutl3y-teams-foreman.agent.md`

## Integration Strategy

### 1. Keep the main skill small

- add only routing and enforcement hooks to `SKILL.md`
- put procedural detail in new reference files
- avoid adding new always-load material unless it is a cross-phase guardrail

### 2. Attach each upgrade to the phase that owns it

- Phase 0 owns early context-health detection and resumed-cycle compaction
- Phase 6 owns degradation-event handling during repair and gate triage
- Phase 7 owns lesson hygiene, consolidation, and workflow evaluation
- Phase 7 owns the closure-control gate before any cycle-close, pause,
  or `task_complete` claim

### 3. Reuse existing artifacts when practical

- extend `learning-context.yaml` with compact context-health fields
  instead of creating a parallel state file
- store degradation or compaction notes in existing phase artifacts
  and execution trace when the event matters for resume or recovery
- keep persistent lesson state under `docs/plan/.mutl3y-lessons/`

### 4. Make fan-out limits explicit

- keep artifact-based handoffs
- document a default worker batch cap so the foreman does not become the bottleneck

## Acceptance Criteria

- the main skill remains orchestration-first and does not absorb long new handbooks
- each new concern has a named reference file and a clear owning phase
- resumed long cycles have a documented anchored compaction path
- lesson maintenance includes stale and superseded handling
- barrier rules include degradation recovery instead of assuming
  artifact-first flow is always sufficient
- workflow evaluation covers continuation quality, artifact fidelity,
  and missed-finding delta instead of control-plane size alone
- Phase 7 cannot be closed by local foreman judgment, generic reviewers,
  or biased God Mode prompts when the closure-control gate is required

## Validation

- verify markdown files load without editor diagnostics
- verify updated files reference only existing workflow paths
- verify the new rules remain consistent with the current Mutl3y
  agent names and artifact paths

## Validation Result 2026-05-03

- `references/closure-control-gate.md` added and linked from the main skill,
  foreman agent, Phase 7 manifest, phase router, foreman prompt,
  deep-review protocol, and execution guardrails.
- Existing-path check passed for the new closure-control gate and all Phase 7
  references it requires.
- Focused formatting check passed for the new gate and this plan file. Historic
  long-line markdown debt remains in older workflow references and was not
  expanded in this closure-control patch.
- Workflow-evaluation result: `artifact_fidelity`, `continuation_quality`,
  `degradation_recovery`, and `memory_hygiene` improved by making the Phase 7
  close/pause/continue decision a single required artifact instead of a
  foreman-local synthesis step.
