# Builder-ControlFlow Wave 2 Summary

## Scope

- Finding: G46-H06
- Owned files:
  - src/prism/scanner_core/di.py
  - src/prism/scanner_core/feature_detector.py
  - src/prism/scanner_core/variable_discovery.py
  - src/prism/scanner_core/scan_cache.py
  - src/prism/api_layer/non_collection.py
  - src/prism/tests/test_t3_03_scan_cache.py
  - src/prism/tests/test_g03_scan_cache_integration.py

## Changes

- Added container-only scan option snapshot helpers in `scanner_core/di.py` and switched DI property/factory paths to return fresh snapshots instead of the caller-owned live dict.
- Updated `FeatureDetector` and `VariableDiscovery` to clone constructor options and pass fresh per-call option snapshots into plugins, preserving opaque prepared-policy object identity while cutting shared mutable control-plane containers.
- Updated `InMemoryLRUScanCache` to clone mutable container payloads on both `set()` and `get()` so stored results and returned results no longer share mutable state across callers.
- Added regression coverage for DI scan-option snapshots, per-call plugin snapshots, cache copy-on-set/get behavior, and cache-hit result isolation.
- Tightened the cache integration tests to use the injectable route seam so they validate cache behavior without depending on unrelated scan-pipeline preflight state.

## Validation

- `python3 -m pytest -q src/prism/tests/test_t3_03_scan_cache.py src/prism/tests/test_g03_scan_cache_integration.py`
- Result: 19 passed
