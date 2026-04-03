"""Scanner README package - README rendering and styling utilities.

Current capability ownership:
- style guide parsing and heading normalization
- README section composition and merge behavior
- documentation insights and README-input parsing
- guide, notes, and variable rendering helpers
"""

from __future__ import annotations

from prism.scanner_readme.render import (
    DEFAULT_SECTION_SPECS,
    SCANNER_STATS_SECTION_IDS,
    render_readme,
    _append_scanner_report_section_if_enabled,
)
from prism.scanner_readme.style import (
    STYLE_SECTION_ALIASES,
    get_style_section_aliases_snapshot,
    detect_style_section_level,
    format_heading,
    normalize_style_heading,
    parse_style_readme,
    _refresh_policy_derived_state as _refresh_style_policy_derived_state,
)
from prism.scanner_readme.guide import (
    _render_guide_section_body,
    refresh_policy_derived_state as _refresh_guide_policy_derived_state,
)
from prism.scanner_readme.doc_insights import (
    build_doc_insights,
    parse_comma_values,
)

# Public wrappers for scanner facade imports; avoid cross-package private imports.
append_scanner_report_section_if_enabled = _append_scanner_report_section_if_enabled
render_guide_section_body = _render_guide_section_body


def refresh_policy_derived_state(policy: dict) -> None:
    """Refresh legacy README policy-derived defaults for compatibility callers."""

    _refresh_style_policy_derived_state(policy)
    _refresh_guide_policy_derived_state(policy)


__all__ = [
    "DEFAULT_SECTION_SPECS",
    "SCANNER_STATS_SECTION_IDS",
    "render_readme",
    "append_scanner_report_section_if_enabled",
    "render_guide_section_body",
    "STYLE_SECTION_ALIASES",
    "get_style_section_aliases_snapshot",
    "detect_style_section_level",
    "format_heading",
    "normalize_style_heading",
    "parse_style_readme",
    "refresh_policy_derived_state",
    "build_doc_insights",
    "parse_comma_values",
]


def __getattr__(name: str) -> object:
    """Enforce module public API at runtime.

    Prevents access to private symbols (prefixed with _) that are not in __all__.
    This reduces reliance on test-only architecture enforcement by making
    boundary violations raise AttributeError immediately at import/access time.
    """
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only public API in dir() and introspection."""
    return sorted(__all__)
