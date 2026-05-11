"""Tests for TerraformVariableDiscoveryPlugin stateless contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from prism.scanner_plugins.terraform.variable_discovery import (
    TerraformVariableDiscoveryPlugin,
)
from prism.tests.fixtures.fixtures_terraform_modules import (
    build_nested_terraform_module_fixture,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
TERRAFORM_FIXTURE_ROOT = PROJECT_ROOT / "src/prism/tests/fixtures/terraform"


pytestmark = pytest.mark.terraform


class TestTerraformVariableDiscoveryPlugin:
    """Verify TerraformVariableDiscoveryPlugin meets contract."""

    def test_terraform_variable_discovery_plugin_is_stateless(self) -> None:
        """Verify PLUGIN_IS_STATELESS = True."""
        assert TerraformVariableDiscoveryPlugin.PLUGIN_IS_STATELESS is True

    def test_terraform_variable_discovery_plugin_discover_returns_empty_tuple(
        self,
    ) -> None:
        """Verify discover stays fail-closed for missing paths."""
        plugin = TerraformVariableDiscoveryPlugin()

        result = plugin.discover(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )

        assert isinstance(result, tuple)
        assert len(result) == 0

    def test_terraform_variable_discovery_extracts_fixture_variables(self) -> None:
        """Verify discover extracts deterministic variable rows from fixture files."""
        plugin = TerraformVariableDiscoveryPlugin()

        result = plugin.discover(
            role_path=str(TERRAFORM_FIXTURE_ROOT),
            scan_options={"role_path": str(TERRAFORM_FIXTURE_ROOT)},
        )

        assert [row["name"] for row in result] == [
            "aws_region",
            "project_name",
            "vpc_cidr",
            "private_subnet_cidr",
            "instance_type",
        ]
        assert result[0]["type"] == "string"
        assert result[0]["default"] == "us-east-1"
        assert result[0]["source"] == "terraform:variables.tf"
        assert result[0]["documented"] is True
        assert result[0]["required"] is False
        assert result[0]["secret"] is False
        assert result[0]["provenance_source_file"] == "variables.tf"
        assert result[0]["provenance_line"] == 1
        assert result[0]["provenance_confidence"] == 0.95

    def test_terraform_variable_discovery_plugin_discover_with_di(self) -> None:
        """Verify discover works when DI container passed."""
        plugin = TerraformVariableDiscoveryPlugin(di=None)

        result = plugin.discover(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )

        assert isinstance(result, tuple)
        assert len(result) == 0

    def test_terraform_variable_discovery_with_prepared_policy_bundle(self) -> None:
        """Verify discover works with prepared_policy_bundle in options."""
        plugin = TerraformVariableDiscoveryPlugin()

        scan_options = {
            "role_path": "/tmp/terraform-module",
            "prepared_policy_bundle": {
                "comment_doc_marker_prefix": "prism",
            },
        }

        result = plugin.discover(
            role_path="/tmp/terraform-module",
            scan_options=scan_options,
        )

        assert isinstance(result, tuple)
        assert len(result) == 0

    def test_terraform_variable_discovery_includes_nested_module_variables(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify variable discovery preserves deterministic root-first relative provenance."""
        plugin = TerraformVariableDiscoveryPlugin()
        fixture_root = build_nested_terraform_module_fixture(tmp_path)

        result = plugin.discover(
            role_path=str(fixture_root),
            scan_options={"role_path": str(fixture_root)},
        )

        assert [row["name"] for row in result] == [
            "root_region",
            "instance_type",
            "vpc_cidr",
        ]
        assert [row["source"] for row in result] == [
            "terraform:variables.tf",
            "terraform:modules/compute/variables.tf",
            "terraform:modules/networking/variables.tf",
        ]
        assert [row["provenance_source_file"] for row in result] == [
            "variables.tf",
            "modules/compute/variables.tf",
            "modules/networking/variables.tf",
        ]
        assert [row["provenance_line"] for row in result] == [1, 1, 1]
