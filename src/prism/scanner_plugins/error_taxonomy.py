"""Shared error taxonomy for multi-platform scanner plugins.

Defines error categories and utility functions for mapping platform-specific
error codes to canonical taxonomy categories.
"""

from __future__ import annotations

from enum import Enum


class ErrorCategory(str, Enum):
    """Canonical error categories for all scanner platforms.

    - runtime: Execution errors (task failed, module error, API error)
    - io: File system or network I/O errors (read, write, timeout)
    - parser: Syntax or parsing errors (YAML, HCL, manifest malformed)
    - api: External API communication errors (auth, connectivity, quota)
    - auth: Authentication/authorization errors (credentials invalid, permission denied)
    """

    RUNTIME = "runtime"
    IO = "io"
    PARSER = "parser"
    API = "api"
    AUTH = "auth"


# Error code to category mapping
# Format: "PLATFORM_ERROR_CODE": ErrorCategory.CATEGORY
ERROR_CODE_CATEGORY_MAP: dict[str, ErrorCategory] = {
    # Kubernetes errors
    "K8S_API_ERROR": ErrorCategory.API,
    "K8S_AUTH_ERROR": ErrorCategory.AUTH,
    "K8S_MANIFEST_PARSE_ERROR": ErrorCategory.PARSER,
    "K8S_RESOURCE_NOT_FOUND": ErrorCategory.API,
    "K8S_TIMEOUT": ErrorCategory.IO,
    "K8S_CONNECTION_ERROR": ErrorCategory.IO,
    # Terraform errors
    "TF_PLAN_PARSE_ERROR": ErrorCategory.PARSER,
    "TF_PROVIDER_AUTH_ERROR": ErrorCategory.AUTH,
    "TF_API_ERROR": ErrorCategory.API,
    "TF_FILE_NOT_FOUND": ErrorCategory.IO,
    "TF_EXECUTION_ERROR": ErrorCategory.RUNTIME,
    # Ansible errors
    "ANSIBLE_MODULE_NOT_FOUND": ErrorCategory.RUNTIME,
    "ANSIBLE_TASK_FAILED": ErrorCategory.RUNTIME,
    "ANSIBLE_SYNTAX_ERROR": ErrorCategory.PARSER,
    "ANSIBLE_COLLECTION_NOT_FOUND": ErrorCategory.IO,
    "ANSIBLE_AUTH_ERROR": ErrorCategory.AUTH,
    "ANSIBLE_ROLE_FILE_NOT_FOUND": ErrorCategory.IO,
}

# Transient error codes (recoverable, may succeed on retry)
TRANSIENT_ERROR_CODES: frozenset[str] = frozenset(
    {
        "K8S_TIMEOUT",
        "K8S_CONNECTION_ERROR",
        "TF_TIMEOUT",
        "ANSIBLE_CONNECTION_TIMEOUT",
    }
)


def error_code_to_category(error_code: str | None) -> ErrorCategory | None:
    """Map an error code to its canonical category.

    Args:
        error_code: Platform error code (e.g., "K8S_API_ERROR")

    Returns:
        ErrorCategory if found, None otherwise
    """
    if error_code is None:
        return None
    return ERROR_CODE_CATEGORY_MAP.get(error_code)


def is_recoverable(error_code: str | None) -> bool:
    """Determine if an error code represents a recoverable (transient) failure.

    Args:
        error_code: Platform error code (e.g., "K8S_TIMEOUT")

    Returns:
        bool: True if transient, False otherwise
    """
    if error_code is None:
        return False
    return error_code in TRANSIENT_ERROR_CODES


def validate_error_code(error_code: str) -> bool:
    """Validate that an error code follows naming conventions.

    Valid codes are UPPER_SNAKE_CASE and in the taxonomy.

    Args:
        error_code: Error code to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not error_code:
        return False
    if not error_code.isupper() or not all(c.isalnum() or c == "_" for c in error_code):
        return False
    return error_code in ERROR_CODE_CATEGORY_MAP or error_code.startswith(
        ("K8S_", "TF_", "ANSIBLE_")
    )


def validate_category(category: str) -> bool:
    """Validate that a category is in the canonical taxonomy.

    Args:
        category: Error category to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        ErrorCategory(category)
        return True
    except ValueError:
        return False
