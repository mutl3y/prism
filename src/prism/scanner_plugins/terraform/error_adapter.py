"""Terraform-specific error adapter for structured error envelope construction.

Provides functions to build Terraform error details with unified provenance
information (module, resource, state file, etc.) and classify Terraform
exceptions into platform-specific error codes.
"""

from __future__ import annotations

from typing import Any

from prism.scanner_plugins.terraform.error_codes import (
    TF_APPLY_FAILED,
    TF_BACKEND_FAILED,
    TF_CREDENTIAL_FAILED,
    TF_LOCK_FAILED,
    TF_MODULE_NOT_FOUND,
    TF_PLAN_FAILED,
    TF_RESOURCE_FAILED,
    TF_STATE_CORRUPTED,
    TF_VALIDATION_FAILED,
    TF_VERSION_FAILED,
)


def build_terraform_error_detail(
    resource_context: dict[str, Any],
    exception: Exception,
) -> dict[str, Any]:
    """Build Terraform error detail with unified provenance information.

    Constructs a detail dictionary with Terraform-specific provenance fields
    that can be used in error envelopes for structured error handling and
    diagnostics.

    Args:
        resource_context: Dictionary with resource context information. Expected keys:
            - module: Terraform module name (e.g., 'networking')
            - resource: Resource identifier (e.g., 'aws_instance.web')
            - state_file: Path to tfstate file
            - plan_file: Path to Terraform configuration file
            - line_number: Line number in configuration file
            - provider: Provider name (e.g., 'aws', 'azurerm')
            - error_message: Human-readable error message
        exception: The exception that occurred during Terraform operation

    Returns:
        Dictionary with unified Terraform provenance structure:
        {
            "module": str,
            "resource": str,
            "state_file": str,
            "plan_file": str,
            "line_number": int,
            "provider": str,
            "error_message": str
        }
    """
    detail: dict[str, Any] = {}

    # Add provenance fields from resource context
    if "module" in resource_context:
        detail["module"] = resource_context["module"]
    if "resource" in resource_context:
        detail["resource"] = resource_context["resource"]
    if "state_file" in resource_context:
        detail["state_file"] = resource_context["state_file"]
    if "plan_file" in resource_context:
        detail["plan_file"] = resource_context["plan_file"]
    if "line_number" in resource_context:
        detail["line_number"] = resource_context["line_number"]
    if "provider" in resource_context:
        detail["provider"] = resource_context["provider"]
    if "error_message" in resource_context:
        detail["error_message"] = resource_context["error_message"]

    return detail


def classify_terraform_error(
    exception: Exception,
) -> tuple[str, str, bool]:
    """Classify a Terraform exception into error code, category, and recoverability.

    Maps common Terraform exception types to structured error metadata for
    use in error envelope construction.

    Args:
        exception: The exception to classify

    Returns:
        Tuple of (error_code, category, recoverable):
        - error_code: Terraform-specific error code (e.g., TF_PLAN_FAILED)
        - category: Error category (runtime, io, parser, api, auth)
        - recoverable: True if scan can continue despite this error
    """
    exception_type = type(exception).__name__
    exception_msg = str(exception).lower()

    # Authentication and credential errors
    if exception_type in ("PermissionError", "OSError") and (
        "credential" in exception_msg or "access denied" in exception_msg
    ):
        return TF_CREDENTIAL_FAILED, "auth", False

    if exception_type in ("ValueError", "RuntimeError") and (
        "auth" in exception_msg or "credential" in exception_msg
    ):
        return TF_CREDENTIAL_FAILED, "auth", False

    # File not found errors (modules)
    if exception_type == "FileNotFoundError":
        if "module" in exception_msg:
            return TF_MODULE_NOT_FOUND, "io", False
        else:
            return TF_MODULE_NOT_FOUND, "io", False

    # State file errors
    if exception_type in ("RuntimeError", "ValueError"):
        if "state" in exception_msg and (
            "corrupt" in exception_msg or "invalid" in exception_msg
        ):
            return TF_STATE_CORRUPTED, "io", False
        elif "lock" in exception_msg:
            return TF_LOCK_FAILED, "io", True
        elif "backend" in exception_msg:
            return TF_BACKEND_FAILED, "io", True

    # Plan and validation errors
    if exception_type in ("RuntimeError", "ValueError", "SyntaxError"):
        if "plan" in exception_msg and "fail" in exception_msg:
            return TF_PLAN_FAILED, "parser", False
        elif "validation" in exception_msg or "validate" in exception_msg:
            return TF_VALIDATION_FAILED, "parser", False
        elif "version" in exception_msg and (
            "mismatch" in exception_msg or "incompatible" in exception_msg
        ):
            return TF_VERSION_FAILED, "runtime", False

    # Apply and resource errors
    if exception_type in ("RuntimeError", "Exception"):
        if "apply" in exception_msg and "fail" in exception_msg:
            return TF_APPLY_FAILED, "runtime", False
        elif "resource" in exception_msg and (
            "creation" in exception_msg or "failed" in exception_msg
        ):
            return TF_RESOURCE_FAILED, "runtime", False

    # Default: generic apply failure (non-recoverable)
    return TF_APPLY_FAILED, "runtime", False
