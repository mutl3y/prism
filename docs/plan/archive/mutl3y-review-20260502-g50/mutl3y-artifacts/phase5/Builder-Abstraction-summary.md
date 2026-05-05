agent name: Builder-Abstraction
owned file set:

- src/prism/scanner_io/output_orchestrator.py
- src/prism/tests/test_output_orchestration.py

summary artifact path: docs/plan/mutl3y-review-20260502-g50/mutl3y-artifacts/phase5/Builder-Abstraction-summary.md
changed files:

- src/prism/scanner_io/output_orchestrator.py
- src/prism/tests/test_output_orchestration.py

concise status: Completed G50-H03 inside owned scope. Replaced the `OutputOrchestrator` facade `options` annotation with a concrete `OutputOrchestratorOptions` `TypedDict` matching the existing validation-layer field contract, and added a regression test that asserts the constructor keeps using that concrete type. Narrow gate: `pytest -q src/prism/tests/test_output_orchestration.py -k orchestrator` -> `2 passed, 3 deselected`. Scope expansion needed: no.
