"""Minimal output contracts for fsrc output orchestration foundations."""

from __future__ import annotations

from typing import Any, TypedDict

from prism.scanner_data.contracts_request import ScanMetadata


class RunScanOutputPayload(TypedDict):
    """Typed seam payload between scan orchestration and output emission."""

    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata


class FinalOutputPayload(TypedDict):
    """Typed payload passed into final output rendering."""

    role_name: str
    description: str
    variables: dict[str, Any]
    requirements: list[Any]
    default_filters: list[dict[str, Any]]
    metadata: dict[str, Any]
    warnings: list[dict[str, Any]]


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


def validate_output_orchestrator_inputs(
    *,
    output_path: object,
    options: object,
) -> None:
    """Validate OutputOrchestrator constructor inputs."""
    if not isinstance(output_path, str) or not output_path.strip():
        raise ValueError(
            f"'output_path' must be a non-empty string. Got: {output_path!r}"
        )
    if not isinstance(options, dict):
        raise ValueError(f"'options' must be a dict. Got: {options!r}")

    output_format = options.get("output_format")
    if output_format is not None and not isinstance(output_format, str):
        raise ValueError(
            "'options.output_format' must be a string when provided. "
            f"Got: {output_format!r}"
        )

    for field_name in ("concise_readme", "include_scanner_report_link"):
        field_value = options.get(field_name)
        if field_value is not None and not isinstance(field_value, bool):
            raise ValueError(
                f"'options.{field_name}' must be a bool when provided. "
                f"Got: {field_value!r}"
            )

    for field_name in (
        "template",
        "scanner_report_output",
        "runbook_output",
        "runbook_csv_output",
    ):
        field_value = options.get(field_name)
        if field_value is not None and not isinstance(field_value, str):
            raise ValueError(
                f"'options.{field_name}' must be a string or None when provided. "
                f"Got: {field_value!r}"
            )


def validate_runbook_sidecar_inputs(
    *,
    md_path: object,
    csv_path: object,
    role_name: object,
    metadata: object,
) -> None:
    """Validate explicit runbook sidecar emission inputs."""
    for field_name, field_value in (("md_path", md_path), ("csv_path", csv_path)):
        if not isinstance(field_value, str):
            raise ValueError(f"'{field_name}' must be a string. Got: {field_value!r}")

    if not isinstance(role_name, str) or not role_name.strip():
        raise ValueError(f"'role_name' must be a non-empty string. Got: {role_name!r}")

    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError(f"'metadata' must be a dict or None. Got: {metadata!r}")


def validate_run_scan_output_payload(payload: object) -> RunScanOutputPayload:
    """Validate and normalize output payload shape."""
    if not isinstance(payload, dict):
        raise ValueError(
            "'payload' must be a RunScanOutputPayload-compatible dict. "
            f"Got: {payload!r}"
        )

    role_name = payload.get("role_name")
    if not role_name or not isinstance(role_name, str) or not role_name.strip():
        raise ValueError(
            "'role_name' is required and cannot be empty. " f"Got: {role_name!r}"
        )

    description = payload.get("description")
    if description is None or not isinstance(description, str):
        raise ValueError(
            "'description' is required and must be a string. " f"Got: {description!r}"
        )

    metadata = payload.get("metadata")
    if metadata is None or not isinstance(metadata, dict):
        raise ValueError(
            "'metadata' is required and must be a dict. " f"Got: {metadata!r}"
        )

    display_variables = payload.get("display_variables", {})
    if not isinstance(display_variables, dict):
        raise ValueError(
            "'display_variables' must be a dict when provided. "
            f"Got: {display_variables!r}"
        )

    requirements_display = payload.get("requirements_display", [])
    if not isinstance(requirements_display, list):
        raise ValueError(
            "'requirements_display' must be a list when provided. "
            f"Got: {requirements_display!r}"
        )

    undocumented_default_filters = payload.get("undocumented_default_filters", [])
    if not isinstance(undocumented_default_filters, list):
        raise ValueError(
            "'undocumented_default_filters' must be a list when provided. "
            f"Got: {undocumented_default_filters!r}"
        )

    return {
        "role_name": role_name,
        "description": description,
        "display_variables": display_variables,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "metadata": metadata,
    }


__all__ = [
    "AnnotationQualityCounters",
    "FinalOutputPayload",
    "NormalizedScannerReportMetadata",
    "ReadmeSectionRenderInput",
    "RunScanOutputPayload",
    "ScannerCounters",
    "ScannerReportIssueListRow",
    "ScannerReportMetadata",
    "ScannerReportSectionRenderInput",
    "ScannerReportYamlParseFailureRow",
    "SectionBodyRenderResult",
    "validate_output_orchestrator_inputs",
    "validate_run_scan_output_payload",
    "validate_runbook_sidecar_inputs",
]
