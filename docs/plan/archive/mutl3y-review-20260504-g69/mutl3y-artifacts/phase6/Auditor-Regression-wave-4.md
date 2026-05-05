# Auditor — Regression (Mutl3y Phase 6, Wave 4)

Plan: mutl3y-review-20260504-g69
Cycle: g69
Phase: P6
Wave: 4
Auditor: GitHub Copilot
Date: 2026-05-04

Scope
- Read-only regression audit focused on two target seams: `G69-H02` (public plugin protocol typing seam) and `G69-H03` (ansible kernel lifecycle protocol seam). Review limited to code touched by g69 waves 3–4 and immediate, nearby contracts.

Verdict (concise)
- Overall: minor regression risk remains, limited and local to typing coverage and integration assertions. No high-severity protocol breaks observed in the touched slices.

Top findings

1) G69-H02 — Public plugin protocol typing seam (Primary)
 - Observation: Several public-facing protocol members and prepared-policy surfaces in the touched slices retain weak typing (members typed as `Any` or accepting raw `dict`/variadic payloads). The g69 work replaced variadic/raw-dict request flow with canonical runtime contracts, but a residue of un-narrowed types remains on plugin Protocol return members and on `PreparedPolicyBundle`-shaped members.
 - Risk: Medium. Static checks that passed the focused touched-file mypy run reduce immediate risk, but the repo lacks a targeted enforcement test that verifies plugin protocol member shapes for public plugin interfaces. A future change could reintroduce raw-dict shapes that only fail at runtime in downstream consumers.
 - Evidence / pointers: touched canonicalization work in wave 4; residual `Any`-typed fields observed in prepared-policy and plugin protocol files referenced by the slice (typing artifacts and Protocols in scanner_core / scanner_plugins). Focused mypy was exercised but not a strict gate across the full public plugin surface.

2) G69-H03 — Ansible kernel lifecycle protocol seam (Secondary)
 - Observation: Wave 4 protocolized the ansible kernel lifecycle and codified the lifecycle transitions. Integration unit tests covering the normal lifecycle passed in the focused bundle; however, there is limited regression coverage for lifecycle error/retry transitions and for thin compatibility wrappers that still exist as short-lived seams.
 - Risk: Low-to-Medium. The principal runtime lifecycle contract was implemented and validated, but a missing small matrix of negative/integration assertions (failure path, partial shutdown, and handler-order enforcement) could allow regressions in rare error scenarios.
 - Evidence / pointers: wave-4 barrier summary indicates lifecycle protocolization; test artifact set is focused but lacks small negative-path matrix for lifecycle failures.

Conclusion
- No material, high-severity regression risk detected in the wave-4 touched slices. The remaining risks are measurable and narrow: (1) ensure a targeted mypy/enforcement test for public plugin protocol member shapes to close G69-H02, and (2) add a compact negative-path lifecycle test matrix to reduce the low remaining risk for G69-H03.

Appendix: actionable minimal checks (for reference only)
- Add one focused mypy/test that asserts a small set of plugin Protocol members are not `Any` (enforce via `reveal_type` or explicit type assertions in a test module targeting public plugin interfaces).
- Add 2–3 integration tests that exercise lifecycle error/shutdown/retry transitions for the ansible kernel path.
