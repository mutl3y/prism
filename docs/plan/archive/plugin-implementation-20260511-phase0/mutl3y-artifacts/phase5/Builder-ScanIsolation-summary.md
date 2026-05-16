# Builder-ScanIsolation Summary

Plan: `g84-remediation-mutl3y-cycle-20260509`
Phase: `P5`
Wave: `rem-1`
Slice: `Wave 7 sequential scan isolation`

## Scope

- Owned implementation file: `/raid5/source/test/prism/src/prism/scanner_core/di.py`
- Allowed but unchanged owned file: `/raid5/source/test/prism/src/prism/scanner_core/scan_request.py`

## Change

`DIContainer` now snapshots request scan options with the current container `role_path` rebound into `scan_options["role_path"]` when that key is already present. This preserves per-request identity across sequential scans without changing the existing contract for callers that omit the key.

The same rebinding is applied in both:

- container initialization
- `replace_scan_options()`

## Result

Sequential scans no longer leak placeholder request identity through reused or caller-supplied option payloads. Each container exposes scan options scoped to its own request path.

## Narrow Gate

Command:

```bash
cd /raid5/source/test/prism && PYTHONPATH=src .venv/bin/python -m pytest src/prism/tests/test_real_world_scans.py::TestConcurrentMultiRoleScan::test_multiple_roles_sequential_scans -q
```

Outcome:

```text
.                                                                        [100%]
1 passed in 0.24s
```
