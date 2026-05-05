agent name: Builder-ControlFlow
fix_group_key: non_collection.cache_wiring_identity
invariant preserved: Cache hits must remain semantically tied to the runtime wiring that can change the returned payload; a shared cache must not replay payloads across distinct orchestration or registry behavior.
status: closed-ready
changes:

- Added explicit runtime wiring identity fingerprints for route orchestration, selected-plugin orchestration, and runtime registry inputs before computing non-collection cache keys.
- Covered the fix with a cache integration test for route changes, a scan-cache unit test for registry-instance differentiation, and an importer-layer assertion that the cache key now carries runtime wiring identity.

validation:

- narrow gate: `pytest -q src/prism/tests/test_g03_scan_cache_integration.py src/prism/tests/test_t3_03_scan_cache.py -k 'cache'` -> 24 passed
- importer layer: `pytest -q src/prism/tests/test_api_cli_entrypoints.py -k 'cache'` -> 3 passed

scope expansion needed: no
regression pattern: Shared cache keys on orchestration seams must fingerprint semantics-bearing injected callables and registry instances, not just request data.
