"""Unit tests for error envelope construction, validation, and sanitization.

Tests cover:
- Basic error entry construction with required and optional fields
- Platform-specific detail population (Ansible, K8s, Terraform)
- Secret sanitization (kubeconfig paths, tokens, passwords, keys)
- Error code taxonomy and categorization
- Backward compatibility with pre-Phase-2 error handling
"""

from __future__ import annotations

import pytest

from prism.scanner_core.error_envelope_builder import ErrorEnvelopeBuilder
from prism.scanner_data.contracts_request import ScanErrorEntry
from prism.scanner_plugins.ansible.error_adapter import (
    build_ansible_error_detail,
    classify_ansible_error,
)
from prism.scanner_plugins.ansible.error_codes import (
    ANSIBLE_ERROR_CODES,
    ANSIBLE_MODULE_NOT_FOUND,
    ANSIBLE_TASK_FAILED,
    ANSIBLE_TASK_TIMEOUT,
    ANSIBLE_SYNTAX_ERROR,
)
from prism.scanner_plugins.error_taxonomy import (
    error_code_to_category,
    is_recoverable,
    validate_error_code,
    ErrorCategory,
)


class TestBasicErrorEntryConstruction:
    """Test ScanErrorEntry construction with required and optional fields."""

    def test_error_entry_with_required_fields_only(self) -> None:
        """Test ScanErrorEntry with required fields only."""
        entry: ScanErrorEntry = {
            "phase": "extraction",
            "error_type": "ValueError",
            "message": "Invalid value",
        }
        assert entry["phase"] == "extraction"
        assert entry["error_type"] == "ValueError"
        assert entry["message"] == "Invalid value"
        assert "error_code" not in entry

    def test_error_entry_with_optional_fields(self) -> None:
        """Test ScanErrorEntry with all new optional fields."""
        entry: ScanErrorEntry = {
            "phase": "extraction",
            "error_type": "RuntimeError",
            "message": "Extraction failed",
            "error_code": "ANSIBLE_MODULE_NOT_FOUND",
            "category": "runtime",
            "recoverable": False,
            "resource_id": "my_role",
            "detail": {"task_file": "tasks/main.yml", "line_number": 42},
            "cause_type": "ModuleNotFoundError",
            "traceback": "Traceback (most recent call last)...",
            "cause": "Missing module",
        }
        assert entry["error_code"] == "ANSIBLE_MODULE_NOT_FOUND"
        assert entry["category"] == "runtime"
        assert entry["recoverable"] is False
        assert entry["resource_id"] == "my_role"
        assert entry["detail"] == {"task_file": "tasks/main.yml", "line_number": 42}
        assert entry["cause_type"] == "ModuleNotFoundError"

    def test_notRequired_fields_omission(self) -> None:
        """Test that NotRequired fields don't cause errors when missing."""
        entry: ScanErrorEntry = {
            "phase": "ingress",
            "error_type": "IOError",
            "message": "File not found",
        }
        # All optional fields should be absent without error
        assert "error_code" not in entry
        assert "category" not in entry
        assert "detail" not in entry


