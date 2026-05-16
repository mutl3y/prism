"""Protocol definitions for platform-extensible error envelope structure.

This module defines the contracts for building and extending error entries
with platform-specific details while maintaining backward compatibility.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PlatformErrorDetail(Protocol):
    """Protocol for platform-specific error detail structures.

    Implementations provide structured, type-safe extensions to generic
    ScanErrorEntry for platform-specific error information. Each platform
    (Kubernetes, Terraform, Ansible) implements this protocol to provide
    domain-specific error context.

    Examples:
        - Kubernetes detail: cluster, namespace, kind, name, manifest_path, http_status
        - Terraform detail: provider, region, resource_type, plan_path, line_number
        - Ansible detail: task_file, line_number, task_index, role_path, module_name

    Contract:
        Implementations must serialize to dict[str, Any] for JSON output.
        All values must be JSON-serializable (str, int, bool, list, dict, None).
    """

    def to_dict(self) -> dict[str, Any]:
        """Serialize platform-specific detail to JSON-serializable dict."""
        ...


@runtime_checkable
class ErrorEnvelopeBuilder(Protocol):
    """Protocol for building error entries with platform-specific extensions.

    Builders encapsulate the logic for:
    - Normalizing exception information into structured error entries
    - Extracting platform-specific context (resource IDs, file paths, etc.)
    - Applying secret sanitization (stripping kubeconfig paths, tokens)
    - Validating error taxonomy compliance (category, error_code, recoverable)

    Contract:
        Builders must preserve backward compatibility: existing ScanErrorEntry
        fields are required, new fields (category, error_code, recoverable, detail)
        are optional for backward compatibility with Ansible-only scans.
    """

    def build_error_entry(
        self,
        phase: str,
        error_type: str,
        message: str,
        *,
        traceback: str | None = None,
        cause: str | None = None,
        error_code: str | None = None,
        category: str | None = None,
        recoverable: bool | None = None,
        resource_id: str | None = None,
        detail: dict[str, Any] | None = None,
        cause_type: str | None = None,
    ) -> dict[str, Any]:
        """Build a structured ScanErrorEntry with optional extensions.

        Args:
            phase: Error phase ("ingress", "extraction", "rendering")
            error_type: Exception class name (e.g., "ValueError", "RuntimeError")
            message: Human-readable error message
            traceback: Optional stack trace
            cause: Optional underlying cause description
            error_code: Platform error code (e.g., "K8S_API_ERROR")
            category: Error category (runtime, io, parser, api, auth)
            recoverable: True for transient errors, False for permanent
            resource_id: Platform resource identifier (namespace/pod, module.resource)
            detail: Platform-specific structured data dict
            cause_type: Underlying exception class name

        Returns:
            dict[str, Any]: ScanErrorEntry-compatible dict with optional extensions
        """
        ...

    def sanitize_detail(self, detail: dict[str, Any]) -> dict[str, Any]:
        """Apply security-sensitive field sanitization to platform detail.

        Strips:
        - Kubeconfig paths containing secrets (e.g., api-token fields)
        - AWS/GCP credential tokens
        - SSH private keys or passphrases

        Args:
            detail: Platform-specific detail dict

        Returns:
            dict[str, Any]: Sanitized detail dict
        """
        ...

    def validate_error_entry(self, entry: dict[str, Any]) -> bool:
        """Validate error entry against taxonomy and structural constraints.

        Checks:
        - Required fields present (phase, error_type, message)
        - Category valid if present (runtime, io, parser, api, auth)
        - Error code follows naming convention (UPPER_SNAKE_CASE)
        - Detail is valid JSON-serializable dict if present

        Args:
            entry: ScanErrorEntry dict to validate

        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        ...
