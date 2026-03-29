"""Style guide parsing, markdown heading, and variable rendering helpers."""

from __future__ import annotations

from pathlib import Path
import re
from typing import TypedDict

import yaml

from ..scanner_config.patterns import load_pattern_config
from ..scanner_extract.task_parser import _format_inline_yaml

_POLICY = load_pattern_config()
STYLE_SECTION_ALIASES: dict[str, str] = _POLICY["section_aliases"]


class _SectionTitleBucket(TypedDict):
    count: int
    known: bool
    titles: list[str]
    normalized_titles: list[str]


def _build_section_title_stats(sections: list[dict]) -> dict:
    """Summarize observed section titles for downstream pattern analysis."""
    by_section_id: dict[str, _SectionTitleBucket] = {}

    for section in sections:
        section_id = str(section.get("id") or "unknown")
        title = str(section.get("title") or "").strip()
        normalized_title = str(section.get("normalized_title") or "").strip()

        bucket = by_section_id.setdefault(
            section_id,
            {
                "count": 0,
                "known": section_id != "unknown",
                "titles": [],
                "normalized_titles": [],
            },
        )
        bucket["count"] = int(bucket["count"]) + 1

        if title and title not in bucket["titles"]:
            bucket["titles"].append(title)
        if normalized_title and normalized_title not in bucket["normalized_titles"]:
            bucket["normalized_titles"].append(normalized_title)

    known_sections = sum(
        int(stats["count"])
        for section_id, stats in by_section_id.items()
        if section_id != "unknown"
    )
    _unknown_bucket = by_section_id.get("unknown")
    unknown_sections = (
        int(_unknown_bucket["count"]) if _unknown_bucket is not None else 0
    )

    return {
        "total_sections": len(sections),
        "known_sections": known_sections,
        "unknown_sections": unknown_sections,
        "by_section_id": by_section_id,
    }


