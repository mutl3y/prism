Errors auto-fixed: 22 of 26

Examples of auto-fixed issues:
- formatting fixes (whitespace, blank lines)
- import ordering and simple unused-import removals

Remaining ruff errors (4) — not auto-fixable:
- src/prism/scanner_io/loader.py:157:17 — F821 Undefined name `_InputT`
- src/prism/scanner_io/loader.py:158:23 — F821 Undefined name `_InputT`
- src/prism/scanner_io/loader.py:158:33 — F821 Undefined name `_ResultT`
- src/prism/scanner_io/loader.py:159:11 — F821 Undefined name `_ResultT`

Reason these remain: undefined TypeVar identifiers (`_InputT`, `_ResultT`) used in annotations; requires manual TypeVar definitions or import adjustments.

Test gate result: PASS — 1306 passed, 7 skipped (18 warnings)
