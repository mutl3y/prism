"""Notes and summary rendering for standard markdown sections."""

from __future__ import annotations


def render_role_notes_section(role_notes: dict | None) -> str:
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


def render_variable_uncertainty_notes(rows: list[dict]) -> str:
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


def render_variable_summary_section(metadata: dict) -> str:
    """Render table and notes for role-local variable insights."""
    variable_insights = metadata.get("variable_insights") or []
    local_rows = [row for row in variable_insights if _is_role_local_variable_row(row)]
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
    uncertainty_notes = render_variable_uncertainty_notes(local_rows)
    if uncertainty_notes:
        lines.extend(["", uncertainty_notes])
    return "\n".join(lines)


def render_template_overrides_section(metadata: dict) -> str:
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


# Helper function used internally by this module
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
