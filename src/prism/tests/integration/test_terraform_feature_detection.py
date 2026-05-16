"""Tests for TerraformFeatureDetectionPlugin stateless contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from prism.scanner_plugins.terraform.feature_detection import (
    TerraformFeatureDetectionPlugin,
)
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.tests.fixtures.fixtures_terraform_modules import (
    build_nested_terraform_module_fixture,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
TERRAFORM_FIXTURE_ROOT = PROJECT_ROOT / "src/prism/tests/fixtures/terraform"


pytestmark = pytest.mark.terraform


class TestTerraformFeatureDetectionPlugin:
    """Verify TerraformFeatureDetectionPlugin meets contract."""

    def test_terraform_feature_detection_plugin_is_stateless(self) -> None:
        """Verify PLUGIN_IS_STATELESS = True."""
        assert TerraformFeatureDetectionPlugin.PLUGIN_IS_STATELESS is True

    def test_terraform_feature_detection_plugin_detect_features_returns_empty_context(
        self,
    ) -> None:
        """Verify detect_features stays fail-closed for missing paths."""
        plugin = TerraformFeatureDetectionPlugin()

        result = plugin.detect_features(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )

        assert isinstance(result, dict)
        assert "task_files_scanned" in result
        assert result["task_files_scanned"] == 0

    def test_terraform_feature_detection_extracts_fixture_metadata(self) -> None:
        """Verify detect_features extracts deterministic module metadata."""
        plugin = TerraformFeatureDetectionPlugin()

        result = plugin.detect_features(
            role_path=str(TERRAFORM_FIXTURE_ROOT),
            scan_options={"role_path": str(TERRAFORM_FIXTURE_ROOT)},
        )

        assert result["task_files_scanned"] == 3
        assert result["tasks_scanned"] == 5
        assert result["unique_modules"] == (
            "aws_instance.web, aws_security_group.app, "
            "aws_subnet.private, aws_vpc.main"
        )
        assert result["external_collections"] == "aws"
        assert result["included_roles"] == "none"
        assert result["dynamic_included_roles"] == "none"

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
        """Verify missing paths still return fail-closed fallback values."""
        plugin = TerraformFeatureDetectionPlugin()

        result = plugin.detect_features(
            role_path="/tmp/terraform-module",
            scan_options={"role_path": "/tmp/terraform-module"},
        )

        assert result["tasks_scanned"] == 0
        assert result["recursive_task_includes"] == 0
        assert result["unique_modules"] == "none"
        assert result["external_collections"] == "none"
        assert result["handlers_notified"] == "none"
        assert result["privileged_tasks"] == 0
        assert result["conditional_tasks"] == 0
        assert result["tagged_tasks"] == 0
        assert result["included_role_calls"] == 0
        assert result["included_roles"] == "none"
        assert result["dynamic_included_role_calls"] == 0
        assert result["dynamic_included_roles"] == "none"
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

    def test_terraform_feature_detection_counts_nested_module_signals(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify feature detection includes nested Terraform directories under role_path."""
        plugin = TerraformFeatureDetectionPlugin()
        fixture_root = build_nested_terraform_module_fixture(tmp_path)

        result = plugin.detect_features(
            role_path=str(fixture_root),
            scan_options={"role_path": str(fixture_root)},
        )

        assert result["task_files_scanned"] == 6
        assert result["tasks_scanned"] == 3
        assert result["recursive_task_includes"] == 2
        assert result["included_role_calls"] == 2
        assert result["included_roles"] == "compute, networking"
        assert result["unique_modules"] == "aws_instance.app, aws_s3_bucket.logs"
        assert result["external_collections"] == "aws"
