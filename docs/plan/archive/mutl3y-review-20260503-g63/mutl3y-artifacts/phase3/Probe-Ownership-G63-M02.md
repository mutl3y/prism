# Probe-Ownership: G63-M02

## Question

What is the correct ownership boundary for the `task_line_parsing` proxy seam: keep fail-closed proxy exports in `scanner_extract`, move ownership to prepared policy/plugin objects, or split public convenience from runtime internals?

## Conclusion

The correct boundary is a split: runtime ownership should stay on prepared policy/plugin objects, while `scanner_extract.task_line_parsing` should be treated only as a public convenience or compatibility facade, not as a runtime authority surface.

## Why this boundary matches the live code

1. Runtime execution already resolves authority through prepared-policy objects.

   `require_prepared_policy()` in `src/prism/scanner_core/di_helpers.py:101` is the canonical fail-closed gate, and runtime callers already use it with explicit DI context rather than package globals. The local helper in `src/prism/scanner_extract/task_line_parsing.py:82` follows that model, and neighboring runtime code such as `scanner_extract.task_catalog_assembly` uses `require_prepared_policy(di, "task_line_parsing", ...)` directly instead of importing module globals.

2. The formal contract places ownership on prepared policy objects, not on `scanner_extract` exports.

   `PreparedTaskLineParsingPolicy` is defined as the runtime contract in `src/prism/scanner_data/contracts_request.py:163`, and `PreparedTaskAnnotationPolicy` is defined separately in `src/prism/scanner_data/contracts_request.py:211`. That is the architectural ownership signal: the bundle carries the policy object, and callers are expected to consume the object.

3. The current proxy module is a facade that mixes two domains and reintroduces implicit global reads.

   The module-level collection and regex proxies in `src/prism/scanner_extract/task_line_parsing.py:13`, `src/prism/scanner_extract/task_line_parsing.py:152`, and `src/prism/scanner_extract/task_line_parsing.py:197` call `require_prepared_policy(None, ...)` internally at access time (`src/prism/scanner_extract/task_line_parsing.py:19`, `src/prism/scanner_extract/task_line_parsing.py:51`). That means they preserve fail-closed behavior, but only by reopening an implicit DI-free lookup path.

4. The proxy surface reaches beyond the declared prepared-policy contracts.

   The task-line prepared-policy protocol exposes key collections plus `detect_task_module` (`src/prism/scanner_data/contracts_request.py:163`), but the proxy layer also reaches for `TEMPLATED_INCLUDE_RE` and `extract_constrained_when_values` (`src/prism/scanner_extract/task_line_parsing.py:112`, `src/prism/scanner_extract/task_line_parsing.py:116`). The same module also hosts annotation regex proxies that depend on `PreparedTaskAnnotationPolicy` members (`src/prism/scanner_data/contracts_request.py:217`, `src/prism/scanner_data/contracts_request.py:218`). That mismatch is a strong sign that the module is no longer the right ownership home for runtime behavior.

5. The ansible plugin layer is already the canonical implementation owner.

   `AnsibleDefaultTaskLineParsingPolicyPlugin` owns the default task-line constants and helpers in `src/prism/scanner_plugins/ansible/default_policies.py:63`, `src/prism/scanner_plugins/ansible/default_policies.py:67`, `src/prism/scanner_plugins/ansible/default_policies.py:73`, and `src/prism/scanner_plugins/ansible/default_policies.py:76`. The annotation defaults likewise live under `src/prism/scanner_plugins/ansible/default_policies.py:134`, `src/prism/scanner_plugins/ansible/default_policies.py:138`, and `src/prism/scanner_plugins/ansible/default_policies.py:148`. The ownership test in `src/prism/tests/test_extract_defaults_ansible_ownership.py:9` explicitly codifies that these default-policy classes belong under `scanner_plugins.ansible`.

6. Public export pressure still exists, so a hard move would break the current package contract.

   `scanner_extract.__init__` re-exports the proxy constants and regex objects (`src/prism/scanner_extract/__init__.py:6`, `src/prism/scanner_extract/__init__.py:12`, `src/prism/scanner_extract/__init__.py:63`), and `src/prism/tests/test_package_export_parity.py:170` enforces that package surface. That means removing the facade outright would break an explicitly tested public API.

## Ownership recommendation

- Keep prepared-policy objects as the only runtime authority.
- Keep `scanner_extract.task_line_parsing` only as a compatibility/public convenience layer.
- Do not let new runtime code depend on the module-level proxies.
- If the facade is retained, narrow it to explicit helper functions that accept `di` and delegate to the prepared bundle; avoid module-level `require_prepared_policy(None, ...)` proxies as the canonical path.

## Rejected alternatives

- Keep fail-closed proxy exports in `scanner_extract` as the owning seam.

  This conflicts with the prepared-policy contract and preserves an implicit DI-free lookup path at module scope.

- Move all ownership wholesale into prepared policy/plugin objects and remove the `scanner_extract` surface.

  This matches runtime design better, but it does not match the currently enforced public package export contract.

## Live verification

Focused pytest passed against the ownership-relevant slices:

```text
.venv/bin/python -m pytest -q \
  src/prism/tests/test_task_line_parsing.py \
  src/prism/tests/test_extract_defaults_ansible_ownership.py \
  src/prism/tests/test_package_export_parity.py

16 passed in 0.47s
```
