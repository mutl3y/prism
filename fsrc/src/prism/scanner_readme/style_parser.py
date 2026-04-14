"""Style guide parsing compatibility facade for the fsrc lane."""

from __future__ import annotations

from prism.scanner_plugins.parsers.markdown.style_parser import (
    build_section_title_stats as _build_section_title_stats,
)
from prism.scanner_plugins.parsers.markdown.style_parser import (
    detect_style_section_level as _detect_style_section_level,
)
from prism.scanner_plugins.parsers.markdown.style_parser import (
    parse_style_readme as _parse_style_readme,
)
from prism.scanner_readme.style_config import get_style_section_aliases_snapshot


def build_section_title_stats(sections: list[dict]) -> dict:
    """Compatibility wrapper for parser-owned section-title stats."""
    return _build_section_title_stats(sections)


def detect_style_section_level(lines: list[str]) -> int:
    """Compatibility wrapper for parser-owned heading-level detection."""
    return _detect_style_section_level(lines)


def parse_style_readme(
    style_readme_path: str,
    *,
    section_aliases: dict[str, str] | None = None,
) -> dict:
    """Compatibility wrapper for parser-owned markdown style parsing."""
    resolved_section_aliases = section_aliases
    if resolved_section_aliases is None:
        resolved_section_aliases = get_style_section_aliases_snapshot()

    return _parse_style_readme(
        style_readme_path,
        section_aliases=resolved_section_aliases,
    )


__all__ = [
    "build_section_title_stats",
    "detect_style_section_level",
    "parse_style_readme",
]
