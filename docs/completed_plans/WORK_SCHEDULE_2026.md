# Work Schedule 2026 — Consolidated Roadmap

Updated: 2026-03-20

Status key: [x] complete, [~] in progress, [ ] planned

Overall status: Completed

## Objective

Deliver known-limitation reductions and external-review improvements in a practical 6-week schedule, with scanner stability first and compatibility testing after stabilization.

## Tracks

### Track A: Scanner Stability

Week 1-2:

- [x] Expand variable-source coverage and provenance confidence labels.
- [x] Improve unresolved/non-literal handling for static scan output.

Week 2-3:

- [x] Expand Jinja2 AST handling for harder expressions and fallback paths.
- [x] Add focused fixtures for nested/default-filter edge behavior.

Week 3-4:

- [x] Expand task/role parsing for include/import role directives and dependency tracing.
- [x] Harden detailed task catalog traversal for include/import variants.

Week 4-5:

- [x] Cover edge cases: dynamic includes, precedence interactions, dependency-provided values.
- [x] Add realistic integration fixtures to reduce regressions.

### Track B: User Experience

Week 1-2 (parallel):

- [x] Publish guidance for Prism-friendly roles and confidence interpretation.
- [x] Clarify static-analysis scope boundaries and explicit non-goals.

Week 3-4 (parallel):

- [x] Improve error reporting quality and actionability.
- [x] Surface parse/problem context in scanner report output.

Week 5:

- [x] Add multi-version Ansible compatibility checks in CI after Track A stabilization.

Week 5-6:

- [x] Polish docs and template customization guidance.

### Track C: Validation and Coverage

Week 5-6:

- [x] Full test and integration validation across tracks.
- [x] Keep coverage >= 80 and target high-risk branch closure in scanner/Jinja paths.
- [x] Validate compatibility matrix and concise scanner-report quality.

## Dependency Rules

1. Start Track B1 immediately in parallel with A1.
2. Do not merge Ansible matrix expansion until A1-A3 is stable.
3. Treat Track C as release gating for both A and B.

## Milestones

1. End of Week 2:

- A1 complete and stable.
- [x] B1 docs merged.

1. End of Week 4:

- A2/A3 complete.
- B2 error-reporting improvements validated.

1. End of Week 5:

- A4 complete.
- B3 CI matrix active.
- C1 coverage audit complete.

1. End of Week 6:

- C2 integration pass complete.
- Release candidate ready.

## Current Progress Snapshot

Completed this session:

- Detailed catalog now normalizes and renders include/import role calls consistently.
- Dict-form include_tasks recursion in task catalog traversal is covered.
- Actionable YAML parse failures are captured and rendered in both scanner sidecar reports and main task-summary output.
- Added parser/Jinja edge-case coverage fixtures for include-role normalization, dynamic include handling, and AST fallback branches.
- CI includes ansible-core compatibility matrix (`2.17.x`, `2.18.x`, `2.19.x`).
- Added `docs/PRISM_FRIENDLY_ROLE_GUIDE.md` for role authoring and confidence-oriented guidance.
- Added `docs/STATIC_ANALYSIS_SCOPE_AND_NONGOALS.md` for explicit scope boundaries and non-goals.
- Added focused `feedback.py` tests and raised module coverage to 97.6%.
- Added focused `collection_plugins.py` helper tests and raised module coverage to 92.5%.
- Added focused `api.py` helper/runbook-path tests and raised module coverage to 87.5%.
- Added additional `scanner.py` helper/path branch tests and refreshed Jinja fallback-path tests.
- Full suite passing: 502 tests.
- Latest tox coverage: 91.66% total.

## Closeout

1. Planned roadmap tracks are complete for this cycle.
2. Remaining work should be tracked in a new schedule file for the next cycle.
