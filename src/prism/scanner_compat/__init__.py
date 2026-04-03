"""Compatibility wrapper package for scanner transitional surfaces.

Current capability ownership:
- retained compatibility helpers for README/style-guide merge behavior
- transitional wrapper surfaces kept outside canonical scanner runtime flow
"""

from prism.scanner_compat.render_compat import (
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


def __getattr__(name: str) -> object:
    """Enforce module public API at runtime."""
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only public API in dir() and introspection."""
    return sorted(__all__)
