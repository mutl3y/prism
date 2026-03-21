"""Variable and notes rendering helpers for scanner style-guide output."""

from __future__ import annotations

import yaml

from ._task_parser import _format_inline_yaml


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