def normalize_style_heading(heading: str) -> str:
    """Normalize markdown heading text for style-guide matching."""
    # Strip markdown inline links so `[Title](#anchor)` normalizes like `Title`.
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
    normalized = re.sub(r"[^a-z0-9()]+", " ", cleaned.lower()).strip()
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
                normalized_title = normalize_style_heading(title)
                canonical = STYLE_SECTION_ALIASES.get(normalized_title, "unknown")
                current_section = {
                    "id": canonical,
                    "title": title,
                    "normalized_title": normalized_title,
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
            normalized_title = normalize_style_heading(line)
            canonical = STYLE_SECTION_ALIASES.get(normalized_title, "unknown")
            current_section = {
                "id": canonical,
                "title": line.strip(),
                "normalized_title": normalized_title,
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
            intro_lines_nb: list[str] = []
            for raw_line in body.splitlines():
                stripped = raw_line.strip()
                if not stripped:
                    if intro_lines_nb:
                        break
                    continue
                if stripped.startswith(("*", "-", "|", "```", "~~~")):
                    break
                intro_lines_nb.append(stripped)
            variable_intro = "\n".join(intro_lines_nb) if intro_lines_nb else None

    return {
        "path": str(Path(style_readme_path).resolve()),
        "title_text": title_text,
        "title_style": title_style,
        "section_style": section_style,
        "section_level": section_level,
        "sections": sections,
        "section_title_stats": _build_section_title_stats(sections),
        "variable_style": variable_style,
        "variable_intro": variable_intro,
    }


def _describe_variable(name: str, source: str) -> str:
    """Generate a lightweight variable description when no source prose exists."""
    lowered = name.lower()
    if lowered.endswith("_enabled"):
        return "Enable or disable related behavior."
    if "port" in lowered:
        return "Set the port value used by the role."
    if "package" in lowered:
        return "Configure the package name or package list used by the role."
    if "service" in lowered:
        return "Control the related service name or service state."
    if "path" in lowered or "file" in lowered:
        return "Override the file or path location used by the role."
    if "user" in lowered or "group" in lowered:
        return "Set the user or group-related value used by the role."
    return f"Configured from `{source}` and can be overridden for environment-specific behavior."


def _is_role_local_variable_row(row: dict) -> bool:
    """Return whether a variable insight row is role-local/static source truth."""
    source = str(row.get("source") or "")
    provenance_source = row.get("provenance_source_file")
    if source.startswith("seed:"):
        return False
    if source.startswith("README.md"):
        return False
    if provenance_source is None:
        return False
    provenance_value = str(provenance_source)
    if provenance_value.startswith("/"):
        return False
    return True


def _render_role_variables_for_style(variables: dict, metadata: dict) -> str:
    """Render role variables following the style guide's preferred format."""
    if not variables:
        return "No variables found."

    style_guide = metadata.get("style_guide") or {}
    variable_style = style_guide.get("variable_style", "simple_list")
    variable_intro = style_guide.get("variable_intro")
    variable_insights = metadata.get("variable_insights") or []
    local_rows = [row for row in variable_insights if _is_role_local_variable_row(row)]
    external_context = metadata.get("external_vars_context") or {}
    has_external_context = bool(external_context.get("paths"))

    if variable_style == "table":
        return _render_role_variables_table_style(
            variables=variables,
            local_rows=local_rows,
            variable_intro=variable_intro,
            has_external_context=has_external_context,
        )

    if variable_style == "nested_bullets":
        return _render_role_variables_nested_bullets_style(
            variable_insights=variable_insights,
            local_rows=local_rows,
            variable_intro=variable_intro,
            has_external_context=has_external_context,
        )

    if variable_style == "yaml_block":
        return _render_role_variables_yaml_block_style(
            variables=variables,
            variable_intro=variable_intro,
        )

    return _render_role_variables_simple_list_style(variables, variable_intro)


def _render_role_variables_table_style(
    *,
    variables: dict,
    local_rows: list[dict],
    variable_intro: str | None,
    has_external_context: bool,
) -> str:
    """Render role variables in markdown table style."""
    lines: list[str] = []
    if variable_intro:
        lines.extend([variable_intro, ""])
    if has_external_context:
        lines.extend(
            [
                "External variable context paths were provided as non-authoritative hints and are excluded from this role-source table.",
                "",
            ]
        )
    lines.extend(["| Name | Default | Description |", "| --- | --- | --- |"])
    source_by_name = {row.get("name"): row for row in local_rows if row.get("name")}
    for name, value in variables.items():
        row = source_by_name.get(name) or {}
        default = str(row.get("default") or _format_inline_yaml(value)).replace(
            "`", "'"
        )
        description = _describe_variable(
            name,
            str(row.get("source") or "defaults/main.yml"),
        )
        lines.append(f"| `{name}` | `{default}` | {description} |")
    return "\n".join(lines)


def _render_role_variables_nested_bullets_style(
    *,
    variable_insights: list[dict],
    local_rows: list[dict],
    variable_intro: str | None,
    has_external_context: bool,
) -> str:
    """Render role variables in nested bullet style."""
    lines: list[str] = []
    if variable_intro:
        lines.extend([variable_intro, ""])
    if has_external_context:
        lines.append(
            "External variable context paths were provided as non-authoritative hints and are excluded from this role-source list."
        )
        lines.append("")
    rows_for_display = local_rows or variable_insights
    for row in rows_for_display:
        default = _format_inline_yaml(row["default"]).replace("`", "'")
        lines.append(f"* `{row['name']}`")
        lines.append(f"  * Default: `{default}`")
        lines.append(
            f"  * Description: {_describe_variable(row['name'], row['source'])}"
        )
    return "\n".join(lines)


def _render_role_variables_yaml_block_style(
    *,
    variables: dict,
    variable_intro: str | None,
) -> str:
    """Render role variables in a YAML code block style."""
    intro = (
        variable_intro
        or "Available variables are listed below, along with default values (see `defaults/main.yml`):"
    )
    yaml_block = yaml.safe_dump(
        variables, sort_keys=False, default_flow_style=False
    ).strip()
    return f"{intro}\n\n```yaml\n{yaml_block}\n```"


def _render_role_variables_simple_list_style(
    variables: dict,
    variable_intro: str | None,
) -> str:
    """Render role variables as a simple key/value bullet list."""
    lines = [variable_intro or "The following variables are available:"]
    for name, value in variables.items():
        rendered = _format_inline_yaml(value).replace("`", "'")
        lines.append(f"- `{name}`: `{rendered}`")
    return "\n".join(lines)


def _render_role_notes_section(role_notes: dict | None) -> str:
    """Render comment-driven role notes in a readable markdown block."""
    notes = role_notes or {}
    warnings = notes.get("warnings") or []
    deprecations = notes.get("deprecations") or []
    general = notes.get("notes") or []
    additionals = notes.get("additionals") or []
    if not warnings and not deprecations and not general and not additionals:
        return "No role notes were found in comment annotations."

    lines: list[str] = []
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings)
    if deprecations:
        if lines:
            lines.append("")
        lines.append("Deprecations:")
        lines.extend(f"- {item}" for item in deprecations)
    if general:
        if lines:
            lines.append("")
        lines.append("Notes:")
        lines.extend(f"- {item}" for item in general)
    if additionals:
        if lines:
            lines.append("")
        lines.append("Additionals:")
        lines.extend(f"- {item}" for item in additionals)
    return "\n".join(lines)


def _render_variable_uncertainty_notes(rows: list[dict]) -> str:
    """Render unresolved/ambiguous variable provenance notes."""
    unresolved = [row for row in rows if row.get("is_unresolved")]
    ambiguous = [row for row in rows if row.get("is_ambiguous")]
    if not unresolved and not ambiguous:
        return ""

    lines = ["Variable provenance and confidence notes:", ""]
    if unresolved:
        lines.append("Unresolved variables:")
        for row in unresolved:
            reason = row.get("uncertainty_reason") or "Unknown source."
            lines.append(f"- `{row['name']}`: {reason}")
    if ambiguous:
        if unresolved:
            lines.append("")
        lines.append("Ambiguous variables:")
        for row in ambiguous:
            reason = row.get("uncertainty_reason") or "Multiple possible sources."
            lines.append(f"- `{row['name']}`: {reason}")
    return "\n".join(lines)


def _render_variable_summary_section(metadata: dict) -> str:
    """Render table and notes for role-local variable insights."""
    rows = metadata.get("variable_insights") or []
    local_rows = [row for row in rows if _is_role_local_variable_row(row)]
    if not local_rows:
        return "No variable insights available."

    lines = ["| Name | Type | Default | Source |", "| --- | --- | --- | --- |"]
    for row in local_rows:
        default = str(row["default"]).replace("`", "'")
        source = row["source"]
        if row.get("secret"):
            source = f"{source} (secret)"
        lines.append(f"| `{row['name']}` | {row['type']} | `{default}` | {source} |")

    external_context = metadata.get("external_vars_context") or {}
    if external_context.get("paths"):
        lines.extend(
            [
                "",
                "External variable context paths were used as non-authoritative hints and are not listed in the table above.",
            ]
        )
    uncertainty_notes = _render_variable_uncertainty_notes(local_rows)
    if uncertainty_notes:
        lines.extend(["", uncertainty_notes])
    return "\n".join(lines)


def _render_template_overrides_section(metadata: dict) -> str:
    """Render template override hints from variables and template files."""
    template_files = metadata.get("templates") or []
    variable_rows = metadata.get("variable_insights") or []
    template_vars = [
        row["name"]
        for row in variable_rows
        if isinstance(row.get("name"), str) and "template" in row["name"].lower()
    ]
    lines = [
        "Override template-related variables or point them at playbook-local templates when the built-in layout is not sufficient."
    ]
    if template_vars:
        lines.append("")
        lines.append("Likely template override variables:")
        lines.extend(f"- `{name}`" for name in template_vars[:8])
    if template_files:
        lines.append("")
        lines.append("Templates detected in this role:")
        lines.extend(f"- `{path}`" for path in template_files)
    return "\n".join(lines)
