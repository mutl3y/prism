Context-manager experiment note for g46

- Baseline live skill: ../agent_and_skills/.github/skills/mutl3y-review-loop/
- Experimental clone: ../agent_and_skills/.github/skills/mutl3y-review-loop-context-manager/

Opinion:

- This is a good idea.
- The main skill should increasingly act as a context manager and orchestrator.
- The foreman should own context selection by default.
- A helper agent should be advisory-only and used only for exceptional synthesis or ambiguous cross-reference arbitration, not for ordinary phase routing.

Why this pattern is good:

- It matches how the workflow already works: stable rules in skill/reference files, changing state in repo-backed artifacts.
- It reduces lost-in-the-middle risk by moving long procedural detail out of the main skill while keeping top-loaded non-negotiables in the main skill.
- It is context-friendly because phase-specific references can be loaded only when needed.

Important constraint:

- Moving rules out of the main skill only works when the main skill still makes the references mandatory at concrete trigger points.
- The main skill must retain top-loaded non-negotiables, enforcement triggers, and phase-to-reference routing.

Current state of the experiment:

- The experimental clone is now explicitly named as a context-manager variant and routes phase-specific loading through phase-context-manager.md.
- The line-count delta is still small, so this is currently a scaffold for comparison rather than a fully minimized orchestrator-only main skill.
- If a stronger comparison is desired, the next step is to extract one or two more long procedural sections from the clone only and keep the live skill unchanged.

Working recommendation:

- Keep the live skill stable.
- Use the cloned context-manager variant for further extraction experiments.
- Compare them on three things: barrier compliance, missing-artifact detection, and whether the foreman actually loads fewer irrelevant references per phase.
