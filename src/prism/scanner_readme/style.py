"""Style parsing and formatting facade for the fsrc lane."""

from __future__ import annotations

from prism.scanner_readme.style_config import (
    STYLE_SECTION_ALIASES,
    get_style_section_aliases_snapshot,
    refresh_policy_derived_state,
    style_section_aliases_scope,
)
from prism.scanner_readme.style_formatter import format_heading, normalize_style_heading
from prism.scanner_plugins.parsers.markdown.style_parser import (
    build_section_title_stats,
    detect_style_section_level,
    parse_style_readme,
)

__all__ = [
    "STYLE_SECTION_ALIASES",
    "build_section_title_stats",
    "detect_style_section_level",
    "format_heading",
    "get_style_section_aliases_snapshot",
    "normalize_style_heading",
    "parse_style_readme",
    "refresh_policy_derived_state",
    "style_section_aliases_scope",
]
