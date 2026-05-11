# Phase Context Manager

Use the main skill as a context manager, not as one giant always-loaded instruction blob.

The goal is:

- keep the main skill short and top-loaded with non-negotiables
- keep detailed procedures in phase-specific references
- load only the references required for the current phase
- keep changing state in repo-backed artifacts, not in live chat context

## Design stance

This is a good idea.

The main skill should behave like an orchestrator and context manager:

- decide the current phase
- decide which references are mandatory for that phase
- decide which artifacts are the current source of truth
- decide which excerpts are small enough to keep live
- offload everything else to repo artifacts

## Default owner of context management

The foreman should do this itself by default.

Why:

- phase selection is the foreman's core job
- routing what to read next is a critical-path decision, not auxiliary clerical work
- inserting a helper agent adds another failure mode, another artifact handoff, and another chance to drift from repo truth
- the foreman already owns the barrier between stable rules and changing state

## When not to use a helper agent

Do not add a helper agent just to decide which references to read for a normal phase.

That would usually be over-engineering because:

- the decision is small
- the policy is stable
- the foreman can express it directly in the skill
- a helper becomes another component that itself needs guardrails and artifact checks

## When a helper agent may be justified

Use a helper only when one of these is true:

- the cycle needs a one-off synthesis across many reference files before work can start
- multiple phase policies conflict and need arbitration
- the repo has grown enough that selecting the right graph slices or artifact excerpts is itself a meaningful research task

If such a helper exists, it must stay advisory only.

It should never own:

- phase transitions
- barrier verdicts
- worker dispatch approval
- status-line emission
- plan-pointer truth

Those remain foreman responsibilities.

## Phase loading matrix

Read the phase manifest first. The manifest then names any narrower specialist references required for that phase.

## Minimal Live Load Rule

Default to the smallest instruction set that can safely continue the current
phase.

Keep live by default:

- the main skill
- this routing file
- the current phase manifest
- the current phase artifacts that prove state
- one short failure excerpt when fixing or recovering

Do not load by default just because the file exists:

- `references/foreman-execution-guardrails.md`
- `references/gate-commands.md`
- `references/deep-review-protocol.md`
- `references/model-routing-policy.md`
- phase-local prompt templates
- optional evaluation references

Load those only when the phase or event actually requires them.

## Canonical Owner Map

To reduce duplication, treat these files as the primary owner of each concern:

- phase routing and read decisions: this file
- startup and compact execution contract: `references/foreman-prompt.md`
- barrier enforcement and status-line control:
  `references/foreman-execution-guardrails.md`
- ledger promotion and durable learning rules:
  `references/self-improvement-protocol.md`
- minimal memory read path: `references/ledger-read-protocol.md`

Other files may reference these owners, but should not restate their full
procedures.

### Always-load set

Load these at the start of every cycle:

- `references/foreman-prompt.md`
- `references/team-topology.md`
- `references/context-efficiency.md`
- `references/ledger-read-protocol.md`
- `references/self-improvement-protocol.md`

Event-triggered global read:

- `references/foreman-execution-guardrails.md` before Phase 0 start,
  Phase 5 wave start, phase-transition narration, or any barrier verdict

Foreman checkpoint rule for real or interruption-prone runs:

- When the repository provides `scripts/record_execution_trace.py`, use it at
  each confirmed checkpoint boundary instead of freehand editing
  `mutl3y-artifacts/execution-trace.yaml`.
- Preferred pattern:
  `python3 scripts/record_execution_trace.py ... --validate-log docs/plan/<PLAN_ID>/.mutl3y-gate/trace-write.log`
- Minimum foreman-owned checkpoint boundaries are: after the Phase 0 batch join,
  after each Phase 5 wave barrier, after the Phase 6 gate verdict, and at Phase
  7 closeout.
- If the repository does not provide the helper, fall back to manual
  `execution-trace.yaml` updates plus the repo-local validator before leaving the
  barrier.

### Phase 0 discovery

Load additionally:

- `references/phase-0-discovery.md`
- `references/context-degradation-playbook.md` when resuming a long or
  interrupted cycle or when continuity is already weak
- `references/anchored-compaction.md` when a compact checkpoint summary
  needs to be created or refreshed

Use artifacts as live state:

- `plan.yaml`
- `findings.yaml` when continuing
- `mutl3y-artifacts/phase0/phase-start-audit.yaml`
- `mutl3y-artifacts/phase0/learning-context.yaml`

### Phase 1 grading

Load additionally:

- `references/phase-1-grading.md`

Use artifacts as live state:

- Phase 0 scout artifacts
- one compact grading artifact target

### Phase 2 persist plan

Load additionally:

- `references/phase-2-persist-plan.md`

Use artifacts as live state:

- compact grading artifact
- `findings.yaml`
- `plan.yaml`

### Phase 3 investigation

Load additionally:

- `references/phase-3-investigation.md`

### Phase 4 decide

Load additionally:

- `references/phase-4-decide.md`

### Phase 5 implementation

Load additionally:

- `references/phase-5-implementation.md`

Use artifacts as live state:

- `mutl3y-artifacts/phase5/wave-<N>-start-audit.yaml`
- `mutl3y-artifacts/phase5/wave-<N>-plan.yaml`
- `findings.yaml`

### Phase 6 validation

Load additionally:

- `references/phase-6-validation.md`
- `references/context-degradation-playbook.md` when repeated re-reading,
  summary contradiction, or route-quality drift appears during triage

Use artifacts as live state:

- `.mutl3y-gate/*`
- gate summary artifact
- model ledger and scorecard

### Phase 7 closure

Load additionally:

- `references/phase-7-close-and-learn.md`
- `references/closure-control-gate.md`
- `references/iteration-cadence.md`
- `references/deep-review-protocol.md`
- `references/foreman-execution-guardrails.md`
- `references/memory-hygiene.md`
- `references/workflow-evaluation.md` when workflow prompts,
  guardrails, or routing behavior changed during the cycle

Use artifacts as live state:

- closure evidence
- `mutl3y-artifacts/phase7/closure-control-gate.yaml`
- `mutl3y-artifacts/phase7/paused-resume.yaml` when pausing
- learning candidates
- scout coverage patches
- model ledger and scorecard

## Main-skill contract

The main skill should stay responsible for three things:

1. Top-loaded non-negotiables.
2. Phase-to-reference routing.
3. Enforcement triggers that say when a reference becomes mandatory.

The references should own the long procedural detail.

That gives you a context-friendly system without weakening enforcement.
