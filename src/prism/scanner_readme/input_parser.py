"""README input-variable parsing helpers.

This module owns README variable/input section parsing semantics used by scanner
variable enrichment.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from ..scanner_extract.variable_extractor import IGNORED_IDENTIFIERS
from .style import STYLE_SECTION_ALIASES, normalize_style_heading

MARKDOWN_VAR_BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
MARKDOWN_VAR_TABLE_RE = re.compile(r"^\|\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\|")
MARKDOWN_VAR_BULLET_RE = re.compile(
    r"^[-*+]\s+`?([A-Za-z_][A-Za-z0-9_]*)`?(?:\s|$|:|-)"
)
MARKDOWN_VAR_PROSE_CONTEXT_RE = re.compile(
    r"\b(variable|variables|set|define|configured|configure|default|defaults|override|overrides|use|documented)\b",
    flags=re.IGNORECASE,
)
MARKDOWN_VAR_NESTED_KEY_HINT_RE = re.compile(
    r"\b(attribute|attributes|key|keys|field|fields|dictionary|map|list item|sub-?key)\b",
    flags=re.IGNORECASE,
)


def is_readme_variable_section_heading(title: str) -> bool:
    """Return True when a heading likely describes role input variables."""
    normalized = normalize_style_heading(title)
    if not normalized:
        return False
    canonical = STYLE_SECTION_ALIASES.get(normalized)
    if canonical in {"role_variables", "variable_summary", "variable_guidance"}:
        return True
    return "variable" in normalized or "input" in normalized


def is_readme_variable_section_heading_with(
    title: str,
    *,
    normalize_heading: Callable[[str], str],
    section_aliases: dict[str, str],
) -> bool:
    """Return heading classification using caller-provided normalization state."""
    normalized = normalize_heading(title)
    if not normalized:
        return False
    canonical = section_aliases.get(normalized)
    if canonical in {"role_variables", "variable_summary", "variable_guidance"}:
        return True
    return "variable" in normalized or "input" in normalized


def _consume_fence_marker(
    *,
    line: str,
    in_fence: bool,
    fence_char: str,
    fence_len: int,
) -> tuple[bool, str, int, bool]:
    """Update fenced-code parsing state and indicate whether line was a marker."""
    fence_match = re.match(r"^\s*([`~]{3,})", line)
    if not fence_match:
        return in_fence, fence_char, fence_len, False
    marker = fence_match.group(1)
    marker_char = marker[0]
    marker_len = len(marker)
    if not in_fence:
        return True, marker_char, marker_len, True
    if marker_char == fence_char and marker_len >= fence_len:
        return False, "", 0, True
    return in_fence, fence_char, fence_len, True


def _resolve_variable_section_heading_state(line: str, next_line: str) -> bool | None:
    """Return variable-section state update from heading syntax, else ``None``."""
    atx_match = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
    if atx_match:
        level = len(atx_match.group(1))
        heading_text = atx_match.group(2).strip()
        if level <= 2:
            return is_readme_variable_section_heading(heading_text)
        heading_lower = heading_text.lower()
        if "variable" not in heading_lower and "parameter" not in heading_lower:
            return False
        return None
    if line.strip() and re.match(r"^[-=]{3,}\s*$", next_line):
        return is_readme_variable_section_heading(line.strip())
    return None


def extract_readme_variable_names_from_line(line: str) -> set[str]:
    """Extract variable names from one markdown line using supported patterns."""
    names: set[str] = set()
    stripped = line.strip()
    if not stripped:
        return names

    patterns: tuple[re.Pattern[str], ...]
    if stripped.startswith("|"):
        patterns = (MARKDOWN_VAR_TABLE_RE,)
    elif MARKDOWN_VAR_BULLET_RE.match(stripped):
        patterns = (MARKDOWN_VAR_BULLET_RE,)
    else:
        # Prose backticks are useful but noisy; require explicit variable guidance hints.
        if not MARKDOWN_VAR_PROSE_CONTEXT_RE.search(line):
            return names
        lowered_line = line.lower()
        if (
            MARKDOWN_VAR_NESTED_KEY_HINT_RE.search(line)
            and "variable" not in lowered_line
        ):
            return names
        patterns = (MARKDOWN_VAR_BACKTICK_RE,)

    for pattern in patterns:
        for match in pattern.findall(line):
            lowered = match.lower()
            if lowered in IGNORED_IDENTIFIERS:
                continue
            names.add(match)
    return names


def extract_readme_input_variables(text: str) -> set[str]:
    """Extract likely variable names from README variable/input sections."""
    if not text.strip():
        return set()

    names: set[str] = set()
    in_fence = False
    fence_char = ""
    fence_len = 0
    in_variable_section = False
    lines = text.splitlines()

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        next_line = lines[idx + 1].rstrip() if idx + 1 < len(lines) else ""

        (
            in_fence,
            fence_char,
            fence_len,
            fence_handled,
        ) = _consume_fence_marker(
            line=line,
            in_fence=in_fence,
            fence_char=fence_char,
            fence_len=fence_len,
        )
        if fence_handled:
            continue

        if in_fence:
            continue

        header_state = _resolve_variable_section_heading_state(line, next_line)
        if header_state is not None:
            in_variable_section = header_state
            continue

        if not in_variable_section:
            continue

        names.update(extract_readme_variable_names_from_line(line))

    return names


def collect_readme_input_variables(
    role_path: str, style_readme_path: str | None = None
) -> set[str]:
    """Extract README variable names, with fallback to style README path."""
    readme_path = Path(role_path) / "README.md"

    if readme_path.is_file():
        try:
            text = readme_path.read_text(encoding="utf-8")
            if text.strip():
                return extract_readme_input_variables(text)
        except OSError, UnicodeDecodeError:
            pass

    if style_readme_path:
        style_path = Path(style_readme_path)
        if style_path.is_file():
            try:
                text = style_path.read_text(encoding="utf-8")
                if text.strip():
                    return extract_readme_input_variables(text)
            except OSError, UnicodeDecodeError:
                pass

    return set()
