"""Extraction domain contracts for variable discovery and analysis results.

Focused on metadata produced by the variable extraction pipeline:
- Variable discovery results (variable_insights)
- YAML parsing failures recorded during extraction
"""

from __future__ import annotations

from typing import Any, TypedDict


class VariableAnalysisResults(TypedDict, total=False):
    """Typed variable analysis output from extraction domain.

    Contains only the results of variable discovery and YAML analysis,
    separated from render configuration, output options, and other domains.
    """

    variable_insights: list[dict[str, Any]]
    yaml_parse_failures: list[dict[str, object]]


__all__ = [
    "VariableAnalysisResults",
]
