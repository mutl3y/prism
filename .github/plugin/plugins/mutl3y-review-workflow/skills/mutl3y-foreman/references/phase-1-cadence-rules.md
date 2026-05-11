# Phase 1 Cadence Rules

Use this during Phase 1 grading instead of loading the full
`iteration-cadence.md` file.

## What Matters In Phase 1

- A light review is only a checkpoint, never a terminating verdict.
- A clean thorough review is also only a checkpoint, not final sign-off.
- High-severity evidence must not be silently dropped during grading.
- High or Critical findings from exhaustive review artifacts must enter the
  shortlist before implementation begins.

## Mandatory Grading Rules

### Rule 1 — No silent drop of high-severity observations

Every `severity_hint: high` scout observation that Phase 1 does not promote
to a finding must be written to a `suppressed_highs` section in the grading
artifact with a one-line suppression rationale.

Valid rationale codes:

- `false_positive`
- `do_not_re_flag`
- `deferred`
- `duplicate_of`

If you cannot give one of those, promote the observation instead.

### Rule 2 — Exhaustive review findings feed the shortlist

Any finding rated High or Critical in an exhaustive review artifact, such as
Synthesizer, God Mode, or an independent grader, that is not already in
`findings.yaml` must be promoted into `findings.yaml` before implementation
begins.

If an exhaustive review artifact was produced by a prompt that violated the
independence contract in `deep-review-protocol.md` for an `independent`,
`fresh`, or `unconstrained` pass, do not treat that artifact as the
authoritative terminal verdict. Record it as calibration or corroborative
evidence, run the corrected independent pass, and promote High/Critical
findings from the corrected pass before implementation begins.

### Rule 3 — Phase 1 cross-cutting micro-check

On every thorough cycle, run these two local checks before finalizing the
shortlist:

- `registry_authority`: read all Phase 0 observations tagged
  `registry_authority`, `composition_root`, or `ownership` and check whether
  they describe a split-authority path.
- `facade_leakage`: read all Phase 0 observations tagged `facade_leakage`,
  `abstraction`, or `ownership` on public API or CLI modules and verify
  whether tests patch internal helpers through the public facade.

If either check yields a new finding, promote it before Phase 2.

### Rule 4 — Low-signal deep-review trigger

If fewer than one-third of raw scout observations are promoted during a
thorough cycle, trigger the deep review path instead of accepting the thin
signal at face value.

## Related References

- `grading-rubric.md` for grading thresholds and density expectations
- `deep-review-protocol.md` when the low-signal trigger fires
- `iteration-cadence.md` only when the whole-cycle cadence decision itself is
  under review
