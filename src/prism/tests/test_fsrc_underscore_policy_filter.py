"""Tests for underscore-reference policy filter extracted from ScannerContext."""

from __future__ import annotations

from typing import Any


def test_underscore_filter_noop_when_flag_disabled() -> None:
    from prism.scanner_plugins.filters.underscore_policy import (
        apply_underscore_reference_filter,
    )

    display_variables: dict[str, Any] = {
        "_internal": {"is_unresolved": True, "source": "tasks/main.yml"},
        "public_var": {"is_unresolved": False, "source": "defaults/main.yml"},
    }
    metadata: dict[str, Any] = {
        "variable_insights": [
            {"name": "_internal", "is_unresolved": True},
            {"name": "public_var", "is_unresolved": False},
        ],
    }

    result = apply_underscore_reference_filter(
        display_variables=display_variables,
        metadata=metadata,
        ignore_flag=False,
    )

    assert "_internal" in result
    assert "public_var" in result
    assert "ignore_unresolved_internal_underscore_references" not in metadata
    assert "underscore_filtered_unresolved_count" not in metadata


def test_underscore_filter_removes_unresolved_underscore_vars() -> None:
    from prism.scanner_plugins.filters.underscore_policy import (
        apply_underscore_reference_filter,
    )

    display_variables: dict[str, Any] = {
        "_internal": {"is_unresolved": True, "source": "tasks/main.yml"},
        "_resolved_internal": {"is_unresolved": False, "source": "defaults/main.yml"},
        "public_var": {"is_unresolved": True, "source": "tasks/main.yml"},
    }
    metadata: dict[str, Any] = {
        "variable_insights": [
            {"name": "_internal", "is_unresolved": True},
            {"name": "_resolved_internal", "is_unresolved": False},
            {"name": "public_var", "is_unresolved": True},
        ],
    }

    result = apply_underscore_reference_filter(
        display_variables=display_variables,
        metadata=metadata,
        ignore_flag=True,
    )

    assert "_internal" not in result
    assert "_resolved_internal" in result
    assert "public_var" in result
    assert metadata["ignore_unresolved_internal_underscore_references"] is True
    assert metadata["underscore_filtered_unresolved_count"] == 1
    assert len(metadata["variable_insights"]) == 2


def test_underscore_filter_no_matches_sets_flag_without_count() -> None:
    from prism.scanner_plugins.filters.underscore_policy import (
        apply_underscore_reference_filter,
    )

    display_variables: dict[str, Any] = {
        "public_var": {"is_unresolved": True, "source": "tasks/main.yml"},
    }
    metadata: dict[str, Any] = {
        "variable_insights": [
            {"name": "public_var", "is_unresolved": True},
        ],
    }

    result = apply_underscore_reference_filter(
        display_variables=display_variables,
        metadata=metadata,
        ignore_flag=True,
    )

    assert "public_var" in result
    assert metadata["ignore_unresolved_internal_underscore_references"] is True
    assert "underscore_filtered_unresolved_count" not in metadata
