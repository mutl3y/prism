"""Tests for TerraformVariableDiscoveryPlugin stateless contract."""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform.variable_discovery import (
    TerraformVariableDiscoveryPlugin,
)
from prism.scanner_data import VariableRow


pytestmark = pytest.mark.terraform


class TestTerraformVariableDiscoveryPlugin:
    """Verify TerraformVariableDiscoveryPlugin meets contract."""

    def test_terraform_variable_discovery_plugin_is_stateless(self) -> None:
        """Verify PLUGIN_IS_STATELESS = True."""
        assert TerraformVariableDiscoveryPlugin.PLUGIN_IS_STATELESS is True

    def test_terraform_variable_discovery_plugin_discover_returns_empty_tuple(
        self,
    ) -> None:
        """Verify discover returns empty tuple (fail-closed)."""
        plugin = TerraformVariableDiscoveryPlugin()
        
        result = plugin.discover(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 0

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
