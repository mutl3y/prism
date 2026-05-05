# Builder-DIEvents Summary

Plan: `mutl3y-review-20260503-g58`
Wave: `P5/W2`
Findings: `G58-H01`, `G58-H02`
Status: narrow gate green; importer-layer follow-up green.

Changes:

- Hardened `DIContainer.replace_scan_options()` in `src/prism/scanner_core/di.py` to coordinate scan-option snapshot replacement under the container lock and invalidate only the cached DI-owned runtime participants that were built from the previous snapshot.
- Switched the container state lock to `RLock` so snapshot reads and cache invalidation share one coherent ownership boundary.
- Made inheritance of process-global default listeners explicit via `inherit_default_event_listeners=False` by default on `DIContainer`; ambient global listeners no longer flow into unrelated container lifetimes unless a caller opts in.
- Preserved CLI/runtime listener behavior by having `src/prism/scanner_core/execution_request_builder.py` opt in explicitly when assembling the canonical non-collection runtime container.
- Updated focused tests to cover cache refresh after `replace_scan_options()`, explicit default-listener opt-in, and the execution-request builder opt-in seam.

Validation:

- Narrow gate: `pytest -q src/prism/tests/test_t4_03_cli_progress.py::test_di_container_picks_up_default_listeners src/prism/tests/test_t4_03_cli_progress.py::test_explicit_empty_listeners_overrides_defaults src/prism/tests/test_t3_05_scan_telemetry.py::test_telemetry_session_registers_and_clears src/prism/tests/test_di_container.py::test_fsrc_di_container_replace_scan_options_refreshes_factory_snapshots src/prism/tests/test_g02_thread_safety.py::test_di_container_concurrent_factory_calls_no_duplicates` -> `5 passed`
- Importer-layer follow-up: `pytest -q src/prism/tests/test_execution_request_builder.py::TestRuntimeAssemblySeam::test_execution_request_finalization_seam_requires_prepared_policy_enforcement src/prism/tests/test_t3_03_scan_cache.py::test_di_container_exposes_scan_options_as_snapshots src/prism/tests/test_t3_01_scan_phase_events.py::test_di_container_exposes_event_bus src/prism/tests/test_di_helpers.py -k event_bus` -> `4 passed, 7 deselected`

Closure read:

- `G58-H01`: closure-ready. Post-ingress scan-option replacement now refreshes coherent DI-owned state instead of leaving stale cached participants alive.
- `G58-H02`: closure-ready. Default listeners are no longer ambient container inheritance; the runtime path must opt in explicitly.
