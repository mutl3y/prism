"""Scanner report rendering and counter helpers."""

from __future__ import annotations

from typing import Callable


def classify_provenance_issue(row: dict) -> str | None:
    """Return a stable issue category label for unresolved/ambiguous rows."""
    reason = str(row.get("uncertainty_reason") or "").lower()
    source = str(row.get("source") or "").lower()

    if row.get("is_unresolved"):
        if "documented in readme" in reason or "readme" in source:
            return "unresolved_readme_documented_only"
        if "dynamic include_vars" in reason:
            return "unresolved_dynamic_include_vars"
        if "no static definition" in reason:
            return "unresolved_no_static_definition"
        return "unresolved_other"

    if row.get("is_ambiguous"):
        if "overridden by vars/main.yml precedence" in reason:
            return "ambiguous_defaults_vars_override"
        if "include_vars" in reason:
            return "ambiguous_include_vars_sources"
        if "set_fact" in reason or "runtime" in reason:
            return "ambiguous_set_fact_runtime"
        return "ambiguous_other"

    return None


def extract_scanner_counters(
    variable_insights: list[dict],
    default_filters: list[dict],
    features: dict | None = None,
    parse_failures: list[dict[str, object]] | None = None,
) -> dict[str, int | dict[str, int]]:
    """Summarize scanner findings by certainty and variable category."""
    counters = {
        "total_variables": len(variable_insights),
        "documented_variables": 0,
        "undocumented_variables": 0,
        "unresolved_variables": 0,
        "ambiguous_variables": 0,
        "secret_variables": 0,
        "required_variables": 0,
        "high_confidence_variables": 0,
        "medium_confidence_variables": 0,
        "low_confidence_variables": 0,
        "total_default_filters": len(default_filters),
        "undocumented_default_filters": len(default_filters),
        "included_role_calls": 0,
        "dynamic_included_role_calls": 0,
        "yaml_parse_failures": len(parse_failures or []),
        "provenance_issue_categories": {
            "unresolved_readme_documented_only": 0,
            "unresolved_dynamic_include_vars": 0,
            "unresolved_no_static_definition": 0,
            "unresolved_other": 0,
            "ambiguous_defaults_vars_override": 0,
            "ambiguous_include_vars_sources": 0,
            "ambiguous_set_fact_runtime": 0,
            "ambiguous_other": 0,
        },
    }

    for row in variable_insights:
        if row.get("documented"):
            counters["documented_variables"] += 1
        else:
            counters["undocumented_variables"] += 1
        if row.get("is_unresolved"):
            counters["unresolved_variables"] += 1
        if row.get("is_ambiguous"):
            counters["ambiguous_variables"] += 1
        if row.get("secret"):
            counters["secret_variables"] += 1
        if row.get("required"):
            counters["required_variables"] += 1

        issue_category = classify_provenance_issue(row)
        if issue_category:
            counters["provenance_issue_categories"][issue_category] += 1

        confidence = float(row.get("provenance_confidence") or 0.0)
        if confidence >= 0.90:
            counters["high_confidence_variables"] += 1
        elif confidence >= 0.70:
            counters["medium_confidence_variables"] += 1
        else:
            counters["low_confidence_variables"] += 1

    features = features or {}
    counters["included_role_calls"] = int(features.get("included_role_calls") or 0)
    counters["dynamic_included_role_calls"] = int(
        features.get("dynamic_included_role_calls") or 0
    )

    return counters


def build_scanner_report_markdown(
    *,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
    render_section_body: Callable[..., str],
) -> str:
    """Render a scanner-focused markdown sidecar report."""
    counters = metadata.get("scanner_counters") or extract_scanner_counters(
        metadata.get("variable_insights") or [],
        default_filters,
        metadata.get("features") or {},
        metadata.get("yaml_parse_failures") or [],
    )
    parse_failures = metadata.get("yaml_parse_failures") or []
    lines = [
        f"{role_name} scanner report",
        "=" * (len(role_name) + len(" scanner report")),
        "",
        description,
        "",
        "Summary",
        "-------",
        "",
        f"- **Total variables**: {counters['total_variables']} ({counters['documented_variables']} documented, {counters['undocumented_variables']} undocumented)",
        f"- **Unresolved**: {counters['unresolved_variables']} | **Ambiguous**: {counters['ambiguous_variables']} | **Required**: {counters['required_variables']} | **Secrets**: {counters['secret_variables']}",
        f"- **Confidence buckets**: high={counters['high_confidence_variables']}, medium={counters['medium_confidence_variables']}, low={counters['low_confidence_variables']}",
        f"- **Default filter findings**: {counters['undocumented_default_filters']} undocumented out of {counters['total_default_filters']} discovered",
        f"- **Role include graph signals**: static={counters['included_role_calls']}, dynamic={counters['dynamic_included_role_calls']}",
        f"- **YAML parse failures**: {counters['yaml_parse_failures']}",
    ]

    issue_categories = counters.get("provenance_issue_categories") or {}
    non_zero_categories = [
        (name, value) for name, value in issue_categories.items() if value
    ]
    if non_zero_categories:
        lines.append("- **Provenance issue categories**:")
        for name, value in non_zero_categories:
            lines.append(f"  - `{name}`: {value}")
    lines.append("")

    unresolved_rows = [
        row
        for row in (metadata.get("variable_insights") or [])
        if row.get("is_unresolved")
    ]
    ambiguous_rows = [
        row
        for row in (metadata.get("variable_insights") or [])
        if row.get("is_ambiguous")
    ]
    if unresolved_rows or ambiguous_rows:
        lines.extend(["Variable provenance issues", "-------------------------", ""])
        if unresolved_rows:
            lines.append("Unresolved variables:")
            for row in unresolved_rows:
                reason = row.get("uncertainty_reason") or "Unknown source."
                lines.append(f"- `{row['name']}`: {reason}")
            lines.append("")

    if parse_failures:
        lines.extend(["YAML parse failures", "-------------------", ""])
        for item in parse_failures:
            file_name = str(item.get("file") or "<unknown>")
            line = item.get("line")
            column = item.get("column")
            location = (
                f"{file_name}:{line}:{column}"
                if line is not None and column is not None
                else file_name
            )
            message = str(item.get("error") or "parse error")
            lines.append(f"- `{location}`: {message}")
        lines.append("")
        if ambiguous_rows:
            lines.append("Ambiguous variables:")
            for row in ambiguous_rows:
                reason = row.get("uncertainty_reason") or "Multiple possible sources."
                lines.append(f"- `{row['name']}`: {reason}")
            lines.append("")

    sections = [
        ("task_summary", "Task/module usage summary"),
        ("role_contents", "Role contents summary"),
        ("features", "Auto-detected role features"),
        ("comparison", "Comparison against local baseline role"),
        ("default_filters", "Detected usages of the default() filter"),
    ]
    for section_id, title in sections:
        body = render_section_body(
            section_id,
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        ).strip()
        if not body:
            continue
        lines.extend([title, "-" * len(title), "", body, ""])
    return "\n".join(lines).strip() + "\n"
