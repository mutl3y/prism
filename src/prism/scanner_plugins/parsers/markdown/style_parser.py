"""Markdown style-guide parsing — re-export shim.

Canonical implementations now live in scanner_config.style_parser.
This module re-exports them for backward compatibility with callers that
import via scanner_plugins.parsers.markdown.style_parser.
"""

from __future__ import annotations

from prism.scanner_config.style_parser import (
    build_section_title_stats,
    detect_style_section_level,
    parse_style_readme,
)
from prism.scanner_config.style_aliases import (
    get_default_style_section_aliases_snapshot,
)

__all__ = [
    "build_section_title_stats",
    "detect_style_section_level",
    "get_default_style_section_aliases_snapshot",
    "parse_style_readme",
]
