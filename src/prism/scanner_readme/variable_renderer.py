"""Variable rendering for different markdown styles."""

from __future__ import annotations

import yaml

from prism.scanner_extract.task_parser import _format_inline_yaml


def is_role_local_variable_row(row: dict) -> bool:
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


def describe_variable(name: str, source: str) -> str:
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


def render_role_variables_table_style(
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
        description = describe_variable(
            name,
            str(row.get("source") or "defaults/main.yml"),
        )
        lines.append(f"| `{name}` | `{default}` | {description} |")
    return "\n".join(lines)


def render_role_variables_nested_bullets_style(
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
            f"  * Description: {describe_variable(row['name'], row['source'])}"
        )
    return "\n".join(lines)


def render_role_variables_yaml_block_style(
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


def render_role_variables_simple_list_style(
    variables: dict,
    variable_intro: str | None,
) -> str:
    """Render role variables as a simple key/value bullet list."""
    lines = [variable_intro or "The following variables are available:"]
    for name, value in variables.items():
        rendered = _format_inline_yaml(value).replace("`", "'")
        lines.append(f"- `{name}`: `{rendered}`")
    return "\n".join(lines)


def render_role_variables_for_style(variables: dict, metadata: dict) -> str:
    """Render role variables following the style guide's preferred format."""
    if not variables:
        return "No variables found."

    style_guide = metadata.get("style_guide") or {}
    variable_style = style_guide.get("variable_style", "simple_list")
    variable_intro = style_guide.get("variable_intro")
    variable_insights = metadata.get("variable_insights") or []
    local_rows = [row for row in variable_insights if is_role_local_variable_row(row)]
    external_context = metadata.get("external_vars_context") or {}
    has_external_context = bool(external_context.get("paths"))

    if variable_style == "table":
        return render_role_variables_table_style(
            variables=variables,
            local_rows=local_rows,
            variable_intro=variable_intro,
            has_external_context=has_external_context,
        )

    if variable_style == "nested_bullets":
        return render_role_variables_nested_bullets_style(
            variable_insights=variable_insights,
            local_rows=local_rows,
            variable_intro=variable_intro,
            has_external_context=has_external_context,
        )

    if variable_style == "yaml_block":
        return render_role_variables_yaml_block_style(
            variables=variables,
            variable_intro=variable_intro,
        )

    return render_role_variables_simple_list_style(variables, variable_intro)
