agent name: Builder-Ownership
fix_group_key: execution_request.default_listener_isolation
invariant preserved: Request-local observability must stay isolated per scan; runtime assembly must not inherit process-global listeners in a way that leaks telemetry or progress across overlapping requests.
status: closed-ready

Implemented change:

- `execution_request_builder._assemble_runtime_participants()` no longer opts runtime DI containers into `inherit_default_event_listeners`.
- Added a regression test proving process-global listeners are not copied into the execution-request event bus.

Validation:

- narrow gate: `pytest -q src/prism/tests/test_execution_request_builder.py src/prism/tests/test_t3_05_scan_telemetry.py src/prism/tests/test_t4_03_cli_progress.py -k 'listener or telemetry or progress or inherit'`
- result: 14 passed, 17 deselected

Importer-layer follow-up:

- `pytest -q src/prism/tests/test_t3_01_scan_phase_events.py -k event_bus`
- result: 2 passed, 11 deselected

Scope:

- scope expansion needed: no

Regression pattern:

- Request-assembly code must not silently opt into process-global observability listeners; require explicit caller opt-in at DI construction boundaries.
