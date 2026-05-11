"""Tests for TerraformFeatureDetectionPlugin stateless contract."""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform.feature_detection import (
    TerraformFeatureDetectionPlugin,
)
from prism.scanner_data.contracts_request import FeaturesContext, ScanOptionsDict


pytestmark = pytest.mark.terraform


class TestTerraformFeatureDetectionPlugin:
    """Verify TerraformFeatureDetectionPlugin meets contract."""

    def test_terraform_feature_detection_plugin_is_stateless(self) -> None:
        """Verify PLUGIN_IS_STATELESS = True."""
        assert TerraformFeatureDetectionPlugin.PLUGIN_IS_STATELESS is True

    def test_terraform_feature_detection_plugin_detect_features_returns_empty_context(
        self,
    ) -> None:
        """Verify detect_features returns empty FeaturesContext (fail-closed)."""
        plugin = TerraformFeatureDetectionPlugin()
        
        result = plugin.detect_features(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )
        
        assert isinstance(result, dict)
        assert "task_files_scanned" in result
        assert result["task_files_scanned"] == 0

    def test_terraform_feature_detection_plugin_detect_features_with_di(self) -> None:
        """Verify detect_features works when DI container passed."""
        plugin = TerraformFeatureDetectionPlugin(di=None)
        
        result = plugin.detect_features(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )
        
        assert isinstance(result, dict)
        assert result["task_files_scanned"] == 0

    def test_terraform_feature_detection_emits_zero_features_context(self) -> None:
        """Verify all feature counters are zero."""
        plugin = TerraformFeatureDetectionPlugin()
        
        result = plugin.detect_features(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )
        
        assert result["tasks_scanned"] == 0
        assert result["recursive_task_includes"] == 0
        assert result["external_collections"] == ""
        assert result["handlers_notified"] == ""
        assert result["privileged_tasks"] == 0
        assert result["conditional_tasks"] == 0
        assert result["tagged_tasks"] == 0
        assert result["included_role_calls"] == 0
        assert result["included_roles"] == ""
        assert result["dynamic_included_role_calls"] == 0
        assert result["dynamic_included_roles"] == ""
        assert result["disabled_task_annotations"] == 0
        assert result["yaml_like_task_annotations"] == 0

    def test_terraform_feature_detection_with_prepared_policy_bundle(self) -> None:
        """Verify detect_features works with prepared_policy_bundle in options."""
        plugin = TerraformFeatureDetectionPlugin()
        
        scan_options: ScanOptionsDict = {
            "role_path": "/tmp/terraform-module",
            "prepared_policy_bundle": {
                "comment_doc_marker_prefix": "prism",
            },
        }
        
        result = plugin.detect_features(
            role_path="/tmp/terraform-module",
            scan_options=scan_options,
        )
        
        assert isinstance(result, dict)
        assert result["task_files_scanned"] == 0
