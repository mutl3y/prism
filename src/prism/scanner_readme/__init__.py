"""Scanner README package - README rendering and styling utilities."""

from __future__ import annotations

from .render import (
    DEFAULT_SECTION_SPECS,
    SCANNER_STATS_SECTION_IDS,
    render_readme,
    _append_scanner_report_section_if_enabled,
)
from .style import (
    STYLE_SECTION_ALIASES,
    detect_style_section_level,
    format_heading,
    normalize_style_heading,
    parse_style_readme,
    _refresh_policy_derived_state,
)
from .guide import (
    _render_guide_section_body,
)
from .doc_insights import (
    build_doc_insights,
    parse_comma_values,
)

# Public wrappers for scanner facade imports; avoid cross-package private imports.
append_scanner_report_section_if_enabled = _append_scanner_report_section_if_enabled
render_guide_section_body = _render_guide_section_body
refresh_policy_derived_state = _refresh_policy_derived_state

__all__ = [
    "DEFAULT_SECTION_SPECS",
    "SCANNER_STATS_SECTION_IDS",
    "render_readme",
    "append_scanner_report_section_if_enabled",
    "render_guide_section_body",
    "STYLE_SECTION_ALIASES",
    "detect_style_section_level",
    "format_heading",
    "normalize_style_heading",
    "parse_style_readme",
    "refresh_policy_derived_state",
    "build_doc_insights",
    "parse_comma_values",
]
