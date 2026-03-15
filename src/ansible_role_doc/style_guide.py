"""Style guide parsing and markdown heading helpers."""

from __future__ import annotations

from pathlib import Path
import re

from .pattern_config import load_pattern_config

_POLICY = load_pattern_config()
STYLE_SECTION_ALIASES: dict[str, str] = _POLICY["section_aliases"]


def normalize_style_heading(heading: str) -> str:
    """Normalize markdown heading text for style-guide matching."""
    normalized = re.sub(r"[^a-z0-9()]+", " ", heading.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def detect_style_section_level(lines: list[str]) -> int:
    """Detect the top-level section heading level used by a style guide."""
    in_fence = False
    fence_char = ""
    fence_len = 0
    atx_levels: set[int] = set()

    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        next_line = lines[index + 1].rstrip() if index + 1 < len(lines) else ""

        fence_match = re.match(r"^\s*([`~]{3,})", line)
        if fence_match:
            marker = fence_match.group(1)
            marker_char = marker[0]
            marker_len = len(marker)
            if not in_fence:
                in_fence = True
                fence_char = marker_char
                fence_len = marker_len
            elif marker_char == fence_char and marker_len >= fence_len:
                in_fence = False
                fence_char = ""
                fence_len = 0
            continue

        if in_fence:
            continue

        if re.match(r"^-+$", next_line):
            return 2

        atx_match = re.match(r"^(#{1,6})\s+", line)
        if not atx_match:
            continue
        level = len(atx_match.group(1))
        if level >= 2:
            atx_levels.add(level)

    if 2 in atx_levels:
        return 2
    if atx_levels:
        return min(atx_levels)
    return 2


def format_heading(text: str, level: int, style: str) -> str:
    """Format markdown headings using ATX or setext style."""
    if style == "atx":
        return f"{'#' * level} {text}"
    if level == 1:
        return f"{text}\n{'=' * len(text)}"
    if level == 2:
        return f"{text}\n{'-' * len(text)}"
    return f"{'#' * level} {text}"


def parse_style_readme(style_readme_path: str) -> dict:
    """Parse a README style guide into section order and heading styles."""
    text = Path(style_readme_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    section_level = detect_style_section_level(lines)
    sections: list[dict] = []
    title_text = ""
    title_style = "setext"
    section_style = "setext"

    i = 0
    current_section: dict | None = None
    in_fence = False
    fence_char = ""
    fence_len = 0
    while i < len(lines):
        line = lines[i].rstrip()
        next_line = lines[i + 1].rstrip() if i + 1 < len(lines) else ""

        fence_match = re.match(r"^\s*([`~]{3,})", line)
        if fence_match:
            marker = fence_match.group(1)
            marker_char = marker[0]
            marker_len = len(marker)
            if not in_fence:
                in_fence = True
                fence_char = marker_char
                fence_len = marker_len
            elif marker_char == fence_char and marker_len >= fence_len:
                in_fence = False
                fence_char = ""
                fence_len = 0
            if current_section is not None:
                current_section["body"].append(line)
            i += 1
            continue

        if in_fence:
            if current_section is not None:
                current_section["body"].append(line)
            i += 1
            continue

        atx_match = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if atx_match:
            level = len(atx_match.group(1))
            title = atx_match.group(2).strip()
            if level == 1:
                title_style = "atx"
                title_text = title
            elif level == section_level:
                section_style = "atx"
            if level == section_level:
                canonical = STYLE_SECTION_ALIASES.get(
                    normalize_style_heading(title), "unknown"
                )
                current_section = {
                    "id": canonical,
                    "title": title,
                    "body": [],
                    "level": level,
                }
                sections.append(current_section)
            i += 1
            continue

        if re.match(r"^=+$", next_line):
            title_style = "setext"
            if not title_text:
                title_text = line.strip()
            i += 2
            continue

        if re.match(r"^-+$", next_line):
            section_style = "setext"
            canonical = STYLE_SECTION_ALIASES.get(
                normalize_style_heading(line), "unknown"
            )
            current_section = {
                "id": canonical,
                "title": line.strip(),
                "body": [],
                "level": 2,
            }
            sections.append(current_section)
            i += 2
            continue

        if current_section is not None:
            current_section["body"].append(line)

        i += 1

    for section in sections:
        section["body"] = "\n".join(section.get("body", [])).strip()

    variable_section = next(
        (section for section in sections if section["id"] == "role_variables"), None
    )
    variable_style = "simple_list"
    variable_intro = None
    if variable_section:
        body = variable_section.get("body", "")
        if "```yaml" in body:
            variable_style = "yaml_block"
            intro_match = re.split(r"```yaml", body, maxsplit=1)
            intro = intro_match[0].strip() if intro_match else ""
            variable_intro = intro or None
        elif re.search(r"^\s*\|.*\|\s*$", body, flags=re.MULTILINE):
            variable_style = "table"
            intro_lines: list[str] = []
            for raw_line in body.splitlines():
                stripped = raw_line.strip()
                if stripped.startswith("|"):
                    break
                if stripped:
                    intro_lines.append(stripped)
            variable_intro = "\n".join(intro_lines) if intro_lines else None
        elif re.search(r"^\s*[*-]\s+`[^`]+`", body, flags=re.MULTILINE) and re.search(
            r"^\s*[*-]\s+Default:", body, flags=re.MULTILINE
        ):
            variable_style = "nested_bullets"
            intro_lines: list[str] = []
            for raw_line in body.splitlines():
                stripped = raw_line.strip()
                if not stripped:
                    if intro_lines:
                        break
                    continue
                if stripped.startswith(("*", "-", "|", "```", "~~~")):
                    break
                intro_lines.append(stripped)
            variable_intro = "\n".join(intro_lines) if intro_lines else None

    return {
        "path": str(Path(style_readme_path).resolve()),
        "title_text": title_text,
        "title_style": title_style,
        "section_style": section_style,
        "section_level": section_level,
        "sections": sections,
        "variable_style": variable_style,
        "variable_intro": variable_intro,
    }