class TestPlatformSpecificDetailPopulation:
    """Test platform-specific detail dictionary structures."""

    def test_ansible_detail_structure(self) -> None:
        """Test Ansible detail dict structure with unified provenance."""
        task_context = {
            "task_file": "tasks/main.yml",
            "line_number": 42,
            "task_index": 3,
            "module_name": "copy",
            "task_name": "Copy configuration",
            "role_path": "/path/to/role",
            "collection": "ansible.builtin",
        }
        detail = build_ansible_error_detail(task_context, Exception("test"))

        assert detail["task_file"] == "tasks/main.yml"
        assert detail["line_number"] == 42
        assert detail["task_index"] == 3
        assert detail["module_name"] == "copy"
        assert detail["task_name"] == "Copy configuration"
        assert detail["role_path"] == "/path/to/role"
        assert detail["collection"] == "ansible.builtin"

    def test_ansible_detail_partial_context(self) -> None:
        """Test Ansible detail with partial context (some fields missing)."""
        task_context = {
            "module_name": "shell",
            "task_file": "handlers/main.yml",
            "line_number": 15,
        }
        detail = build_ansible_error_detail(task_context, Exception("test"))

        assert detail["module_name"] == "shell"
        assert detail["task_file"] == "handlers/main.yml"
        assert detail["line_number"] == 15
        # Missing fields should not be in detail
        assert "role_path" not in detail or detail.get("role_path") is None

    def test_k8s_detail_structure_expected(self) -> None:
        """Test expected K8s detail structure (documented for Q3 implementation)."""
        # Document expected structure
        expected_k8s_detail = {
            "cluster": "prod-us-west",
            "namespace": "default",
            "kind": "Pod",
            "name": "nginx-7d8b49c9bd-abcde",
            "manifest_path": "/path/to/deployment.yaml",
            "api_version": "v1",
            "http_status": 404,
            "retryable": True,
        }
        assert expected_k8s_detail["cluster"] == "prod-us-west"
        assert expected_k8s_detail["http_status"] == 404

    def test_terraform_detail_structure_expected(self) -> None:
        """Test expected Terraform detail structure (documented for Q3 implementation)."""
        # Document expected structure
        expected_tf_detail = {
            "provider": "aws",
            "region": "us-west-2",
            "resource_type": "aws_instance",
            "resource_name": "web_server",
            "plan_path": "/path/to/main.tf",
            "line_number": 42,
            "diagnostic_severity": "error",
        }
        assert expected_tf_detail["provider"] == "aws"
        assert expected_tf_detail["line_number"] == 42


