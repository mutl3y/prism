"""Scanner report rendering and counter helpers."""

from __future__ import annotations

from typing import Any, Callable, TypedDict, cast


PRECEDENCE_DEFAULTS_OVERRIDDEN_BY_VARS = "precedence_defaults_overridden_by_vars"
LEGACY_AMBIGUOUS_DEFAULTS_VARS_OVERRIDE = "ambiguous_defaults_vars_override"

# Explicit unresolved-noise categories used by downstream metric gates.
# Informational precedence categories must stay out of this set.
UNRESOLVED_NOISE_CATEGORY_KEYS = frozenset(
    {
        "unresolved_readme_documented_only",
        "unresolved_dynamic_include_vars",
        "unresolved_no_static_definition",
        "unresolved_other",
    }
)


class ScannerCounters(TypedDict):
    """Typed scanner counter payload used by report rendering and sidecars."""

    total_variables: int
    documented_variables: int
    undocumented_variables: int
    unresolved_variables: int
    unresolved_noise_variables: int
    ambiguous_variables: int
    secret_variables: int
    required_variables: int
    high_confidence_variables: int
    medium_confidence_variables: int
    low_confidence_variables: int
    total_default_filters: int
    undocumented_default_filters: int
    included_role_calls: int
    dynamic_included_role_calls: int
    disabled_task_annotations: int
    yaml_like_task_annotations: int
    yaml_parse_failures: int
    non_authoritative_test_evidence_variables: int
    non_authoritative_test_evidence_saturation_hits: int
    non_authoritative_test_evidence_budget_hits: int
    provenance_issue_categories: dict[str, int]


class ScannerReportMetadata(TypedDict, total=False):
    """Typed metadata contract consumed by scanner-report rendering helpers."""

    scanner_counters: ScannerCounters
    variable_insights: list[dict[str, Any]]
    features: dict[str, Any]
    yaml_parse_failures: list[dict[str, object]]


class ReadmeSectionRenderInput(TypedDict):
    """Typed contract for readme section rendering invocation inputs."""

    section_id: str
    role_name: str
    description: str
    variables: dict[str, Any]
    requirements: list[Any]
    default_filters: list[Any]
    metadata: ScannerReportMetadata


class ScannerReportIssueListRow(TypedDict):
    """Typed contract for scanner report issue-list row rendering."""

    name: str
    uncertainty_reason: str | None


class ScannerReportYamlParseFailureRow(TypedDict):
    """Typed contract for scanner report YAML parse-failure row rendering."""

    location: str
    error: str


class AnnotationQualityCounters(TypedDict):
    """Typed annotation-quality counter payload extracted from scan features."""

    disabled_task_annotations: int
    yaml_like_task_annotations: int


class ScannerReportSectionRenderInput(TypedDict):
    """Typed contract for scanner report section-title/body rendering."""

    title: str
    body: str


class NormalizedScannerReportMetadata(TypedDict):
    """Typed optional-field normalization result for scanner-report metadata."""

    scanner_counters: ScannerCounters | None
    variable_insights: list[dict[str, Any]]
    features: dict[str, Any]
    yaml_parse_failures: list[dict[str, object]]


class SectionBodyRenderResult(TypedDict):
    """Typed result of a readme section body renderer invocation."""

    body: str
    has_content: bool


ReadmeSectionBodyRenderer = Callable[
    [
        str,
        str,
        str,
        dict[str, Any],
        list[Any],
        list[Any],
        ScannerReportMetadata,
    ],
    str,
]


def build_readme_section_render_input(
    *,
    section_id: str,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[Any],
    metadata: ScannerReportMetadata,
) -> ReadmeSectionRenderInput:
    """Build typed readme-section render inputs for scanner report rendering."""
    return {
        "section_id": section_id,
        "role_name": role_name,
        "description": description,
        "variables": variables,
        "requirements": requirements,
        "default_filters": default_filters,
        "metadata": metadata,
    }


