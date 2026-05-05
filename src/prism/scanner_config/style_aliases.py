"""Shared style section alias definitions for fsrc style parsing seams."""

from __future__ import annotations


DEFAULT_STYLE_SECTION_ALIASES: dict[str, str] = {
    "galaxy info": "galaxy_info",
    "requirements": "requirements",
    "role purpose and capabilities": "purpose",
    "role notes": "role_notes",
    "inputs variables summary": "variable_summary",
    "task module usage summary": "task_summary",
    "inferred example usage": "example_usage",
    "role variables": "role_variables",
    "role contents summary": "role_contents",
    "auto detected role features": "features",
    "comparison against local baseline role": "comparison",
    "detected usages of the default() filter": "default_filters",
    "scanner report": "scanner_report",
}


def get_default_style_section_aliases_snapshot() -> dict[str, str]:
    """Return a copy of the default style section aliases."""
    return dict(DEFAULT_STYLE_SECTION_ALIASES)
