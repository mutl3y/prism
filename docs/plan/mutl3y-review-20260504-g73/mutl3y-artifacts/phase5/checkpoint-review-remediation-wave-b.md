# Checkpoint Review Remediation Wave B

- Scope: same-scan registry drift, nested scan-options mutation isolation, and fail-fast config-path validation on the public API path.
- Outcome: all three confirmed High-severity checkpoint-review defects are now closed with focused regressions.

## Closed Highs

- Same-scan registry drift: runtime orchestration now honors the plugin factory frozen into `RoutePreflightRuntimeCarrier`, so registry mutation after preflight cannot swap the plugin implementation used for the same scan.
- Nested scan-options mutation leak: the non-collection API boundary now clones nested container nodes before plugin execution, so plugin mutation of nested `policy_context` data does not leak back to the caller.
- Missing config-path no-op acceptance: `readme_config_path` and `policy_config_path` now fail fast when the caller passes a missing path instead of being accepted and silently ignored.

## Focused Validation

- `.venv/bin/python -m pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'nested_policy_context_mutation_is_isolated or rejects_missing_config_paths'`
- `.venv/bin/python -m pytest -q src/prism/tests/test_plugin_kernel_extension_parity.py -k 'registry mutation does not affect same scan' src/prism/tests/test_api_cli_entrypoints.py -k 'nested_policy_context_mutation_is_isolated or rejects_missing_config_paths'`

## Regrade Notes

- A Jinja-related checkpoint-review candidate was not promoted in this slice because no concrete reachability or same-scan runtime failure was confirmed from the local read/validation path.
