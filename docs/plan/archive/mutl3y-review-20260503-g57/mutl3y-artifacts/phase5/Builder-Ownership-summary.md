Wave 1 retired the public `ensure_prepared_policy_bundle_fn` override seam from `prism.api_layer.non_collection.run_scan`.

Changed files:

- `src/prism/api_layer/non_collection.py`
- `src/prism/tests/test_api_cli_entrypoints.py`

Outcome:

- Removed the public `ensure_prepared_policy_bundle_fn` parameter from `run_scan`.
- Bound prepared-policy bundle assembly to `plugin_facade.ensure_prepared_policy_bundle` at execution-request ingress.
- Updated the nearest API entrypoint test to monkeypatch the canonical facade function instead of asserting public forwarding of an alternate resolver.

Focused validation:

- `2 passed, 28 deselected in 0.40s`
