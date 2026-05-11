"""Ansible-specific error adapter for structured error envelope construction.

Provides functions to build Ansible error details with unified provenance
information (task file, line number, task index, etc.) and classify Ansible
exceptions into platform-specific error codes.
"""

from __future__ import annotations

from typing import Any

from prism.scanner_plugins.ansible.error_codes import (
    ANSIBLE_AUTH_ERROR,
    ANSIBLE_COLLECTION_NOT_FOUND,
    ANSIBLE_CONNECTION_ERROR,
    ANSIBLE_CONNECTION_TIMEOUT,
    ANSIBLE_LOOP_ERROR,
    ANSIBLE_MODULE_NOT_FOUND,
    ANSIBLE_PERMISSION_DENIED,
    ANSIBLE_ROLE_FILE_NOT_FOUND,
    ANSIBLE_SYNTAX_ERROR,
    ANSIBLE_TASK_FAILED,
    ANSIBLE_TASK_FILE_NOT_FOUND,
    ANSIBLE_TASK_TIMEOUT,
    ANSIBLE_VARIABLE_UNDEFINED,
    ANSIBLE_YAML_PARSE_ERROR,
)


def build_ansible_error_detail(
    task_context: dict[str, Any],
    exception: Exception,
) -> dict[str, Any]:
    """Build Ansible error detail with unified provenance information.

    Constructs a detail dictionary with Ansible-specific provenance fields
    that can be used in error envelopes for structured error handling and
    diagnostics.

    Args:
        task_context: Dictionary with task context information. Expected keys:
            - task_file: Relative path to task file from role root
            - line_number: Task start line number in the file
            - task_index: Task position in file (0-based)
            - task_name: Human-readable task name
            - module_name: Ansible module name (e.g., 'copy', 'template')
            - role_path: Absolute path to role directory
            - collection: Collection namespace (e.g., 'ansible.builtin')
        exception: The exception that occurred during task execution

    Returns:
        Dictionary with unified Ansible provenance structure:
        {
            "module_name": str,
            "task_name": str,
            "task_file": str,
            "line_number": int,
            "task_index": int,
            "role_path": str,
            "collection": str
        }
    """
    detail: dict[str, Any] = {}

    # Add provenance fields from task context
    if "module_name" in task_context:
        detail["module_name"] = task_context["module_name"]
    if "task_name" in task_context:
        detail["task_name"] = task_context["task_name"]
    if "task_file" in task_context:
        detail["task_file"] = task_context["task_file"]
    if "line_number" in task_context:
        detail["line_number"] = task_context["line_number"]
    if "task_index" in task_context:
        detail["task_index"] = task_context["task_index"]
    if "role_path" in task_context:
        detail["role_path"] = task_context["role_path"]
    if "collection" in task_context:
        detail["collection"] = task_context["collection"]

    return detail


def classify_ansible_error(
    exception: Exception,
) -> tuple[str, str, bool]:
    """Classify an Ansible exception into error code, category, and recoverability.

    Maps common Ansible exception types to structured error metadata for
    use in error envelope construction.

    Args:
        exception: The exception to classify

    Returns:
        Tuple of (error_code, category, recoverable):
        - error_code: Ansible-specific error code (e.g., ANSIBLE_MODULE_NOT_FOUND)
        - category: Error category (runtime, io, parser, api, auth)
        - recoverable: True if scan can continue despite this error
    """
    exception_type = type(exception).__name__
    exception_msg = str(exception).lower()

    # Authentication errors
    if exception_type in ("PermissionError", "OSError") and (
        "permission" in exception_msg or "access denied" in exception_msg
    ):
        return ANSIBLE_PERMISSION_DENIED, "auth", False

    if exception_type in ("ValueError", "RuntimeError") and (
        "credential" in exception_msg or "auth" in exception_msg
    ):
        return ANSIBLE_AUTH_ERROR, "auth", False

    # Connection errors
    if exception_type == "TimeoutError" or "timeout" in exception_msg:
        return ANSIBLE_CONNECTION_TIMEOUT, "api", True

    if exception_type in ("ConnectionError", "OSError") or (
        "connection" in exception_msg and "refused" in exception_msg
    ):
        return ANSIBLE_CONNECTION_ERROR, "api", True

    # File not found errors
    if exception_type == "FileNotFoundError":
        if "role" in exception_msg:
            return ANSIBLE_ROLE_FILE_NOT_FOUND, "io", False
        elif "task" in exception_msg:
            return ANSIBLE_TASK_FILE_NOT_FOUND, "io", False
        else:
            return ANSIBLE_ROLE_FILE_NOT_FOUND, "io", False

    # Module and collection errors
    if exception_type == "ImportError" or "import" in exception_msg:
        if "module" in exception_msg:
            return ANSIBLE_MODULE_NOT_FOUND, "runtime", False
        else:
            return ANSIBLE_COLLECTION_NOT_FOUND, "runtime", False

    if exception_type == "ModuleNotFoundError" or "module" in exception_msg:
        return ANSIBLE_MODULE_NOT_FOUND, "runtime", False

    # Parsing and syntax errors
    if exception_type in ("SyntaxError", "yaml.YAMLError"):
        if "yaml" in exception_msg or "parsing" in exception_msg:
            return ANSIBLE_YAML_PARSE_ERROR, "parser", False
        else:
            return ANSIBLE_SYNTAX_ERROR, "parser", False

    if exception_type == "ValueError" and (
        "syntax" in exception_msg or "parse" in exception_msg
    ):
        return ANSIBLE_SYNTAX_ERROR, "parser", False

    # Variable and fact errors
    if exception_type == "KeyError" and (
        "variable" in exception_msg or "undefined" in exception_msg
    ):
        return ANSIBLE_VARIABLE_UNDEFINED, "runtime", True

    if exception_type == "NameError" or (
        exception_type == "RuntimeError" and "undefined" in exception_msg
    ):
        return ANSIBLE_VARIABLE_UNDEFINED, "runtime", True

    # Task execution errors
    if exception_type in ("RuntimeError", "Exception"):
        if "timeout" in exception_msg:
            return ANSIBLE_TASK_TIMEOUT, "runtime", True
        elif "loop" in exception_msg or "iteration" in exception_msg:
            return ANSIBLE_LOOP_ERROR, "runtime", True
        else:
            return ANSIBLE_TASK_FAILED, "runtime", True

    # Default: generic task failure (recoverable)
    return ANSIBLE_TASK_FAILED, "runtime", True
