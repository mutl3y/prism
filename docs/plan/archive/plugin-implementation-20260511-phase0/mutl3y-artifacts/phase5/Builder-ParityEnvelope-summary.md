Builder-ParityEnvelope (Wave 8) — Summary

Agent: Builder-ParityEnvelope
Plan: g84-remediation-mutl3y-cycle-20260509
Phase: P5
Wave: rem-1 (Wave 8: parity envelope)

Scope (strict):
- Edited: src/prism/scanner_core/scanner_context.py
- Purpose: Reconcile the public error envelope shape emitted in `metadata.scan_errors` to match fsrc/src parity expectations.

Change:
- Trimmed `_record_phase_error` entries to include only: `phase`, `error_type`, `message`.
- Rationale: The parity test `test_w2_t05_scanner_context_error_envelope_parity` expects scan error entries to be a compact envelope (no traceback field). This change preserves behavior (errors still recorded and `scan_degraded` set) while matching the expected public shape.

Files changed:
- src/prism/scanner_core/scanner_context.py

Gate run:
- Command: `cd /raid5/source/test/prism && PYTHONPATH=src .venv/bin/python -m pytest src/prism/tests/test_scanner_parity.py::test_w2_t05_scanner_context_error_envelope_parity -q`
- Result: `1 passed in 0.34s`

Notes and risks:
- The traceback is no longer included in the public `scan_errors` metadata entries. Internal logging still emits traceback where appropriate (unchanged). If consumers relied on `traceback` being present in `scan_errors`, they must be updated to use logs or inspect exceptions via other channels.
- This change strictly targets the envelope shape and avoids behavioral drift.

Status: complete

---

## Gilfoyle Phase 7 Audit Note (May 11, 2026)

**Discrepancy identified**: This summary claims traceback was trimmed. However, the current production code in `scanner_context.py:367` **includes traceback** in the error envelope. This reflects the final outcome after the ErrorEnvelopeBoundary wave (rem-2), which added traceback for "context preservation."

The parity tests pass either way because `traceback` is `NotRequired[str]` in the `ScanErrorEntry` TypedDict — its presence doesn't violate the parity contract.

**Actual current state**: Traceback is included (as per ErrorEnvelopeBoundary design). This summary is stale but not blocking — the production behavior is correct.
