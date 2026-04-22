"""Tests for fsrc/src/prism/api_layer/common.py."""

from __future__ import annotations

import pytest

from prism.api_layer.common import (
    normalize_scan_role_payload_shape,
    parse_scan_role_payload,
)


class TestNormalizeScanRolePayloadShape:
    def test_display_variables_aliased_to_variables(self):
        payload = {"display_variables": [{"name": "x"}]}
        result = normalize_scan_role_payload_shape(payload)
        assert result["variables"] == [{"name": "x"}]

    def test_requirements_display_aliased_to_requirements(self):
        payload = {"requirements_display": ["req1"]}
        result = normalize_scan_role_payload_shape(payload)
        assert result["requirements"] == ["req1"]

    def test_undocumented_default_filters_aliased_to_default_filters(self):
        payload = {"undocumented_default_filters": ["filter_a"]}
        result = normalize_scan_role_payload_shape(payload)
        assert result["default_filters"] == ["filter_a"]

    def test_existing_variables_key_not_overwritten(self):
        payload = {"variables": ["original"], "display_variables": ["shadow"]}
        result = normalize_scan_role_payload_shape(payload)
        assert result["variables"] == ["original"]

    def test_passthrough_dict_with_none_of_the_internal_keys(self):
        payload = {"role_name": "myrole", "readme": "some text"}
        result = normalize_scan_role_payload_shape(payload)
        assert result["role_name"] == "myrole"
        assert result["readme"] == "some text"
        assert "variables" not in result
        assert "requirements" not in result
        assert "default_filters" not in result


class TestParseScanRolePayload:
    def test_accepts_dict_directly(self):
        payload = {"role_name": "testrole"}
        result = parse_scan_role_payload(payload)
        assert result == {"role_name": "testrole"}

    def test_raises_runtime_error_on_non_dict_json(self):
        with pytest.raises(RuntimeError, match="SCAN_ROLE_PAYLOAD_TYPE_INVALID"):
            parse_scan_role_payload("[1, 2, 3]")