def build_scanner_report_issue_list_row(
    *, row: dict[str, Any]
) -> ScannerReportIssueListRow:
    """Build typed scanner report issue-list row payloads from raw insights."""
    reason_value = row.get("uncertainty_reason") or None
    return {
        "name": str(row["name"]),
        "uncertainty_reason": (str(reason_value) if reason_value is not None else None),
    }


def render_scanner_report_issue_list_row(
    *, row: ScannerReportIssueListRow, fallback_reason: str
) -> str:
    """Render one markdown row for unresolved/ambiguous issue lists."""
    reason = row["uncertainty_reason"] or fallback_reason
    return f"- `{row['name']}`: {reason}"


def build_scanner_report_yaml_parse_failure_row(
    *, row: dict[str, object]
) -> ScannerReportYamlParseFailureRow:
    """Build typed scanner report YAML parse-failure row payloads."""
    file_name = str(row.get("file") or "<unknown>")
    line = row.get("line")
    column = row.get("column")
    location = (
        f"{file_name}:{line}:{column}"
        if line is not None and column is not None
        else file_name
    )
    message = str(row.get("error") or "parse error")
    return {"location": location, "error": message}


def render_scanner_report_yaml_parse_failure_row(
    *, row: ScannerReportYamlParseFailureRow
) -> str:
    """Render one markdown row for YAML parse-failure lists."""
    return f"- `{row['location']}`: {row['error']}"


def build_scanner_report_section_render_input(
    *, title: str, body: str
) -> ScannerReportSectionRenderInput:
    """Build typed scanner report section-title/body payloads."""
    return {
        "title": title,
        "body": body,
    }


def render_scanner_report_section(*, row: ScannerReportSectionRenderInput) -> list[str]:
    """Render section heading/body lines for scanner report markdown."""
    return [
        row["title"],
        "-" * len(row["title"]),
        "",
        row["body"],
        "",
    ]


def normalize_section_body_render_result(raw: str) -> SectionBodyRenderResult:
    """Normalize a raw renderer result string into a typed result payload."""
    stripped = raw.strip()
    return {"body": stripped, "has_content": bool(stripped)}


def invoke_readme_section_renderer(
    render_input: ReadmeSectionRenderInput,
    renderer: ReadmeSectionBodyRenderer,
) -> SectionBodyRenderResult:
    """Invoke the section body renderer with typed inputs and normalize the result."""
    raw = renderer(
        render_input["section_id"],
        render_input["role_name"],
        render_input["description"],
        render_input["variables"],
        render_input["requirements"],
        render_input["default_filters"],
        render_input["metadata"],
    )
    return normalize_section_body_render_result(raw)


def coerce_optional_scanner_report_metadata_fields(
    metadata: ScannerReportMetadata,
) -> NormalizedScannerReportMetadata:
    """Coerce optional scanner-report metadata fields to stable typed containers."""
    raw_counters = metadata.get("scanner_counters")
    raw_variable_insights = metadata.get("variable_insights")
    raw_features = metadata.get("features")
    raw_parse_failures = metadata.get("yaml_parse_failures")

    return {
        "scanner_counters": (
            cast(ScannerCounters, raw_counters)
            if isinstance(raw_counters, dict)
            else None
        ),
        "variable_insights": (
            cast(list[dict[str, Any]], raw_variable_insights)
            if isinstance(raw_variable_insights, list)
            else []
        ),
        "features": (
            cast(dict[str, Any], raw_features) if isinstance(raw_features, dict) else {}
        ),
        "yaml_parse_failures": (
            cast(list[dict[str, object]], raw_parse_failures)
            if isinstance(raw_parse_failures, list)
            else []
        ),
    }


def _normalize_provenance_issue_category(category: str | None) -> str | None:
    """Map legacy category labels onto current stable labels."""
    if category == LEGACY_AMBIGUOUS_DEFAULTS_VARS_OVERRIDE:
        return PRECEDENCE_DEFAULTS_OVERRIDDEN_BY_VARS
    return category


def is_unresolved_noise_category(category: str | None) -> bool:
    """Return True when a category should contribute to unresolved-noise metrics."""
    normalized = _normalize_provenance_issue_category(category)
    return normalized in UNRESOLVED_NOISE_CATEGORY_KEYS


