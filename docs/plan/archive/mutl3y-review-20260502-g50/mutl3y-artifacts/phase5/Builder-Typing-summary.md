agent name: Builder-Typing

owned file set:

- src/prism/scanner_plugins/defaults.py
- src/prism/tests/test_defaults.py

summary artifact path: docs/plan/mutl3y-review-20260502-g50/mutl3y-artifacts/phase5/Builder-Typing-summary.md

changed files:

- src/prism/scanner_plugins/defaults.py
- docs/plan/mutl3y-review-20260502-g50/mutl3y-artifacts/phase5/Builder-Typing-summary.md

concise status: Completed the owned typing repair in scope. `resolve_blocker_fact_builder` now normalizes `ScanMetadata` into a real `dict[str, Any]` before calling the canonical blocker-fact builder, which fixes the concrete adapter/callee contract mismatch without weakening the public protocol or adding casts. Narrow gate passed: `pytest -q src/prism/tests/test_defaults.py -k blocker` -> `1 passed`. Narrow style gate passed: `ruff check` + `black --check` on the owned files. Focused mypy on `src/prism/scanner_plugins/defaults.py` is clean with `--follow-imports=skip`; the plain single-file mypy invocation still surfaces an unrelated pre-existing error in `src/prism/scanner_core/metadata_merger.py`, outside the owned scope. Scope expansion needed: no.
