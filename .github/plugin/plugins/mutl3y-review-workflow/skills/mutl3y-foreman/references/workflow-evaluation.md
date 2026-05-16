# Workflow Evaluation

Use this when changing the workflow itself or when checking whether recent
workflow changes actually improved execution quality.

## Evaluate Outcomes, Not Just Footprint

`context-manager-evaluation.md` already checks control-plane size and routing
drills. This reference adds execution-quality checks.

## Core Dimensions

Score the workflow across these dimensions:

- `startup_load_budget`: how many files, lines, and words are required before
  the foreman can safely start a new cycle?
- `artifact_fidelity`: can the foreman continue from retained artifacts without
  re-reading broad history?
- `continuation_quality`: can work resume from a compact summary without losing
  the active phase, finding slice, or next action?
- `docs_loaded_to_continue`: how many reference files had to be read to make
  the next correct move from the current checkpoint?
- `missed_finding_delta`: how many net-new High or Critical findings still come
  from deep review or God Mode?
- `degradation_recovery`: when continuity weakens, does the workflow recover by
  artifact-backed restart rather than narration drift?
- `memory_hygiene`: do promoted lessons stay compact, current, and non-
  contradictory?

## Suggested Drills

Run these when changing workflow references or prompts:

1. resumed-cycle drill from a compact summary
2. degraded-context drill with repeated re-read pressure
3. stale-lesson drill where one prior rule should be superseded
4. independent-review delta drill against the latest God Mode pass
5. startup-load drill that counts files and words required before the first
  safe Phase 0 dispatch
6. continuation-load drill that counts how many docs were needed to make the
  next correct move from a barrier or resume checkpoint

## Reporting

Record pass or fail plus one short note per dimension. If a dimension fails,
identify the owning reference file before changing prompts broadly.

For the two load-oriented dimensions, always report the measured count, not
just a pass or fail label.
