# Phase 1 Grading

Purpose:

- Grade discovery findings into a compact, decision-ready artifact.
- Convert raw discovery output into the shortlist that drives plan persistence.

Source of truth:

- Phase 0 scout artifacts
- `mutl3y-artifacts/phase0/learning-context.yaml`
- `findings.yaml` when continuing a cycle

Load now:

- `phase-1-cadence-rules.md`
- `review-checklist.md`
- `grading-rubric.md`
- `phase-1-grader-prompt.md` when using an independent grader

Rules:

- Default to foreman-local grading from artifact-backed scout output.
- Always write one compact grading artifact before leaving Phase 1.
- Use an independent grader only when a second opinion is needed,
  the merge is still too large, or a zero-Critical/High result needs
  extra skepticism.
- If a light review reports zero Critical or High and a later thorough
  review reports any Critical or High, record a `light_false_negative`
  entry in the phase artifact and proceed from the thorough findings only.
- Every merged finding must cite a stable in-repo artifact path.
- Findings sourced only from transient inline output are invalid until persisted.

Outcomes:

- `P1 complete -> P2`
- `repeat P1`
- `STALL`
- `BLOCKED`
