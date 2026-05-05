# Builder-Ownership Summary

- Finding: `G46-H03`
- Scope: `src/prism/scanner_plugins/ansible/default_policies.py`, `src/prism/tests/test_variable_discovery_pipeline.py`, `src/prism/tests/test_gilfoyle_blockers_runtime.py`
- Change: `AnsibleDefaultVariableExtractorPolicyPlugin.collect_include_vars_files()` now accepts only resolved include files that remain under the resolved role root, preventing `include_vars` traversal via `..` segments or absolute paths outside the role while preserving normalized in-role relative paths.
- Tests: added a direct policy regression covering safe in-role `../vars/...` includes plus rejected relative and absolute escapes, and an end-to-end runtime regression asserting the outside files are not surfaced in `display_variables`.
- Validation: `pytest -q src/prism/tests/test_variable_discovery_pipeline.py src/prism/tests/test_gilfoyle_blockers_runtime.py`
