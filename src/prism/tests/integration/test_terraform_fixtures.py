"""Tests for Terraform fixture integration.

Tests that Terraform fixtures work correctly with the adapter layer
and produce expected error envelopes.
"""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform.error_adapter import (
    build_terraform_error_detail,
)

pytestmark = pytest.mark.terraform


class TestPlanFixtures:
    """Test plan-related fixture integration."""

    def test_plan_failed_fixture_integration(
        self, tf_plan_failed_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("terraform plan failed")

        detail = build_terraform_error_detail(tf_plan_failed_context, exception)

        assert detail["module"] == "networking"
        assert detail["plan_file"] == "/path/to/main.tf"
        assert detail["line_number"] == 42
        assert "plan failed" in detail["error_message"]

    def test_validation_failed_fixture_integration(
        self, tf_validation_failed_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("validation failed")

        detail = build_terraform_error_detail(tf_validation_failed_context, exception)

        assert detail["module"] == "compute"
        assert detail["provider"] == "aws"
        assert "validation failed" in detail["error_message"]

    def test_version_mismatch_fixture_integration(
        self, tf_version_mismatch_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("version mismatch")

        detail = build_terraform_error_detail(tf_version_mismatch_context, exception)

        assert detail["module"] == "database"
        assert "version mismatch" in detail["error_message"]


class TestApplyFixtures:
    """Test apply-related fixture integration."""

    def test_apply_failed_fixture_integration(
        self, tf_apply_failed_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("terraform apply failed")

        detail = build_terraform_error_detail(tf_apply_failed_context, exception)

        assert detail["module"] == "infrastructure"
        assert detail["resource"] == "aws_instance.web"
        assert detail["state_file"] == "/path/to/terraform.tfstate"
        assert "apply failed" in detail["error_message"]

    def test_state_lock_fixture_integration(
        self, tf_state_lock_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("state lock acquisition failed")

        detail = build_terraform_error_detail(tf_state_lock_context, exception)

        assert detail["module"] == "storage"
        assert detail["state_file"] == "/path/to/terraform.tfstate"
        assert "lock acquisition failed" in detail["error_message"]

    def test_resource_failed_fixture_integration(
        self, tf_resource_failed_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("resource creation failed")

        detail = build_terraform_error_detail(tf_resource_failed_context, exception)

        assert detail["module"] == "networking"
        assert detail["resource"] == "azurerm_virtual_network.main"
        assert detail["provider"] == "azurerm"
        assert "resource creation failed" in detail["error_message"]


class TestStateFixtures:
    """Test state-related fixture integration."""

    def test_state_corrupted_fixture_integration(
        self, tf_state_corrupted_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("state file corrupted")

        detail = build_terraform_error_detail(tf_state_corrupted_context, exception)

        assert detail["module"] == "production"
        assert detail["state_file"] == "/path/to/terraform.tfstate"
        assert "state file corrupted" in detail["error_message"]

    def test_backend_failed_fixture_integration(
        self, tf_backend_failed_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("backend initialization failed")

        detail = build_terraform_error_detail(tf_backend_failed_context, exception)

        assert detail["module"] == "infrastructure"
        assert "s3://" in detail["state_file"]
        assert detail["provider"] == "aws"
        assert "backend initialization failed" in detail["error_message"]

    def test_remote_state_error_fixture_integration(
        self, tf_remote_state_error_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("remote state access failed")

        detail = build_terraform_error_detail(tf_remote_state_error_context, exception)

        assert detail["module"] == "networking"
        assert "azurerm://" in detail["state_file"]
        assert detail["provider"] == "azurerm"
        assert "remote state access failed" in detail["error_message"]


class TestModuleFixtures:
    """Test module-related fixture integration."""

    def test_module_not_found_fixture_integration(
        self, tf_module_not_found_context: dict[str, str]
    ) -> None:
        exception = FileNotFoundError("module not found")

        detail = build_terraform_error_detail(tf_module_not_found_context, exception)

        assert detail["module"] == "networking"
        assert detail["plan_file"] == "/path/to/main.tf"
        assert "module not found" in detail["error_message"]

    def test_module_version_conflict_fixture_integration(
        self, tf_module_version_conflict_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("module version conflict")

        detail = build_terraform_error_detail(
            tf_module_version_conflict_context, exception
        )

        assert detail["module"] == "compute"
        assert "version conflict" in detail["error_message"]

    def test_dependency_cycle_fixture_integration(
        self, tf_dependency_cycle_context: dict[str, str]
    ) -> None:
        exception = RuntimeError("dependency cycle detected")

        detail = build_terraform_error_detail(tf_dependency_cycle_context, exception)

        assert detail["module"] == "infrastructure"
        assert "dependency cycle" in detail["error_message"]
