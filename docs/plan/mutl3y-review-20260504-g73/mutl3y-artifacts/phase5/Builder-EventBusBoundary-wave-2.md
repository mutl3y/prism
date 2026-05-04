# Builder-Ownership Wave 2 Summary

- Agent: Builder-Ownership
- Finding: G73-H01
- Status: fixed in owned scope

## Local hypothesis

The leak came from the ambient default-listener registry being stored as mutable process-global state. Any DI container that explicitly opted into defaults could therefore inherit listener registrations created by unrelated threads.

## Change summary

- Replaced the process-global mutable default-listener registry in `scanner_core/events.py` with an ambient `ContextVar` snapshot.
- Kept the public listener registration API unchanged so existing opt-in flows still work in the current execution context.
- Made the DI container snapshot the ambient defaults once at construction time, so later registrations cannot mutate an already-built per-container `EventBus`.

## Focused regression coverage

- Added a thread-boundary test proving a listener registered in one thread is not inherited by an opted-in container built in another thread.
- Added a construction-snapshot test proving an opted-in container only observes the listener set present when it was built.
- Strengthened runtime-participant coverage so later ambient registrations still do not affect non-opt-in runtime participants.

## Validation

- Narrow gate command: `pytest -q src/prism/tests/test_t4_03_cli_progress.py src/prism/tests/test_execution_request_builder.py`
- Result: `32 passed in 0.13s`
