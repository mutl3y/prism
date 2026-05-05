# Builder-MypyScanOptionFixtures

Updated the three owned test files to use canonical `ScanOptionsDict` fixtures instead of partial `{}` payloads, and removed the unsupported `feature_detection_plugin` key from the event-system test by keeping the mock injection on `DIContainer`.

## Changed Files

- `src/prism/tests/test_t4_03_cli_progress.py`
- `src/prism/tests/test_t3_05_scan_telemetry.py`
- `src/prism/tests/test_t3_01_scan_phase_events.py`

## Validation

- Focused mypy command: still fails, but only on pre-existing errors outside the owned set in `src/prism/scanner_core/task_extract_adapters.py`, `src/prism/scanner_core/execution_request_builder.py`, and `src/prism/scanner_kernel/orchestrator.py`.
- Focused pytest bundle: `26 passed` for the three owned test files.
