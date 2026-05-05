# Probe-Imports: G63-M02

## Question

Does the `task_line_parsing` proxy seam require only local changes in `scanner_extract`, or do imports/runtime consumers create a broader scope-expansion requirement?

## Conclusion

The seam is not purely local to `scanner_extract`: canonical runtime ownership already sits outside this module in the prepared-policy bundle resolver and DI/plugin path, while the live broader surface is the `prism.scanner_extract` public import facade plus import-contract tests, not additional production call sites directly consuming the proxy constants.

## Evidence

- `src/prism/scanner_extract/task_line_parsing.py` defines proxy objects that call `require_prepared_policy(...)` at use time, including `TASK_INCLUDE_KEYS`, `ROLE_NOTES_RE`, and `TEMPLATED_INCLUDE_RE`.
- `src/prism/scanner_extract/__init__.py` re-exports those proxy symbols, so any import of `prism.scanner_extract` also imports the task-line parsing shim module.
- The import graph slice records `prism.scanner_extract.task_line_parsing` with one live importer: `src/prism/scanner_extract/__init__.py`; it records `prism.scanner_extract` as imported by `src/prism/api.py` and `src/prism/tests/test_task_line_parsing.py`.
- `src/prism/api.py` imports `prism.scanner_extract` in public helpers, which means the shim remains on a public package-import path even though the helpers shown there do not read the proxy constants directly.
- Canonical runtime policy assembly is owned outside `scanner_extract`: `src/prism/scanner_plugins/bundle_resolver.py` ensures `prepared_policy_bundle["task_line_parsing"]`, and `src/prism/scanner_core/di.py` exposes `factory_task_line_parsing_policy_plugin()` for DI wiring.
- `src/prism/scanner_extract/task_catalog_assembly.py` already reads task-line behavior directly from `require_prepared_policy(di, "task_line_parsing", ...)` instead of importing the proxy constants, which limits production blast radius on the extract side.
- `src/prism/scanner_plugins/ansible/extract_policies.py` and `src/prism/scanner_plugins/ansible/default_policies.py` consume Ansible-owned task-line modules and constants, not `scanner_extract.task_line_parsing`, so canonical plugin/runtime consumers are already decoupled from this shim.

## Affected Neighbors

- `src/prism/scanner_extract/task_line_parsing.py`: shim under review.
- `src/prism/scanner_extract/__init__.py`: public re-export surface; any change to exported names or import behavior widens here immediately.
- `src/prism/api.py`: public facade that imports `prism.scanner_extract`, so package-level compatibility matters.
- `src/prism/scanner_plugins/bundle_resolver.py`: canonical runtime owner of task-line policy population.
- `src/prism/scanner_core/di.py`: DI seam for task-line parsing policy plugin resolution.
- `src/prism/scanner_extract/task_catalog_assembly.py`: nearby extract consumer already using prepared policy directly.
- `src/prism/tests/test_task_line_parsing.py`: explicit fail-closed contract for shim proxies.
- `src/prism/tests/test_scanner_extract_shim_parity.py` and `src/prism/tests/test_comment_doc_plugin_resolution.py`: import-contract/runtime tests that exercise `importlib.import_module("prism.scanner_extract.task_line_parsing")` and proxy behavior.

## Scope Assessment

Local-only repair is plausible only if it preserves both of these external contracts:

- `prism.scanner_extract` must remain import-compatible for public/package consumers.
- shim tests must keep their current fail-closed semantics for direct module import and proxy access.

If the intended fix changes exported names, removes the shim module, or reroutes package imports away from `scanner_extract.__init__`, scope expands beyond `scanner_extract` into the public facade/tests. If the fix only rewrites internal proxy implementation while preserving module exports and fail-closed behavior, the production runtime surface stays largely local because canonical execution already resolves task-line policy through bundle resolver + DI instead of these proxies.

## Runtime Check

Focused validation run:

```text
.venv/bin/python -m pytest -q src/prism/tests/test_task_line_parsing.py src/prism/tests/test_scanner_extract_shim_parity.py src/prism/tests/test_comment_doc_plugin_resolution.py -k 'task_line_parsing or scanner_extract_shim_parity'
22 passed, 55 deselected, 2 warnings in 0.90s
```

The warnings were existing stateless-plugin warnings from the task-line parsing registry tests, not failures in the shim import contract.

## Bottom Line

Imports do create a real but narrow scope-expansion requirement: not extra production runtime consumers of the proxy constants, but the `scanner_extract` package facade, `api.py` package import path, and the existing shim/import tests must be preserved or updated together.
