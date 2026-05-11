"""Tests for Terraform provenance extraction.

Tests that Terraform adapter correctly extracts and preserves
provenance information (module, resource, state_file, etc.) from
error contexts.
"""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform.error_adapter import (
    build_terraform_error_detail,
)

pytestmark = pytest.mark.terraform


class TestProvenanceExtraction:
    """Test provenance field extraction from Terraform contexts."""

    def test_extracts_module_provenance(self) -> None:
        context = {"module": "networking"}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert "module" in detail
        assert detail["module"] == "networking"

    def test_extracts_resource_provenance(self) -> None:
        context = {"resource": "aws_instance.web"}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert "resource" in detail
        assert detail["resource"] == "aws_instance.web"

    def test_extracts_state_file_provenance(self) -> None:
        context = {"state_file": "/path/to/terraform.tfstate"}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert "state_file" in detail
        assert detail["state_file"] == "/path/to/terraform.tfstate"

    def test_extracts_plan_file_provenance(self) -> None:
        context = {"plan_file": "/path/to/main.tf"}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert "plan_file" in detail
        assert detail["plan_file"] == "/path/to/main.tf"

    def test_extracts_line_number_provenance(self) -> None:
        context = {"line_number": 42}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert "line_number" in detail
        assert detail["line_number"] == 42

    def test_extracts_provider_provenance(self) -> None:
        context = {"provider": "aws"}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert "provider" in detail
        assert detail["provider"] == "aws"

    def test_extracts_error_message_provenance(self) -> None:
        context = {"error_message": "Test error message"}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert "error_message" in detail
        assert detail["error_message"] == "Test error message"

    def test_preserves_all_provenance_fields(self) -> None:
        context = {
            "module": "test-module",
            "resource": "test_resource.name",
            "state_file": "terraform.tfstate",
            "plan_file": "main.tf",
            "line_number": 10,
            "provider": "aws",
            "error_message": "Complete error",
        }
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert len(detail) == 7
        assert detail["module"] == "test-module"
        assert detail["resource"] == "test_resource.name"
        assert detail["state_file"] == "terraform.tfstate"
        assert detail["plan_file"] == "main.tf"
        assert detail["line_number"] == 10
        assert detail["provider"] == "aws"
        assert detail["error_message"] == "Complete error"

    def test_handles_partial_provenance(self) -> None:
        context = {
            "module": "partial",
            "error_message": "Partial context",
        }
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert len(detail) == 2
        assert detail["module"] == "partial"
        assert detail["error_message"] == "Partial context"
