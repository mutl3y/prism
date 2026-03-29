"""Scanner README package - README rendering and styling utilities."""

from __future__ import annotations

from .render import (
    DEFAULT_SECTION_SPECS,
    SCANNER_STATS_SECTION_IDS,
    render_readme,
    _append_scanner_report_section_if_enabled,
    _compose_section_body,
    _generated_merge_markers,
    _render_readme_with_style_guide,
    _resolve_ordered_style_sections,
    _resolve_section_content_mode,
    _strip_prior_generated_merge_block,
)
from .style import (
    STYLE_SECTION_ALIASES,
    detect_style_section_level,
    format_heading,
    normalize_style_heading,
    parse_style_readme,
    _describe_variable,
    _is_role_local_variable_row,
    _render_role_notes_section,
    _render_role_variables_for_style,
    _render_template_overrides_section,
    _render_variable_summary_section,
    _render_variable_uncertainty_notes,
)
from .guide import (
    _render_guide_section_body,
    _render_guide_identity_sections,
)
from .doc_insights import (
    build_doc_insights,
    parse_comma_values,
)

__all__ = [
    "DEFAULT_SECTION_SPECS",
    "SCANNER_STATS_SECTION_IDS",
    "render_readme",
    "_append_scanner_report_section_if_enabled",
    "_compose_section_body",
    "_generated_merge_markers",
    "_render_readme_with_style_guide",
    "_resolve_ordered_style_sections",
    "_resolve_section_content_mode",
    "_strip_prior_generated_merge_block",
    "STYLE_SECTION_ALIASES",
    "detect_style_section_level",
    "format_heading",
    "normalize_style_heading",
    "parse_style_readme",
    "_describe_variable",
    "_is_role_local_variable_row",
    "_render_role_notes_section",
    "_render_role_variables_for_style",
    "_render_template_overrides_section",
    "_render_variable_summary_section",
    "_render_variable_uncertainty_notes",
    "_render_guide_section_body",
    "_render_guide_identity_sections",
    "build_doc_insights",
    "parse_comma_values",
]
