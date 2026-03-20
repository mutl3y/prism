# Work Schedule 2026 — Consolidated Roadmap

Updated: 2026-03-20

## Objective
Deliver known-limitation reductions and external-review improvements in a practical 6-week schedule, with scanner stability first and compatibility testing after stabilization.

## Tracks

### Track A: Scanner Stability

Week 1-2:
- Expand variable-source coverage and provenance confidence labels.
- Improve unresolved/non-literal handling for static scan output.

Week 2-3:
- Expand Jinja2 AST handling for harder expressions and fallback paths.
- Add focused fixtures for nested/default-filter edge behavior.

Week 3-4:
- Expand task/role parsing for include/import role directives and dependency tracing.
- Harden detailed task catalog traversal for include/import variants.

Week 4-5:
- Cover edge cases: dynamic includes, precedence interactions, dependency-provided values.
- Add realistic integration fixtures to reduce regressions.

### Track B: User Experience

Week 1-2 (parallel):
- Publish guidance for Prism-friendly roles and confidence interpretation.
- Clarify static-analysis scope boundaries and explicit non-goals.

Week 3-4 (parallel):
- Improve error reporting quality and actionability.
- Surface parse/problem context in scanner report output.

Week 5:
- Add multi-version Ansible compatibility checks in CI after Track A stabilization.

Week 5-6:
- Polish docs and template customization guidance.

### Track C: Validation and Coverage

Week 5-6:
- Full test and integration validation across tracks.
- Keep coverage >= 80 and target high-risk branch closure in scanner/Jinja paths.
- Validate compatibility matrix and concise scanner-report quality.

## Dependency Rules

1. Start Track B1 immediately in parallel with A1.
2. Do not merge Ansible matrix expansion until A1-A3 is stable.
3. Treat Track C as release gating for both A and B.

## Milestones

1. End of Week 2:
- A1 complete and stable.
- B1 docs merged.

2. End of Week 4:
- A2/A3 complete.
- B2 error-reporting improvements validated.

3. End of Week 5:
- A4 complete.
- B3 CI matrix active.
- C1 coverage audit complete.

4. End of Week 6:
- C2 integration pass complete.
- Release candidate ready.

## Current Progress Snapshot

Completed this session:
- Detailed catalog now normalizes and renders include/import role calls consistently.
- Dict-form include_tasks recursion in task catalog traversal is covered.
- Actionable YAML parse failures are now captured and rendered in concise scanner reports.
- Full suite passing: 369 tests.
- Latest tox coverage: 84.64% total.

## Immediate Next Actions

1. Extend AST/Jinja coverage in `src/prism/_jinja_analyzer.py` for remaining low-coverage branches.
2. Add targeted scanner edge-case tests in `src/prism/scanner.py` branch-heavy paths.
3. Add/expand CI compatibility matrix for supported ansible-core versions.
