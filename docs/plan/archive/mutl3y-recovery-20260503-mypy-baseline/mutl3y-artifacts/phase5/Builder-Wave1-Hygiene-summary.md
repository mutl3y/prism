**Builder Wave-1 Hygiene — Minimal Fixes**

- **Agent:** Builder-Wave1-Hygiene
- **Owned files changed:**
  - src/prism/tests/test_g03_scan_cache_integration.py (removed unused import)
  - src/prism/api.py (black reformat)
  - src/prism/tests/test_api_cli_repo_parity.py (black reformat)
  - src/prism/tests/test_plugin_name_resolver.py (black reformat)
  - src/prism/tests/test_api_cli_entrypoints.py (black reformat)

- **Actions performed:**
  - Removed an unused import (`Callable`) to satisfy `ruff`.
  - Ran `black` to reformat four files to project style.
  - Re-ran `ruff` and `black --check` to validate hygiene.

- **Validation results:**
  - `ruff check` on affected files: All checks passed.
  - `black --check` on reformatted files: Passed (files are now formatted).

- **Behavior:** No functional changes made; only formatting and one unused-import removal.
- **Timestamp:** 2026-05-03
