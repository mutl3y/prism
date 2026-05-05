# Error Boundary Audit (T3-04)

## Trust model

Public API entry points (`prism.api.run_scan`, `scan_role`, `scan_collection`,
`scan_repo`) and CLI commands are the only callers expected to translate raw
exceptions into structured `PrismRuntimeError` instances with stable codes.
Internal modules (`scanner_core`, `scanner_io`, `scanner_extract`,
`scanner_readme`, `scanner_reporting`) historically raise `ValueError`, `RuntimeError`,
`TypeError`, or `KeyError` for invariant violations.

T3-04 establishes a **regression-blocking baseline** rather than a one-shot
rewrite. The baseline records every existing raw raise; new raises that
appear in audited modules without being added to the baseline cause CI to
fail.

## How it works

1. `scripts/audit_error_boundaries.py` scans the audited modules for
   `raise (ValueError|RuntimeError|TypeError|KeyError)(`.
2. The set of `(file, kind)` pairs is stored in
   `docs/dev_docs/error-boundary-audit-baseline.json`.
3. `--check` mode compares the current scan against the baseline and exits
   non-zero when new raw raises appear.
4. `--update` rewrites the baseline (use only after wrapping a raise in
   `PrismRuntimeError` or after consciously introducing a new one).

## Test integration

`src/prism/tests/test_t3_04_error_boundary_audit.py` invokes the audit
script in `--check` mode. CI fails fast when developers introduce new raw
raises without adjusting the baseline.

## Recommended workflow when adding new module-boundary errors

1. Prefer raising `PrismRuntimeError` from `prism.errors` with a stable code.
2. If a raw exception is unavoidable (internal invariant guard), wrap it at
   the module boundary or update the baseline with an explanatory commit
   message.
3. Future cleanup tasks should peel raises off the baseline as they are
   converted, shrinking the allowlist over time.
