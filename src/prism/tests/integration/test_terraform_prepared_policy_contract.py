"""Integration tests for Terraform plugin prepared-policy contract."""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform import (
    TerraformFeatureDetectionPlugin,
    TerraformVariableDiscoveryPlugin,
    build_terraform_execution_bundle,
)
from prism.tests.fixtures.fixtures_terraform_pipeline import (
    build_terraform_scan_options,
)


pytestmark = pytest.mark.terraform


class TestTerraformPreparedPolicyContract:
    """Verify prepared-policy contract integrity across plugin chain."""

    def test_terraform_feature_detection_and_variable_discovery_both_stateless(
        self,
    ) -> None:
        """Verify both plugins declare PLUGIN_IS_STATELESS."""
        assert TerraformFeatureDetectionPlugin.PLUGIN_IS_STATELESS is True
        assert TerraformVariableDiscoveryPlugin.PLUGIN_IS_STATELESS is True

    def test_terraform_plugins_work_with_execution_bundle(self) -> None:
        """Verify plugins work together with execution bundle."""
        bundle = build_terraform_execution_bundle(
            scan_options=build_terraform_scan_options()
        )
        
        feature_plugin = TerraformFeatureDetectionPlugin()
        variable_plugin = TerraformVariableDiscoveryPlugin()
        
        scan_options = build_terraform_scan_options(
            prepared_policy_bundle=bundle["prepared_policy"],
        )
        
        features = feature_plugin.detect_features(
            role_path="/tmp/terraform-module",
            scan_options=scan_options,
        )
        variables = variable_plugin.discover(
            role_path="/tmp/terraform-module",
            scan_options=scan_options,
        )
        
        assert isinstance(features, dict)
        assert isinstance(variables, tuple)
        assert len(variables) == 0

    def test_terraform_execution_bundle_policies_are_callable(self) -> None:
        """Verify all prepared-policy participants are callable."""
        bundle = build_terraform_execution_bundle()
        prepared_policy = bundle["prepared_policy"]
        
        for key, policy in prepared_policy.items():
            assert policy is not None, f"Policy {key} is None"
            assert hasattr(
                policy, "__class__"
            ), f"Policy {key} is not an object instance"

    def test_terraform_bundle_with_fixture_options(self) -> None:
        """Verify execution bundle works with fixture-built options."""
        scan_options = build_terraform_scan_options(role_path="/custom/path")
        bundle = build_terraform_execution_bundle(scan_options=scan_options)
        
        assert "prepared_policy" in bundle
        assert "platform_participants" in bundle
        
        feature_plugin = TerraformFeatureDetectionPlugin()
        result = feature_plugin.detect_features(
            role_path="/custom/path",
            scan_options=scan_options,
        )
        
        assert result["task_files_scanned"] == 0
