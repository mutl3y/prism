"""Scan result payload shaping helpers."""

from __future__ import annotations

from typing import Any

from prism.errors import normalize_metadata_warnings


def normalize_scan_role_payload_shape(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach stable public field names to the structured scan payload."""
    normalized = dict(payload)
    if "variables" not in normalized and "display_variables" in normalized:
        normalized["variables"] = normalized["display_variables"]
    if "requirements" not in normalized and "requirements_display" in normalized:
        normalized["requirements"] = normalized["requirements_display"]
    if (
        "default_filters" not in normalized
        and "undocumented_default_filters" in normalized
    ):
        normalized["default_filters"] = normalized["undocumented_default_filters"]
    metadata = normalized.get("metadata")
    warnings = normalize_metadata_warnings(
        metadata if isinstance(metadata, dict) else {}
    )
    if warnings:
        normalized["warnings"] = warnings
    return normalized
