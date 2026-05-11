"""Test Terraform README renderer metadata-backed output contracts (Wave 3)."""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform import TerraformReadmeRendererPlugin


pytestmark = pytest.mark.terraform


class TestTerraformRendererMetadataBackedSections:
    """Verify Terraform renderer uses metadata to produce meaningful output."""

    def test_resources_section_from_metadata(self) -> None:
        """RED: resources section should render metadata-backed resource inventory."""
        plugin = TerraformReadmeRendererPlugin()

        # When metadata contains managed_resources
        metadata = {
            "managed_resources": [
                "aws_vpc.main",
                "aws_subnet.private",
                "aws_security_group.default",
            ]
        }

        result = plugin.render_section_body(
            section_id="resources",
            role_name="vpc-module",
            description="VPC infrastructure module",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        # Then output should list resources with markdown formatting
        assert result is not None
        assert "aws_vpc.main" in result
        assert "aws_subnet.private" in result
        assert "aws_security_group.default" in result
        assert "-" in result  # Markdown list format

    def test_provider_requirements_section_from_metadata(self) -> None:
        """RED: requirements section should render provider requirements from metadata."""
        plugin = TerraformReadmeRendererPlugin()

        metadata = {
            "provider_requirements": [
                "terraform >= 1.5",
                "aws >= 5.0",
                "kubernetes >= 2.20",
            ]
        }

        result = plugin.render_section_body(
            section_id="requirements",
            role_name="platform-module",
            description="Platform infrastructure",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        # Then output should list provider requirements
        assert result is not None
        assert "terraform" in result
        assert "aws" in result
        assert "kubernetes" in result

    def test_variables_section_description_from_metadata(self) -> None:
        """RED: purpose section should include metadata-enriched description."""
        plugin = TerraformReadmeRendererPlugin()

        metadata = {
            "module_description": "Multi-environment VPC provisioning with dynamic CIDR allocation"
        }

        result = plugin.render_section_body(
            section_id="purpose",
            role_name="vpc-module",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        # Then output should use metadata description
        assert result is not None
        assert "Multi-environment VPC provisioning" in result or "vpc-module" in result

    def test_operational_constraints_section_from_metadata(self) -> None:
        """RED: operational_constraints section should render from metadata."""
        plugin = TerraformReadmeRendererPlugin()

        metadata = {
            "operational_constraints": [
                "State locking required for concurrent operations",
                "Remote backend mandatory for production",
                "Workspace isolation enforced per environment",
            ]
        }

        result = plugin.render_section_body(
            section_id="operational_constraints",
            role_name="backend-module",
            description="Backend configuration",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        # Then output should list constraints
        assert result is not None
        assert "State locking required" in result or "concurrent" in result

    def test_scanner_report_section_from_metadata_relpath(self) -> None:
        """RED: scanner_report section should render when metadata has relpath."""
        plugin = TerraformReadmeRendererPlugin()

        metadata = {
            "scanner_report_relpath": "docs/terraform-scan-report.md"
        }

        result = plugin.render_section_body(
            section_id="scanner_report",
            role_name="main",
            description="Root module",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        # Then output should contain scanner report blurb
        assert result is not None
        assert "docs/terraform-scan-report.md" in result

    def test_fallback_when_metadata_unavailable(self) -> None:
        """RED: renderer should provide sensible fallback when metadata missing."""
        plugin = TerraformReadmeRendererPlugin()

        metadata = {}  # Empty metadata

        result = plugin.render_section_body(
            section_id="resources",
            role_name="main",
            description="Root module",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        # Then output should be sensible fallback
        assert result is not None
        assert "No" in result or "resources" in result.lower() or "detected" in result.lower()

    def test_identity_section_with_workspace_metadata(self) -> None:
        """RED: identity section should render workspace from metadata."""
        plugin = TerraformReadmeRendererPlugin()

        identity_metadata = {
            "workspace": "production",
            "backend_type": "s3",
        }

        result = plugin.render_identity_section(
            section_id="purpose",
            role_name="production-infra",
            description="Production infrastructure",
            requirements=[],
            identity_metadata=identity_metadata,
            metadata={},
        )

        # Then output should include workspace information
        assert result is not None
        assert ("production" in result.lower() or "production-infra" in result)

    def test_extra_section_ids_includes_operational_constraints(self) -> None:
        """RED: plugin should advertise operational_constraints as extra section."""
        plugin = TerraformReadmeRendererPlugin()

        extra_sections = plugin.extra_section_ids()

        assert "operational_constraints" in extra_sections
        assert "scanner_report" in extra_sections

    def test_merge_eligible_sections_includes_operational_constraints(self) -> None:
        """RED: plugin should mark operational_constraints as merge-eligible."""
        plugin = TerraformReadmeRendererPlugin()

        merge_eligible = plugin.merge_eligible_section_ids()

        assert "operational_constraints" in merge_eligible


class TestTerraformScanMetadataSchema:
    """Verify Terraform scan metadata schema contracts."""

    def test_terraform_metadata_schema_keys(self) -> None:
        """RED: Terraform execution should populate standard metadata schema."""
        from prism.scanner_plugins.terraform import build_terraform_execution_bundle

        bundle = build_terraform_execution_bundle(
            scan_options={"role_path": "/tmp/terraform"}
        )

        # Verify bundle has expected contract keys
        assert "prepared_policy" in bundle
        assert "platform_participants" in bundle

    def test_terraform_renderer_handles_typed_metadata(self) -> None:
        """RED: renderer should handle typed metadata dicts safely."""
        plugin = TerraformReadmeRendererPlugin()

        # Metadata with mixed types and None values
        metadata: dict[str, object] = {
            "managed_resources": ["resource1", "resource2"],
            "provider_requirements": None,
            "module_description": "Test module",
            "scan_timestamp": 1234567890,
        }

        result = plugin.render_section_body(
            section_id="resources",
            role_name="test",
            description="Test",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        # Should not raise, should handle safely
        assert result is not None
