Skill structure note for g46

- Main Mutl3y skill was 513 lines before refactor; critical execution guardrails sat deep in the file, increasing lost-in-the-middle risk.
- Refactor outcome:
  - Main skill reduced to 399 lines.
  - Detailed foreman execution rules moved to ../agent_and_skills/.github/skills/mutl3y-review-loop/references/foreman-execution-guardrails.md.
  - Main skill now top-loads a short Critical Execution Guardrails section and mandates reading the reference before Phase 0 start, Phase 5 wave start, phase-transition messages, and barrier verdicts.
  - The same structure change was also recorded in foreman-compliance-audit-20260501.yaml so the main audit trail stays canonical.
- Conclusion: a reference-file pattern is valid, but only when the main skill explicitly marks it mandatory and repeats a short top-level summary of the non-negotiables.
