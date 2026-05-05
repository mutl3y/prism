# Builder-ControlFlow Summary

- Findings: `G46-H01`, `G46-H02`
- Scope: `src/prism/repo_services.py`, `src/prism/tests/test_api_cli_repo_parity.py`, `src/prism/tests/test_t3_06_path_safety.py`
- Change: `resolve_repo_scan_target()` now treats `repo_role_path` and `repo_style_readme_path` as repository-relative inputs, rejects absolute paths, and rejects any resolved target that escapes the resolved `repo_root`.
- Change: `clone_repo()` now inserts `--` before `repo_url` so leading-dash user input cannot be parsed as a `git clone` option.
- Tests: added focused regressions for leading-dash `repo_url`, `../` traversal in `repo_role_path`, and absolute-path `repo_style_readme_path` rejection.
- Validation: `pytest -q src/prism/tests/test_api_cli_repo_parity.py src/prism/tests/test_t3_06_path_safety.py` => `38 passed`
