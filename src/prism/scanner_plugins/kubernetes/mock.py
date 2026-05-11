"""Mock Kubernetes plugin for scanner demonstration and testing.

This is a basic mock implementation that demonstrates the plugin pattern
for Kubernetes manifest scanning. It will be enhanced in Q3 2026 with
real K8s API interaction, manifest validation, and error handling.

**Current Scope** (Mock/Demo):
- Basic K8s manifest parsing from YAML files
- Error envelope construction for common K8s errors
- Unified provenance (manifest file, line number, resource name)
- Sample error codes for testing

**Q3 2026 Scope** (Real Implementation):
- Live K8s cluster connectivity
- API resource validation
- Permission & quota checking
- Network policy analysis
- Security policy auditing
"""

from __future__ import annotations

from typing import Any

__all__ = ["MockKubernetesScanner"]


class MockKubernetesScanner:
    """Mock Kubernetes scanner for Q3 implementation.

    This mock scanner demonstrates the plugin architecture pattern
    before real Kubernetes scanning is implemented.

    **Not for production use.** This is a demonstration of the
    expected interface and error handling patterns.
    """

    def __init__(self) -> None:
        """Initialize the mock K8s scanner."""
        self.name = "kubernetes-mock"
        self.version = "0.1.0-mock"
        self.ready = False

    def scan_manifests(self, manifest_paths: list[str]) -> dict[str, Any]:
        """Mock scan for Kubernetes manifests.

        Args:
            manifest_paths: List of YAML manifest file paths

        Returns:
            Dictionary with scan results (mocked)
        """
        raise NotImplementedError(
            "Kubernetes scanner not yet implemented. "
            "Expected in Q3 2026. Use mock or Ansible scanner for now."
        )

    def build_error_detail(
        self, manifest_path: str, resource_kind: str, line_number: int
    ) -> dict[str, Any]:
        """Build K8s error detail with unified provenance.

        **Unified Provenance Fields** (matches Ansible/Terraform):
        - manifest_path: Path to manifest file (like task_file)
        - line_number: Resource definition start line
        - resource_kind: K8s resource kind (Pod, Deployment, etc.)
        - resource_name: K8s resource name

        Args:
            manifest_path: Path to K8s manifest file
            resource_kind: Kubernetes resource kind
            line_number: Line number in manifest

        Returns:
            Detail dict with K8s provenance fields
        """
        return {
            "cluster": "pending-implementation",
            "manifest_path": manifest_path,
            "line_number": line_number,
            "resource_kind": resource_kind,
            "api_version": "v1",
            "namespace": "default",
            "note": "Mock implementation (Q3 2026)",
        }


# Kubernetes error codes (to be used when real implementation arrives)
K8S_ERROR_CODES = {
    "K8S_API_ERROR",
    "K8S_AUTH_ERROR",
    "K8S_MANIFEST_PARSE_ERROR",
    "K8S_RESOURCE_NOT_FOUND",
    "K8S_TIMEOUT",
    "K8S_CONNECTION_ERROR",
    "K8S_PERMISSION_DENIED",
    "K8S_RESOURCE_CONFLICT",
    "K8S_QUOTA_EXCEEDED",
    "K8S_NETWORK_POLICY_ERROR",
}
