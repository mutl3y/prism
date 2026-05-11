# Outstanding Review List (11 May 2026)

## Gate Status

- `pytest -q`: PASS (`1369 passed, 7 skipped, 18 warnings`)
- `ruff check src/prism`: PASS
- `black --check src/prism`: PASS (after formatting 8 files)
- `tox -e typecheck`: FAIL (`42 errors in 9 files`)

## Typecheck Blockers (Must Resolve Before "all gates green" commit)

1. `src/prism/scanner_data/error_envelope_protocol.py` (1 error)
2. `src/prism/scanner_plugins/marker_prefix_policy.py` (1 error)
3. `src/prism/scanner_extract/task_line_parsing.py` (5 errors)
4. `src/prism/scanner_extract/task_annotation_parsing.py` (1 error)
5. `src/prism/scanner_extract/task_file_traversal.py` (8 errors)
6. `src/prism/scanner_extract/task_catalog_assembly.py` (2 errors)
7. `src/prism/scanner_plugins/ansible/feature_detection.py` (11 errors)
8. `src/prism/scanner_core/service_locator.py` (1 error)
9. `src/prism/scanner_core/plugin_resolver.py` (12 errors)

## Dirty Tree Snapshot

- `docs/plan/*`: 156 entries (largest non-code bucket)
- `src/prism/*`: 65 entries (source/tests commit candidate)
- `.github/agents/*`: 12 entries
- `demos/output/*`: 16 entries
- `mutl3y-artifacts/*`: multiple buckets

## Focused Commit Scope Candidate (Source + Tests)

- Include only:
  - `src/prism/**`
  - `conftest.py`
  - `setup.cfg`
  - `tests/**` (if intended)
- Exclude from this commit:
  - `docs/**`
  - `.github/**`
  - `demos/**`
  - `mutl3y-artifacts/**`
  - other infra/config churn

## Why Commit Is Not Created Yet

- Request condition was "if it all works".
- Local CI bundle is not fully green due to `typecheck` failures.
- Creating a focused commit now would either:
  - violate the all-green gate expectation, or
  - require a partial commit with unresolved type debt.

## Suggested Next Move

1. Fix the 42 mypy errors in the 9 listed files.
2. Re-run full local gate bundle.
3. Create one focused source/tests commit once all gates are green.
