## Builder-ScanOptionsContract

- Scope: `src/prism/scanner_core/di.py`
- Fix: preserve caller-provided `scan_options["role_path"]` in DI snapshots instead of rebinding it to the container runtime `role_path`
- Validation: `PYTHONPATH=src .venv/bin/python -m pytest src/prism/tests/test_policy_integration.py::TestFullScanWithAllPolicies::test_container_exposes_scan_options -q`
- Result: passed
