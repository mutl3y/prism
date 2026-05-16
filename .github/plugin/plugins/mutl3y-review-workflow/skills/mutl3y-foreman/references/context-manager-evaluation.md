# Context Manager Evaluation

Use this when comparing the Mutl3y review workflow against the baseline skill or when validating a structural refactor.

## Baseline Snapshot

- Pre-refactor main skill footprint: `409` lines, `3474` words.
- Baseline file: `.github/skills/mutl3y-review-workflow/SKILL.md`

## Current Snapshot

- Post-refactor main skill footprint: `175` lines, `1394` words.
- Always-loaded control-plane reduction: `234` lines (`57.2%`) and `2080` words (`59.9%`).
- Detailed phase headings remaining in the main skill: `0`.
- Operational output contract: `docs/plan/<plan-id>/mutl3y-artifacts/` for durable cycle output and `.mutl3y-gate/` for transient validation output.

## Primary Questions

1. Did the always-loaded control plane get smaller?
2. Did cross-phase guardrails remain globally available?
3. Can the foreman execute one phase by loading only the main skill, always-read globals, the active phase manifest, and the specialist references that manifest names?
4. Did stall, barrier, cancellation, and learning behavior remain at least as strong as before?

## Measurement Commands

Main control-plane footprint:

```bash
wc -l -w .github/skills/mutl3y-review-workflow/SKILL.md
```

Phase-manifest footprint:

```bash
wc -l -w .github/skills/mutl3y-review-workflow/references/phase-*.md
```

Specialist phase policy footprint:

```bash
wc -l -w .github/skills/mutl3y-review-workflow/references/phase-5-builder-policy.md
```

## Context Savings Metrics

Track these values after each structural change:

- `main_skill_lines`
- `main_skill_words`
- `phase_manifest_count`
- `phase_local_lines_moved_out_of_main`
- `percent_reduction_always_loaded_lines`
- `percent_reduction_always_loaded_words`

Use this formula for the primary savings number:

- `phase_local_lines_moved_out_of_main = baseline_main_skill_lines - current_main_skill_lines`
- `percent_reduction_always_loaded_lines = phase_local_lines_moved_out_of_main / baseline_main_skill_lines`

Words are a better proxy than lines when comparing refactors that change formatting.

## Operational Drills

Run these drills when validating the refactor:

1. Phase-resolution drill: resume from an existing `plan.yaml` and verify the foreman loads only the correct phase manifest.
2. Missing-artifact drill: remove or simulate a missing expected artifact and confirm the foreman emits `STALL` instead of progress narration.
3. Cancellation drill: simulate a cancelled subagent and verify file evidence inspection, route-failure logging, and re-dispatch behavior.
4. Wave-barrier drill: confirm builder artifacts, narrow gate, and anti-pattern grep gate all run before Phase 6.
5. Resume drill: restart from a Phase 5 or Phase 6 artifact set and confirm the router selects the right next phase without rereading unrelated phase procedures.
6. Learning-continuity drill: confirm model ledger, scorecard, and durable lesson promotion still work after the split.
7. Output-contract drill: confirm the workflow entrypoint, phase manifests, and gate references all use `mutl3y-artifacts/` and `.mutl3y-gate/` while the learning store is `.mutl3y-lessons`.
8. Execution-trace drill: interrupt after a confirmed barrier, then verify `execution-trace.yaml` and `plan.yaml` point to the same restart checkpoint.
9. Failure-debug drill: force a stall or cancellation and verify the trace captures the failure slice needed to debug the stop without reading full logs first.

## Acceptance Criteria

- The main skill shrinks materially while preserving all cross-phase guardrails.
- Each phase has exactly one manifest reference.
- The main skill contains no bulky phase-specific handbooks.
- Each phase manifest declares purpose, source-of-truth artifacts, required references, and valid outcomes.
- Cross-phase rules live globally; phase-local rules live in phase manifests or specialist references.
- No required learning or self-improvement behavior disappears as part of the split.
- Mutl3y operational outputs are consistently routed to `mutl3y-artifacts/` and `.mutl3y-gate/` with the learning store under `.mutl3y-lessons`.

## Reporting

When comparing variants, report:

- baseline vs current line and word counts
- percent reduction in always-loaded footprint
- which rules stayed global
- which rules moved phase-local
- whether the output-contract drill passed
- whether the execution-trace drill passed
- whether the failure-debug drill passed
- any regression found in the operational drills
