"""Tests for Terraform execution bundle metadata and capability behavior."""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform import (
    build_terraform_execution_bundle,
    TerraformScanPipelinePlugin,
)
from prism.scanner_plugins.interfaces import PlatformExecutionBundle


pytestmark = pytest.mark.terraform


class TestTerraformExecutionBundleMetadata:
    """Verify execution bundle emits deterministic platform metadata."""

    def test_terraform_execution_bundle_returns_platform_execution_bundle(
        self,
    ) -> None:
        """Verify bundle is PlatformExecutionBundle typed."""
        bundle = build_terraform_execution_bundle()

        assert isinstance(bundle, dict)
        assert "prepared_policy" in bundle
        assert "platform_participants" in bundle

    def test_terraform_execution_bundle_participants_contain_key_policies(self) -> None:
        """Verify platform_participants contain required policy instances."""
        bundle = build_terraform_execution_bundle()
        
        participants = bundle["platform_participants"]
        assert "task_line_parsing" in participants
        assert "jinja_analysis" in participants

    def test_terraform_execution_bundle_prepared_policy_full_coverage(self) -> None:
        """Verify prepared_policy covers all policy participant types."""
        bundle = build_terraform_execution_bundle()
        
        prepared_policy = bundle["prepared_policy"]
        required_keys = {
            "task_line_parsing",
            "jinja_analysis",
            "task_traversal",
            "yaml_parsing",
            "variable_extractor",
            "task_annotation_parsing",
        }
        
        for key in required_keys:
            assert key in prepared_policy, f"Missing {key} in prepared_policy"

    def test_terraform_execution_bundle_participants_reference_prepared_policy(
        self,
    ) -> None:
        """Verify platform_participants reference same objects in prepared_policy."""
        bundle = build_terraform_execution_bundle()
        
        participants = bundle["platform_participants"]
        prepared_policy = bundle["prepared_policy"]
        
        assert (
            participants["task_line_parsing"]
            is prepared_policy["task_line_parsing"]
        )
        assert (
            participants["jinja_analysis"]
            is prepared_policy["jinja_analysis"]
        )

    def test_terraform_scan_pipeline_plugin_emits_deterministic_metadata(self) -> None:
        """Verify scan pipeline plugin emits deterministic platform metadata."""
        plugin = TerraformScanPipelinePlugin()
        
        payload = {
            "metadata": {},
        }
        
        result = plugin.orchestrate_scan_payload(
            payload=payload,
            scan_options={"role_path": "/tmp/terraform-module"},
            strict_mode=False,
        )
        
        metadata = result.get("metadata")
        assert metadata is not None
        assert metadata.get("plugin_platform") == "terraform"
        assert metadata.get("plugin_name") == "terraform"
        assert metadata.get("plugin_enabled") is True

    def test_terraform_execution_bundle_with_scan_options(self) -> None:
        """Verify execution bundle accepts scan_options parameter."""
        scan_options = {"role_path": "/tmp/terraform-module"}
        
        bundle = build_terraform_execution_bundle(scan_options=scan_options)
        
        assert isinstance(bundle, dict)
        assert "prepared_policy" in bundle
        assert "platform_participants" in bundle
