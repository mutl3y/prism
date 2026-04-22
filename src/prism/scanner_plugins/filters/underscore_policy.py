"""Underscore-reference filtering policy — extracted from ScannerContext."""

from __future__ import annotations

from typing import Any


def apply_underscore_reference_filter(
    *,
    display_variables: dict[str, Any],
    metadata: dict[str, Any],
    ignore_flag: bool,
) -> dict[str, Any]:
    """Filter unresolved underscore-prefixed variables from display output.

    Mutates *metadata* in-place to record filtering provenance.
    Returns the (possibly filtered) display_variables dict.
    """
    if not ignore_flag:
        return display_variables

    metadata["ignore_unresolved_internal_underscore_references"] = True

    filtered = {
        name: data
        for name, data in display_variables.items()
        if not (
            isinstance(name, str)
            and name.startswith("_")
            and isinstance(data, dict)
            and bool(data.get("is_unresolved"))
        )
    }

    filtered_count = len(display_variables) - len(filtered)
    if filtered_count > 0:
        metadata["underscore_filtered_unresolved_count"] = filtered_count
        insights = metadata.get("variable_insights")
        if isinstance(insights, list):
            metadata["variable_insights"] = [
                row
                for row in insights
                if not (
                    isinstance(row, dict)
                    and isinstance(row.get("name"), str)
                    and str(row.get("name")).startswith("_")
                    and bool(row.get("is_unresolved"))
                )
            ]

    return filtered
