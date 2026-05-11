"""Generic error envelope builder for platform-agnostic error construction.

Provides utilities for building, sanitizing, and validating error entries
across all scanner platforms (Ansible, Kubernetes, Terraform).
"""

from __future__ import annotations

import re
from typing import Any

from prism.scanner_data.contracts_request import ScanErrorEntry


class ErrorEnvelopeBuilder:
    """Generic builder utility for platform-agnostic error envelope construction.

    Handles error entry construction with optional platform-specific extensions,
    secret sanitization, and validation.
    """

    # Secret patterns for sanitization
    _SECRET_PATTERNS = [
        re.compile(r".*kubeconfig.*", re.IGNORECASE),
        re.compile(r".*(token|password|pwd|passwd|secret|key).*", re.IGNORECASE),
    ]

    @staticmethod
    def build_error_entry(
        phase: str,
        error_type: str,
        message: str,
        **kwargs: Any,
    ) -> ScanErrorEntry:
        """Build a ScanErrorEntry from required and optional fields.

        Args:
            phase: Execution phase (ingress, discovery, extraction, rendering)
            error_type: Exception class name
            message: Human-readable error message
            **kwargs: Optional fields (error_code, category, recoverable, resource_id,
                      detail, cause_type, traceback, cause)

        Returns:
            ScanErrorEntry with validated fields

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not phase or not isinstance(phase, str):
            raise ValueError("phase must be a non-empty string")
        if not error_type or not isinstance(error_type, str):
            raise ValueError("error_type must be a non-empty string")
        if not message or not isinstance(message, str):
            raise ValueError("message must be a non-empty string")

        entry: ScanErrorEntry = {
            "phase": phase,
            "error_type": error_type,
            "message": message,
        }

        # Add optional fields
        if "traceback" in kwargs and kwargs["traceback"] is not None:
            entry["traceback"] = kwargs["traceback"]
        if "cause" in kwargs and kwargs["cause"] is not None:
            entry["cause"] = kwargs["cause"]
        if "error_code" in kwargs and kwargs["error_code"] is not None:
            entry["error_code"] = kwargs["error_code"]
        if "category" in kwargs and kwargs["category"] is not None:
            entry["category"] = kwargs["category"]
        if "recoverable" in kwargs and kwargs["recoverable"] is not None:
            entry["recoverable"] = kwargs["recoverable"]
        if "resource_id" in kwargs and kwargs["resource_id"] is not None:
            entry["resource_id"] = kwargs["resource_id"]
        if "cause_type" in kwargs and kwargs["cause_type"] is not None:
            entry["cause_type"] = kwargs["cause_type"]

        # Sanitize detail if provided
        if "detail" in kwargs and kwargs["detail"] is not None:
            entry["detail"] = ErrorEnvelopeBuilder.sanitize_detail(kwargs["detail"])

        return entry

    @staticmethod
    def sanitize_detail(detail: dict[str, Any]) -> dict[str, Any]:
        """Sanitize error detail to remove sensitive information.

        Removes or redacts:
        - Keys and values containing kubeconfig paths
        - Keys and values containing tokens, passwords, secrets, keys

        Args:
            detail: Original error detail dictionary

        Returns:
            Sanitized copy of detail dictionary
        """
        if not isinstance(detail, dict):
            raise ValueError("detail must be a dictionary")

        sanitized = {}

        for key, value in detail.items():
            # Check if key matches secret patterns
            key_is_secret = any(
                pattern.match(key) for pattern in ErrorEnvelopeBuilder._SECRET_PATTERNS
            )
            if key_is_secret:
                sanitized[key] = "[REDACTED]"
                continue

            # Check if value is a string matching secret patterns
            if isinstance(value, str):
                value_matches_secret = any(
                    pattern.match(value)
                    for pattern in ErrorEnvelopeBuilder._SECRET_PATTERNS
                )
                if value_matches_secret:
                    sanitized[key] = "[REDACTED]"
                    continue

            # Keep the value as-is
            sanitized[key] = value

        return sanitized

    @staticmethod
    def validate_error_entry(entry: ScanErrorEntry) -> bool:
        """Validate a ScanErrorEntry for required fields and structure.

        Args:
            entry: Error entry to validate

        Returns:
            True if entry is valid

        Raises:
            ValueError: If entry is invalid
        """
        if not isinstance(entry, dict):
            raise ValueError("Error entry must be a dictionary")

        # Check required fields
        required = {"phase", "error_type", "message"}
        missing = required - set(entry.keys())
        if missing:
            raise ValueError(f"Missing required error fields: {missing}")

        # Validate required field types
        if not isinstance(entry.get("phase"), str) or not entry["phase"]:
            raise ValueError("phase must be a non-empty string")
        if not isinstance(entry.get("error_type"), str) or not entry["error_type"]:
            raise ValueError("error_type must be a non-empty string")
        if not isinstance(entry.get("message"), str) or not entry["message"]:
            raise ValueError("message must be a non-empty string")

        # Validate optional field types if present
        if "traceback" in entry and entry["traceback"] is not None:
            if not isinstance(entry["traceback"], str):
                raise ValueError("traceback must be a string")

        if "error_code" in entry and entry["error_code"] is not None:
            if not isinstance(entry["error_code"], str):
                raise ValueError("error_code must be a string")

        if "category" in entry and entry["category"] is not None:
            if not isinstance(entry["category"], str):
                raise ValueError("category must be a string")

        if "recoverable" in entry and entry["recoverable"] is not None:
            if not isinstance(entry["recoverable"], bool):
                raise ValueError("recoverable must be a boolean")

        if "resource_id" in entry and entry["resource_id"] is not None:
            if not isinstance(entry["resource_id"], str):
                raise ValueError("resource_id must be a string")

        if "detail" in entry and entry["detail"] is not None:
            if not isinstance(entry["detail"], dict):
                raise ValueError("detail must be a dictionary")

        if "cause_type" in entry and entry["cause_type"] is not None:
            if not isinstance(entry["cause_type"], str):
                raise ValueError("cause_type must be a string")

        return True
