"""Tests for Terraform error adapter core functionality.

Tests error detection, provenance extraction, and secret sanitization
for Terraform platform errors.
"""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform.error_adapter import (
    build_terraform_error_detail,
    classify_terraform_error,
)
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

pytestmark = pytest.mark.terraform


class TestBuildTerraformErrorDetail:
    """Test error detail construction with Terraform provenance."""

    def test_build_error_detail_resource_context(self) -> None:
        resource_context = {
            "module": "networking",
            "resource": "aws_instance.web",
            "state_file": "/path/to/terraform.tfstate",
            "error_message": "Resource creation failed",
        }
        exception = RuntimeError("Resource failed")

        detail = build_terraform_error_detail(resource_context, exception)

        assert detail["module"] == "networking"
        assert detail["resource"] == "aws_instance.web"
        assert detail["state_file"] == "/path/to/terraform.tfstate"
        assert detail["error_message"] == "Resource creation failed"

    def test_build_error_detail_plan_context(self) -> None:
        resource_context = {
            "module": "database",
            "plan_file": "/path/to/main.tf",
            "line_number": 42,
            "error_message": "Invalid configuration",
        }
        exception = RuntimeError("Plan failed")

        detail = build_terraform_error_detail(resource_context, exception)

        assert detail["module"] == "database"
        assert detail["plan_file"] == "/path/to/main.tf"
        assert detail["line_number"] == 42
        assert detail["error_message"] == "Invalid configuration"

    def test_build_error_detail_minimal_context(self) -> None:
        resource_context: dict[str, str] = {}
        exception = RuntimeError("Generic error")

        detail = build_terraform_error_detail(resource_context, exception)

        assert isinstance(detail, dict)

    def test_build_error_detail_preserves_all_fields(self) -> None:
        resource_context = {
            "module": "test-module",
            "resource": "test_resource.name",
            "state_file": "terraform.tfstate",
            "plan_file": "main.tf",
            "line_number": 10,
            "provider": "aws",
            "error_message": "Test error",
        }
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(resource_context, exception)

        assert len(detail) == 7
        for key in resource_context:
            assert detail[key] == resource_context[key]


class TestClassifyTerraformError:
    """Test Terraform error classification into error codes and categories."""

    def test_classify_plan_failed(self) -> None:
        exception = RuntimeError("Error: terraform plan failed")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_PLAN_FAILED
        assert category == "parser"
        assert recoverable is False

    def test_classify_validation_failed(self) -> None:
        exception = RuntimeError("Error: validation failed")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_VALIDATION_FAILED
        assert category == "parser"
        assert recoverable is False

    def test_classify_version_failed(self) -> None:
        exception = RuntimeError("Error: version mismatch")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_VERSION_FAILED
        assert category == "runtime"
        assert recoverable is False

    def test_classify_apply_failed(self) -> None:
        exception = RuntimeError("Error: terraform apply failed")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_APPLY_FAILED
        assert category == "runtime"
        assert recoverable is False

    def test_classify_resource_failed(self) -> None:
        exception = RuntimeError("Error: resource creation failed")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_RESOURCE_FAILED
        assert category == "runtime"
        assert recoverable is False

    def test_classify_module_not_found(self) -> None:
        exception = FileNotFoundError("Module not found")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_MODULE_NOT_FOUND
        assert category == "io"
        assert recoverable is False

    def test_classify_state_corrupted(self) -> None:
        exception = RuntimeError("Error: state file corrupted")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_STATE_CORRUPTED
        assert category == "io"
        assert recoverable is False

    def test_classify_backend_failed(self) -> None:
        exception = RuntimeError("Error: backend initialization failed")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_BACKEND_FAILED
        assert category == "io"
        assert recoverable is True

    def test_classify_lock_failed(self) -> None:
        exception = RuntimeError("Error: state lock acquisition failed")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_LOCK_FAILED
        assert category == "io"
        assert recoverable is True

    def test_classify_credential_failed(self) -> None:
        exception = PermissionError("Error: invalid credentials")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == TF_CREDENTIAL_FAILED
        assert category == "auth"
        assert recoverable is False
