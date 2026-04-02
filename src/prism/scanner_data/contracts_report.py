"""Report domain contracts for scanner report rendering and analysis results.

Focused on metadata produced for scanner report rendering:
- Counter aggregations (ScannerCounters)
- Feature detection context
- YAML parse failure tracking
"""

from __future__ import annotations

from typing import Any, TypedDict


class ReportRenderingMetadata(TypedDict, total=False):
    """Typed metadata for scanner-report rendering operations.

    Contains only the fields needed for generating scanner reports,
    separated from variable analysis details and output configuration.
    """

    scanner_counters: dict[str, Any] | None
    features: dict[str, Any]
    yaml_parse_failures: list[dict[str, object]]


__all__ = [
    "ReportRenderingMetadata",
]
