"""Scanner README package - README rendering and styling utilities."""

from __future__ import annotations

from prism.scanner_readme.render import (
    ALL_SECTION_IDS,
    DEFAULT_SECTION_SPECS,
    EXTRA_SECTION_IDS,
    SCANNER_STATS_SECTION_IDS,
    render_readme,
    append_scanner_report_section_if_enabled,
)
from prism.scanner_readme.style import (
    detect_style_section_level,
    format_heading,
    get_style_section_aliases_snapshot,
    normalize_style_heading,
    parse_style_readme,
    STYLE_SECTION_ALIASES,
    refresh_policy_derived_state as _refresh_style_policy_derived_state,
)
from prism.scanner_readme.guide import (
    render_guide_section_body,
)
from prism.scanner_readme.doc_insights import (
    build_doc_insights,
    parse_comma_values,
)


def refresh_policy_derived_state(policy: dict) -> None:
    """Refresh style alias state after scanner policy reloads."""
    _refresh_style_policy_derived_state(policy)


__all__ = [
    "ALL_SECTION_IDS",
    "DEFAULT_SECTION_SPECS",
    "EXTRA_SECTION_IDS",
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
