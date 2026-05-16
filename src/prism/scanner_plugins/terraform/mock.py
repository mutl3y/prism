"""Mock Terraform plugin for scanner demonstration and testing.

This is a basic mock implementation that demonstrates the plugin pattern
for Terraform scanning. It will be enhanced in Q3 2026 with real
HCL parsing, plan analysis, and error handling.

**Current Scope** (Mock/Demo):
- Basic Terraform plan/configuration parsing from HCL files
- Error envelope construction for common Terraform errors
- Unified provenance (config file, line number, resource name)
- Sample error codes for testing

**Q3 2026 Scope** (Real Implementation):
- HCL parsing and analysis (using go-hcl2 or python port)
- Terraform plan file analysis
- Provider configuration validation
- State file integrity checking
- Security policy scanning (e.g., exposed secrets)
"""

from __future__ import annotations

from typing import Any

__all__ = ["MockTerraformScanner"]


class MockTerraformScanner:
    """Mock Terraform scanner for Q3 implementation.

    This mock scanner demonstrates the plugin architecture pattern
    before real Terraform scanning is implemented.

    **Not for production use.** This is a demonstration of the
    expected interface and error handling patterns.
    """

    def __init__(self) -> None:
        """Initialize the mock Terraform scanner."""
        self.name = "terraform-mock"
        self.version = "0.1.0-mock"
        self.ready = False

    def scan_plans(self, plan_paths: list[str]) -> dict[str, Any]:
        """Mock scan for Terraform plans.

        Args:
            plan_paths: List of .tf file paths or plan JSON files

        Returns:
            Dictionary with scan results (mocked)
        """
        raise NotImplementedError(
            "Terraform scanner not yet implemented. "
            "Expected in Q3 2026. Use Ansible scanner for now."
        )

    def build_error_detail(
        self, plan_path: str, resource_type: str, line_number: int
    ) -> dict[str, Any]:
        """Build Terraform error detail with unified provenance.

        **Unified Provenance Fields** (matches Ansible/Kubernetes):
        - plan_path: Path to .tf configuration file
        - line_number: Resource definition start line
        - resource_type: Terraform resource type (e.g., aws_instance)
        - provider: Terraform provider (e.g., aws, gcp)

        Args:
            plan_path: Path to Terraform plan/configuration file
            resource_type: Terraform resource type
            line_number: Line number in configuration

        Returns:
            Detail dict with Terraform provenance fields
        """
        return {
            "provider": "pending-implementation",
            "plan_path": plan_path,
            "line_number": line_number,
            "resource_type": resource_type,
            "region": "unknown",
            "note": "Mock implementation (Q3 2026)",
        }


# Terraform error codes (to be used when real implementation arrives)
TF_ERROR_CODES = {
    "TF_PLAN_PARSE_ERROR",
    "TF_PROVIDER_AUTH_ERROR",
    "TF_API_ERROR",
    "TF_FILE_NOT_FOUND",
    "TF_EXECUTION_ERROR",
    "TF_STATE_ERROR",
    "TF_VALIDATION_ERROR",
    "TF_PROVIDER_NOT_FOUND",
    "TF_VERSION_MISMATCH",
    "TF_TIMEOUT",
}
