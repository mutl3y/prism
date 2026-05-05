# Probe-Tests: G63-M02

## Scope

- Question: Which direct tests lock in the current `task_line_parsing` proxy behavior, and would a local fix need same-wave test/API updates beyond the narrow suggested gate?
- Focus: tests only.

## Live validation

- Ran:
  - `.venv/bin/python -m pytest -q src/prism/tests/test_task_line_parsing.py src/prism/tests/test_task_parser_precedence_matrix.py src/prism/tests/test_comment_doc_plugin_resolution.py src/prism/tests/test_package_export_parity.py`
- Result: `79 passed, 14 warnings`.

## Direct tests that lock the current `task_line_parsing` proxy behavior

### 1. Dedicated proxy fail-closed contract tests

- `src/prism/tests/test_task_line_parsing.py:15` — `test_get_task_include_keys_raises_without_bundle`
- `src/prism/tests/test_task_line_parsing.py:45` — `test_get_templated_include_re_raises_without_bundle`
- `src/prism/tests/test_task_line_parsing.py:50` — `test_collection_proxy_iter_returns_empty_when_policy_unavailable`
- `src/prism/tests/test_task_line_parsing.py:65` — `test_marker_line_regex_proxy_raises_without_bundle`
- `src/prism/tests/test_task_line_parsing.py:70` — `test_annotation_regex_proxy_raises_without_bundle`

These are the most direct seam locks. They assert the module-level proxies and getter helpers fail closed through `require_prepared_policy(...)` when no prepared bundle is available.

### 2. Broader plugin-resolution tests that still directly assert the task-line proxy surface

- `src/prism/tests/test_comment_doc_plugin_resolution.py:543` — `test_task_line_parsing_policy_resolver_prefers_di_over_registry`
- `src/prism/tests/test_comment_doc_plugin_resolution.py:565` — `test_task_line_parsing_policy_resolver_uses_registry_before_fallback`
- `src/prism/tests/test_comment_doc_plugin_resolution.py:581` — `test_task_line_parsing_policy_resolver_uses_fallback_when_unavailable`
- `src/prism/tests/test_comment_doc_plugin_resolution.py:786` — `test_task_line_parsing_raises_without_prepared_policy`
- `src/prism/tests/test_comment_doc_plugin_resolution.py:795` — `test_task_line_parsing_prefers_prepared_policy_bundle`
- `src/prism/tests/test_comment_doc_plugin_resolution.py:813` — `test_task_line_parsing_constants_require_prepared_policy`
- `src/prism/tests/test_comment_doc_plugin_resolution.py:834` — `test_task_line_parsing_templated_include_regex_requires_prepared_policy`

These extend the lock beyond the narrow gate. They preserve three current contracts:

- resolver precedence is `DI -> registry -> fallback`
- extractor helpers prefer `prepared_policy_bundle`
- module-level constant/regex proxies still exist and fail closed without DI context

### 3. One directly adjacent consumer test

- `src/prism/tests/test_comment_doc_plugin_resolution.py:959` — `test_task_catalog_assembly_uses_dynamic_task_include_keys`

This is not about the proxy object itself, but it proves downstream scanner behavior still consumes the policy-derived `TASK_INCLUDE_KEYS` dynamically. A fix that changes how task-line policy is resolved may need this test updated if consumer wiring changes, even if the core proxy unit tests are rewritten.

## Tests reviewed that are adjacent but not direct locks for G63-M02

- `src/prism/tests/test_task_parser_precedence_matrix.py:127` — `test_task_parser_annotation_policy_precedence_di_over_registry`
- `src/prism/tests/test_task_parser_precedence_matrix.py:173` — `test_task_parser_annotation_policy_precedence_registry_over_fallback`
- `src/prism/tests/test_task_parser_precedence_matrix.py:223` — `test_task_parser_annotation_policy_precedence_fallback_when_no_di_or_registry`

These are useful control evidence for shared policy-resolution patterns, but they target `task_annotation_parsing`, not `task_line_parsing`. A local G63-M02 fix should not require same-wave updates here unless it intentionally changes the shared resolver contract across extract-policy domains.

## API-surface test that matters if the fix changes exports

- `src/prism/tests/test_package_export_parity.py:170` — `test_fsrc_required_scanner_package_exports_match_contract`
- Export contract includes `TASK_INCLUDE_KEYS`, `ROLE_INCLUDE_KEYS`, `INCLUDE_VARS_KEYS`, `SET_FACT_KEYS`, `TASK_BLOCK_KEYS`, `TASK_META_KEYS`, and `ROLE_NOTES_RE` at `src/prism/tests/test_package_export_parity.py:65-71`.

This means a purely local fix that preserves the exported names should not need API-contract updates. A fix that removes or renames the public proxy exports will need same-wave updates here, and that would no longer be a narrow behavioral-only change.

## Conclusion

A local fix does need validation beyond the suggested narrow gate because the current proxy behavior is directly locked by `test_task_line_parsing.py` and the task-line slices in `test_comment_doc_plugin_resolution.py`; however, same-wave test or API updates are only required if the fix changes the public proxy contract itself (module-level exported proxies/getters or resolver precedence), not if it preserves that surface and only rewires the internal resolution path.

## Open edges

- The dedicated narrow gate in `findings.yaml` omits the most direct proxy lock file, `src/prism/tests/test_task_line_parsing.py`, so using the suggested gate alone would under-sample the seam.
- `test_comment_doc_plugin_resolution.py:581` still locks the fallback branch as live behavior; if G63-M02 intends to retire fallback rather than merely localize it, that is a same-wave behavior-contract change, not just an internal fix.
- `test_package_export_parity.py` makes public-export removal or renaming non-local by design.
