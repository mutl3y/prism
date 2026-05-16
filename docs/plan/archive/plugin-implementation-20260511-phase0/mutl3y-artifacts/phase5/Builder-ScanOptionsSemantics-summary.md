Builder-ScanOptionsSemantics summary

- Wave: g84 rem-3
- Scope: restore DI scan option snapshot isolation for per-container role paths
- Changes:
  - Rebased `DIContainer._snapshot_scan_options()` to stamp the container-owned `role_path` into each returned snapshot.
  - Updated the policy integration assertion to match canonical DI behavior by checking the resolved role directory name instead of the stale seed value.
- Validation:
  - `PYTHONPATH=src .venv/bin/python -m pytest src/prism/tests/test_policy_integration.py::TestFullScanWithAllPolicies::test_container_exposes_scan_options src/prism/tests/test_real_world_scans.py::TestConcurrentMultiRoleScan::test_multiple_roles_sequential_scans -q`
  - Result: 2 passed
