"""Compatibility wrapper package for scanner transitional surfaces."""

from .render_compat import (
    append_scanner_report_section_if_enabled,
    compose_section_body,
    generated_merge_markers,
    render_guide_identity_sections,
    render_guide_section_body,
    render_readme_with_style_guide,
    resolve_ordered_style_sections,
    resolve_section_content_mode,
    strip_prior_generated_merge_block,
)

__all__ = [
    "append_scanner_report_section_if_enabled",
    "compose_section_body",
    "generated_merge_markers",
    "render_guide_identity_sections",
    "render_guide_section_body",
    "render_readme_with_style_guide",
    "resolve_ordered_style_sections",
    "resolve_section_content_mode",
    "strip_prior_generated_merge_block",
]