def classify_provenance_issue(row: dict[str, Any]) -> str | None:
    """Return a stable provenance category label for unresolved/ambiguous rows."""
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
        if "vars/main.yml" in reason and "precedence" in reason:
            return PRECEDENCE_DEFAULTS_OVERRIDDEN_BY_VARS
        if "include_vars" in reason:
            return "ambiguous_include_vars_sources"
        # Keep this bucket specific to set_fact-derived ambiguity.
        if "set_fact" in reason:
            return "ambiguous_set_fact_runtime"
        return "ambiguous_other"

    return None


def coerce_annotation_quality_counters_from_features(
    features: dict[str, Any],
) -> AnnotationQualityCounters:
    """Extract and coerce annotation-quality counters from scan features."""
    return {
        "disabled_task_annotations": int(
            features.get("disabled_task_annotations") or 0
        ),
        "yaml_like_task_annotations": int(
            features.get("yaml_like_task_annotations") or 0
        ),
    }


def extract_scanner_counters(
    variable_insights: list[dict[str, Any]],
    default_filters: list[dict[str, Any]],
    features: dict[str, Any] | None = None,
    parse_failures: list[dict[str, object]] | None = None,
) -> ScannerCounters:
    """Summarize scanner findings by certainty and variable category."""
    counters: ScannerCounters = {
        "total_variables": len(variable_insights),
        "documented_variables": 0,
        "undocumented_variables": 0,
        "unresolved_variables": 0,
        "unresolved_noise_variables": 0,
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
        "disabled_task_annotations": 0,
        "yaml_like_task_annotations": 0,
        "yaml_parse_failures": len(parse_failures or []),
        "non_authoritative_test_evidence_variables": 0,
        "non_authoritative_test_evidence_saturation_hits": 0,
        "non_authoritative_test_evidence_budget_hits": 0,
        "provenance_issue_categories": {
            "unresolved_readme_documented_only": 0,
            "unresolved_dynamic_include_vars": 0,
            "unresolved_no_static_definition": 0,
            "unresolved_other": 0,
            PRECEDENCE_DEFAULTS_OVERRIDDEN_BY_VARS: 0,
            LEGACY_AMBIGUOUS_DEFAULTS_VARS_OVERRIDE: 0,
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

        issue_category = _normalize_provenance_issue_category(
            classify_provenance_issue(row)
        )
        if issue_category:
            counters["provenance_issue_categories"].setdefault(issue_category, 0)
            counters["provenance_issue_categories"][issue_category] += 1
            # Backward-compat alias for downstream consumers; remove after migration.
            if issue_category == PRECEDENCE_DEFAULTS_OVERRIDDEN_BY_VARS:
                counters["provenance_issue_categories"].setdefault(
                    LEGACY_AMBIGUOUS_DEFAULTS_VARS_OVERRIDE,
                    0,
                )
                counters["provenance_issue_categories"][
                    LEGACY_AMBIGUOUS_DEFAULTS_VARS_OVERRIDE
                ] += 1
            if is_unresolved_noise_category(issue_category):
                counters["unresolved_noise_variables"] += 1

        confidence = float(row.get("provenance_confidence") or 0.0)
        if confidence >= 0.90:
            counters["high_confidence_variables"] += 1
        elif confidence >= 0.70:
            counters["medium_confidence_variables"] += 1
        else:
            counters["low_confidence_variables"] += 1

        test_evidence = row.get("non_authoritative_test_evidence")
        if isinstance(test_evidence, dict):
            counters["non_authoritative_test_evidence_variables"] += 1
            if bool(test_evidence.get("saturation_applied")):
                counters["non_authoritative_test_evidence_saturation_hits"] += 1
            if bool(test_evidence.get("scan_budget_hit")):
                counters["non_authoritative_test_evidence_budget_hits"] += 1

    features = features or {}
    counters["included_role_calls"] = int(features.get("included_role_calls") or 0)
    counters["dynamic_included_role_calls"] = int(
        features.get("dynamic_included_role_calls") or 0
    )
    annotation_quality = coerce_annotation_quality_counters_from_features(features)
    counters["disabled_task_annotations"] = annotation_quality[
        "disabled_task_annotations"
    ]
    counters["yaml_like_task_annotations"] = annotation_quality[
        "yaml_like_task_annotations"
    ]

    return counters


def build_scanner_report_markdown(
    *,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[Any],
    metadata: ScannerReportMetadata,
    render_section_body: ReadmeSectionBodyRenderer,
) -> str:
    """Render a scanner-focused markdown sidecar report."""
    normalized = coerce_optional_scanner_report_metadata_fields(metadata)
    counters = normalized["scanner_counters"] or extract_scanner_counters(
        normalized["variable_insights"],
        default_filters,
        normalized["features"],
        normalized["yaml_parse_failures"],
    )
    parse_failures = normalized["yaml_parse_failures"]
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
        f"- **Task annotation quality**: disabled={counters.get('disabled_task_annotations', 0)}, yaml_like={counters.get('yaml_like_task_annotations', 0)}",
        f"- **YAML parse failures**: {counters['yaml_parse_failures']}",
        (
            "- **Test-evidence telemetry**: "
            f"vars={counters.get('non_authoritative_test_evidence_variables', 0)}, "
            f"saturated={counters.get('non_authoritative_test_evidence_saturation_hits', 0)}, "
            f"budget_hits={counters.get('non_authoritative_test_evidence_budget_hits', 0)}"
        ),
    ]

    issue_categories = counters["provenance_issue_categories"]
    non_zero_categories = [
        (name, value) for name, value in issue_categories.items() if value
    ]
    if non_zero_categories:
        lines.append("- **Provenance issue categories**:")
        for name, value in non_zero_categories:
            lines.append(f"  - `{name}`: {value}")
    lines.append("")

    unresolved_rows = [
        row for row in normalized["variable_insights"] if row.get("is_unresolved")
    ]
    ambiguous_rows = [
        row for row in normalized["variable_insights"] if row.get("is_ambiguous")
    ]
    if unresolved_rows or ambiguous_rows:
        lines.extend(["Variable provenance issues", "--------------------------", ""])
        if unresolved_rows:
            lines.append("Unresolved variables:")
            for row in unresolved_rows:
                issue_row = build_scanner_report_issue_list_row(row=row)
                lines.append(
                    render_scanner_report_issue_list_row(
                        row=issue_row,
                        fallback_reason="Unknown source.",
                    )
                )
            lines.append("")

    if parse_failures:
        lines.extend(["YAML parse failures", "-------------------", ""])
        for item in parse_failures:
            parse_failure_row = build_scanner_report_yaml_parse_failure_row(
                row=item,
            )
            lines.append(
                render_scanner_report_yaml_parse_failure_row(
                    row=parse_failure_row,
                )
            )
        lines.append("")
        if ambiguous_rows:
            lines.append("Ambiguous variables:")
            for row in ambiguous_rows:
                issue_row = build_scanner_report_issue_list_row(row=row)
                lines.append(
                    render_scanner_report_issue_list_row(
                        row=issue_row,
                        fallback_reason="Multiple possible sources.",
                    )
                )
            lines.append("")

    sections = [
        ("task_summary", "Task/module usage summary"),
        ("role_contents", "Role contents summary"),
        ("features", "Auto-detected role features"),
        ("comparison", "Comparison against local baseline role"),
        ("default_filters", "Detected usages of the default() filter"),
    ]
    for section_id, title in sections:
        section_inputs = build_readme_section_render_input(
            section_id=section_id,
            role_name=role_name,
            description=description,
            variables=variables,
            requirements=requirements,
            default_filters=default_filters,
            metadata=metadata,
        )
        render_result = invoke_readme_section_renderer(
            render_input=section_inputs,
            renderer=render_section_body,
        )
        if not render_result["has_content"]:
            continue
        section_row = build_scanner_report_section_render_input(
            title=title,
            body=render_result["body"],
        )
        lines.extend(render_scanner_report_section(row=section_row))
    return "\n".join(lines).strip() + "\n"
