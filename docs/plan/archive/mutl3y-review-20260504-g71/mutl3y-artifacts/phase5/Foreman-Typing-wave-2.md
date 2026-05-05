## Foreman Recovery Wave 2

- Plan ID: `mutl3y-review-20260504-g71`
- Cycle: `g71`
- Wave: `2`
- Fix group: `api_layer.common.scan_role_payload_contract`
- Status: `closed-ready`

### Local hypothesis

`parse_scan_role_payload()` validates a small public boundary shape but still
returns a raw `dict[str, Any]`. That leaves a typed boundary hole at the public
API seam even though the accepted shape is already narrow enough to expose as a
small typed contract.

### Implemented fix

- Added a local `ScanRolePayload` TypedDict in `api_layer.common`.
- Tightened `parse_scan_role_payload()` to accept `str | Mapping[str, object]`
  and return the validated `ScanRolePayload` contract.
- Added focused regression coverage proving a metadata object survives the
  helper’s validated typed boundary.

### Validation

- Required narrow gate: `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_api_layer_common.py`
- Result: `8 passed`
- Narrow mypy: `cd /raid5/source/test/prism && .venv/bin/python -m mypy src/prism/api_layer/common.py`
- Result: `Success: no issues found in 1 source file`

### Changed files

- `src/prism/api_layer/common.py`
- `src/prism/tests/test_api_layer_common.py`
