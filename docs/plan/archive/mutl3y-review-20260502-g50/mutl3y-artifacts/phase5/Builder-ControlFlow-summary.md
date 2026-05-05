agent name: Builder-ControlFlow

owned file set:

- src/prism/api_layer/non_collection.py
- src/prism/tests/test_api_cli_entrypoints.py

summary artifact path: docs/plan/mutl3y-review-20260502-g50/mutl3y-artifacts/phase5/Builder-ControlFlow-summary.md

changed files:

- src/prism/api_layer/non_collection.py
- src/prism/tests/test_api_cli_entrypoints.py

concise status: Completed G50-H02 inside owned scope. Replaced local `Any` and weak run-scan callback/payload typing with explicit local contracts, added a typed local payload normalizer for the non-collection seam, and added a direct regression covering explicit `ensure_prepared_policy_bundle_fn` forwarding. Narrow gate passed: `pytest -q src/prism/tests/test_api_cli_entrypoints.py` (29 passed). Scope expansion needed: no.
