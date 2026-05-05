"""Underscore-reference filtering policy for the scanner_plugins layer.

Both ``scanner_plugins`` and ``scanner_core`` need this filter but neither
layer should import the other.  The implementation here depends only on
``scanner_data`` types, so it is safe to own in the plugin layer.
``scanner_core.filters.underscore_policy`` carries an identical copy for
use by ``ScannerContext`` without introducing a scanner_core→scanner_plugins
dependency in either direction.
"""

from __future__ import annotations

from prism.scanner_data.contracts_request import DisplayVariables, ScanMetadata


def apply_underscore_reference_filter(
    *,
    display_variables: DisplayVariables,
    metadata: ScanMetadata,
    ignore_flag: bool,
) -> DisplayVariables:
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


__all__ = ["apply_underscore_reference_filter"]