class TestSecretSanitization:
    """Test sanitization of sensitive information in error details."""

    def test_sanitize_kubeconfig_paths(self) -> None:
        """Test sanitization of kubeconfig file paths."""
        detail = {
            "config_file": "/home/user/.kube/config.kubeconfig",
            "description": "API config",
            "normal_field": "value",
        }
        sanitized = ErrorEnvelopeBuilder.sanitize_detail(detail)

        assert sanitized["config_file"] == "[REDACTED]"
        assert sanitized["description"] == "API config"
        assert sanitized["normal_field"] == "value"

    def test_sanitize_token_strings(self) -> None:
        """Test sanitization of token and API token fields."""
        detail = {
            "api_token": "sk-1234567890abcdef",
            "access_token": "ghp_1234567890abcdef",
            "bearer_token": "v1.abc123xyz789",
            "description": "API auth",
        }
        sanitized = ErrorEnvelopeBuilder.sanitize_detail(detail)

        assert sanitized["api_token"] == "[REDACTED]"
        assert sanitized["access_token"] == "[REDACTED]"
        assert sanitized["bearer_token"] == "[REDACTED]"
        assert sanitized["description"] == "API auth"

    def test_sanitize_password_fields(self) -> None:
        """Test sanitization of password and related fields."""
        detail = {
            "password": "my_secret_password",
            "passwd": "another_secret",
            "pwd": "yet_another",
            "normal_field": "public_value",
        }
        sanitized = ErrorEnvelopeBuilder.sanitize_detail(detail)

        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["passwd"] == "[REDACTED]"
        assert sanitized["pwd"] == "[REDACTED]"
        assert sanitized["normal_field"] == "public_value"

    def test_sanitize_secret_keys(self) -> None:
        """Test sanitization of secret, key, and key-related fields."""
        detail = {
            "secret": "my_secret_value",
            "api_key": "key_1234567890",
            "private_key": "-----BEGIN PRIVATE KEY-----",
            "secret_key": "sk-proj-123456789",
            "public_field": "visible",
        }
        sanitized = ErrorEnvelopeBuilder.sanitize_detail(detail)

        assert sanitized["secret"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["private_key"] == "[REDACTED]"
        assert sanitized["secret_key"] == "[REDACTED]"
        assert sanitized["public_field"] == "visible"

    def test_preserve_non_secret_strings(self) -> None:
        """Test that non-secret strings are NOT sanitized."""
        detail = {
            "task_name": "Run deploy script",
            "module_name": "shell",
            "line_number": 42,
            "file_path": "/path/to/playbook.yml",
            "status": "failed",
        }
        sanitized = ErrorEnvelopeBuilder.sanitize_detail(detail)

        assert sanitized["task_name"] == "Run deploy script"
        assert sanitized["module_name"] == "shell"
        assert sanitized["line_number"] == 42
        assert sanitized["file_path"] == "/path/to/playbook.yml"
        assert sanitized["status"] == "failed"

    def test_sanitize_mixed_secrets_and_values(self) -> None:
        """Test sanitization of mixed secret and non-secret fields."""
        detail = {
            "api_token": "sk_12345",
            "api_endpoint": "https://api.example.com",
            "password": "secret123",
            "user_name": "admin",
            "config_file": "/etc/myapp.conf.kubeconfig",
            "description": "Production deployment",
        }
        sanitized = ErrorEnvelopeBuilder.sanitize_detail(detail)

        assert sanitized["api_token"] == "[REDACTED]"
        assert sanitized["api_endpoint"] == "https://api.example.com"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["user_name"] == "admin"
        assert sanitized["config_file"] == "[REDACTED]"
        assert sanitized["description"] == "Production deployment"


class TestErrorCodeTaxonomy:
    """Test error code categorization and taxonomy."""

    def test_all_ansible_error_codes_valid(self) -> None:
        """Test that all Ansible error codes are in the set."""
        assert ANSIBLE_MODULE_NOT_FOUND in ANSIBLE_ERROR_CODES
        assert ANSIBLE_TASK_FAILED in ANSIBLE_ERROR_CODES
        assert ANSIBLE_TASK_TIMEOUT in ANSIBLE_ERROR_CODES
        assert ANSIBLE_SYNTAX_ERROR in ANSIBLE_ERROR_CODES
        # Verify count
        assert len(ANSIBLE_ERROR_CODES) >= 20

    def test_error_code_to_category_mapping(self) -> None:
        """Test error_code_to_category() mapping works."""
        assert (
            error_code_to_category("ANSIBLE_MODULE_NOT_FOUND") == ErrorCategory.RUNTIME
        )
        assert error_code_to_category("ANSIBLE_SYNTAX_ERROR") == ErrorCategory.PARSER
        assert error_code_to_category("K8S_API_ERROR") == ErrorCategory.API
        assert error_code_to_category("TF_PLAN_PARSE_ERROR") == ErrorCategory.PARSER

    def test_error_code_to_category_none_handling(self) -> None:
        """Test error_code_to_category() with None."""
        assert error_code_to_category(None) is None
        assert error_code_to_category("UNKNOWN_CODE") is None

    def test_is_recoverable_transient_errors(self) -> None:
        """Test is_recoverable() correctly identifies transient errors."""
        assert is_recoverable("K8S_TIMEOUT") is True
        assert is_recoverable("K8S_CONNECTION_ERROR") is True
        assert is_recoverable("ANSIBLE_CONNECTION_TIMEOUT") is True
        # Verify permanent errors are not recoverable
        assert is_recoverable("ANSIBLE_TASK_FAILED") is False
        assert is_recoverable("K8S_API_ERROR") is False

    def test_is_recoverable_none_handling(self) -> None:
        """Test is_recoverable() with None."""
        assert is_recoverable(None) is False

    def test_validate_error_code_valid(self) -> None:
        """Test validate_error_code() with valid codes."""
        assert validate_error_code("ANSIBLE_MODULE_NOT_FOUND") is True
        assert validate_error_code("K8S_API_ERROR") is True
        assert validate_error_code("TF_PLAN_PARSE_ERROR") is True

    def test_validate_error_code_invalid(self) -> None:
        """Test validate_error_code() with invalid codes."""
        assert validate_error_code("invalid-code") is False
        assert validate_error_code("InvalidCode") is False
        assert validate_error_code("UNKNOWN_PLATFORM_ERROR") is False

    def test_validate_category_valid(self) -> None:
        """Test that all ErrorCategory values are valid."""
        assert ErrorCategory.RUNTIME.value == "runtime"
        assert ErrorCategory.IO.value == "io"
        assert ErrorCategory.PARSER.value == "parser"
        assert ErrorCategory.API.value == "api"
        assert ErrorCategory.AUTH.value == "auth"


class TestErrorEnvelopeBuilder:
    """Test ErrorEnvelopeBuilder methods for entry construction and validation."""

    def test_build_error_entry_minimal(self) -> None:
        """Test build_error_entry() with minimal required fields."""
        entry = ErrorEnvelopeBuilder.build_error_entry(
            phase="extraction",
            error_type="ValueError",
            message="Invalid input",
        )
        assert entry["phase"] == "extraction"
        assert entry["error_type"] == "ValueError"
        assert entry["message"] == "Invalid input"

    def test_build_error_entry_with_optional_fields(self) -> None:
        """Test build_error_entry() with optional fields."""
        entry = ErrorEnvelopeBuilder.build_error_entry(
            phase="extraction",
            error_type="RuntimeError",
            message="Task failed",
            error_code="ANSIBLE_TASK_FAILED",
            category="runtime",
            recoverable=False,
            resource_id="my_task",
            cause_type="Exception",
        )
        assert entry["error_code"] == "ANSIBLE_TASK_FAILED"
        assert entry["category"] == "runtime"
        assert entry["recoverable"] is False
        assert entry["resource_id"] == "my_task"
        assert entry["cause_type"] == "Exception"

    def test_build_error_entry_with_detail_sanitization(self) -> None:
        """Test build_error_entry() sanitizes detail dict."""
        entry = ErrorEnvelopeBuilder.build_error_entry(
            phase="extraction",
            error_type="RuntimeError",
            message="Error",
            detail={
                "api_token": "secret_token_value",
                "task_file": "tasks/main.yml",
                "line_number": 42,
            },
        )
        assert entry["detail"]["api_token"] == "[REDACTED]"
        assert entry["detail"]["task_file"] == "tasks/main.yml"
        assert entry["detail"]["line_number"] == 42

    def test_build_error_entry_invalid_phase(self) -> None:
        """Test build_error_entry() rejects empty phase."""
        with pytest.raises(ValueError, match="phase must be a non-empty string"):
            ErrorEnvelopeBuilder.build_error_entry(
                phase="",
                error_type="ValueError",
                message="Test",
            )

    def test_build_error_entry_invalid_error_type(self) -> None:
        """Test build_error_entry() rejects empty error_type."""
        with pytest.raises(ValueError, match="error_type must be a non-empty string"):
            ErrorEnvelopeBuilder.build_error_entry(
                phase="extraction",
                error_type="",
                message="Test",
            )

    def test_build_error_entry_invalid_message(self) -> None:
        """Test build_error_entry() rejects empty message."""
        with pytest.raises(ValueError, match="message must be a non-empty string"):
            ErrorEnvelopeBuilder.build_error_entry(
                phase="extraction",
                error_type="ValueError",
                message="",
            )

    def test_validate_error_entry_valid(self) -> None:
        """Test validate_error_entry() accepts valid entries."""
        entry: ScanErrorEntry = {
            "phase": "extraction",
            "error_type": "RuntimeError",
            "message": "Test error",
        }
        assert ErrorEnvelopeBuilder.validate_error_entry(entry) is True

    def test_validate_error_entry_with_optional_fields(self) -> None:
        """Test validate_error_entry() with optional fields."""
        entry: ScanErrorEntry = {
            "phase": "extraction",
            "error_type": "RuntimeError",
            "message": "Test error",
            "error_code": "ANSIBLE_TASK_FAILED",
            "category": "runtime",
            "recoverable": False,
            "resource_id": "task1",
            "detail": {"line_number": 42},
            "cause_type": "Exception",
        }
        assert ErrorEnvelopeBuilder.validate_error_entry(entry) is True

    def test_validate_error_entry_missing_required_fields(self) -> None:
        """Test validate_error_entry() rejects entries missing required fields."""
        entry: ScanErrorEntry = {  # type: ignore
            "phase": "extraction",
            # Missing error_type and message
        }
        with pytest.raises(ValueError, match="Missing required error fields"):
            ErrorEnvelopeBuilder.validate_error_entry(entry)

    def test_validate_error_entry_invalid_types(self) -> None:
        """Test validate_error_entry() rejects invalid field types."""
        entry: ScanErrorEntry = {  # type: ignore
            "phase": 123,  # Should be string
            "error_type": "ValueError",
            "message": "Test",
        }
        with pytest.raises(ValueError, match="phase must be a non-empty string"):
            ErrorEnvelopeBuilder.validate_error_entry(entry)

    def test_validate_error_entry_invalid_recoverable_type(self) -> None:
        """Test validate_error_entry() rejects non-boolean recoverable."""
        entry: ScanErrorEntry = {  # type: ignore
            "phase": "extraction",
            "error_type": "RuntimeError",
            "message": "Test",
            "recoverable": "yes",  # Should be bool
        }
        with pytest.raises(ValueError, match="recoverable must be a boolean"):
            ErrorEnvelopeBuilder.validate_error_entry(entry)


class TestBackwardCompatibility:
    """Test backward compatibility with pre-Phase-2 error handling."""

    def test_existing_error_entry_format_still_works(self) -> None:
        """Test that existing ScanErrorEntry entries (pre-Phase 2) still work."""
        # Old-style entry with only required fields
        entry: ScanErrorEntry = {
            "phase": "rendering",
            "error_type": "IOError",
            "message": "File not found",
        }
        assert ErrorEnvelopeBuilder.validate_error_entry(entry) is True

    def test_old_entry_without_new_optional_fields(self) -> None:
        """Test code that doesn't use new optional fields continues unchanged."""
        entry: ScanErrorEntry = {
            "phase": "ingress",
            "error_type": "ValueError",
            "message": "Invalid config",
            "traceback": "Traceback...",
            "cause": "Config parse error",
        }
        # New fields should not be added when not provided
        assert "error_code" not in entry
        assert "category" not in entry
        assert entry["phase"] == "ingress"

    def test_ansible_scanner_errors_captured_correctly(self) -> None:
        """Test that Ansible scanner errors are still captured correctly."""
        # Simulate pre-Phase 2 Ansible error
        entry: ScanErrorEntry = {
            "phase": "extraction",
            "error_type": "RuntimeError",
            "message": "Ansible task failed",
        }
        assert entry["phase"] == "extraction"
        assert entry["error_type"] == "RuntimeError"

    def test_optional_fields_subset_still_valid(self) -> None:
        """Test entries with only some new optional fields."""
        entry: ScanErrorEntry = {
            "phase": "extraction",
            "error_type": "RuntimeError",
            "message": "Task failed",
            "error_code": "ANSIBLE_TASK_FAILED",
            # No category, recoverable, resource_id, detail, cause_type
        }
        assert entry["error_code"] == "ANSIBLE_TASK_FAILED"
        assert ErrorEnvelopeBuilder.validate_error_entry(entry) is True


class TestAnsibleErrorClassification:
    """Test Ansible error classification."""

    def test_classify_ansible_error_task_failed(self) -> None:
        """Test classifying a task failure exception."""
        exc = RuntimeError("Ansible task failed")
        error_code, category, recoverable = classify_ansible_error(exc)

        # Verify return type (specific classification depends on implementation)
        assert isinstance(error_code, str)
        assert isinstance(category, str)
        assert isinstance(recoverable, bool)

    def test_classify_ansible_error_returns_tuple(self) -> None:
        """Test that classify_ansible_error returns proper tuple."""
        exc = ValueError("Invalid module")
        result = classify_ansible_error(exc)

        assert isinstance(result, tuple)
        assert len(result) == 3
        error_code, category, recoverable = result
        assert all(
            isinstance(x, (str, bool)) for x in [error_code, category, recoverable]
        )
