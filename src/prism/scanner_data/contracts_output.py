"""Render, report, and output contracts owned by the output domain."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self, TypedDict

from .contracts_request import ScanMetadata


class ScanRenderPayload(TypedDict):
    """Render-stage payload shared by README, report, and primary output flows."""

    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]


class OutputConfiguration(TypedDict, total=False):
    """Output-specific configuration separated from scan metadata.

    Contains only configuration for output rendering and file emission,
    separate from scan configuration, variable analysis, and error tracking.
    """

    concise_readme: bool
    include_scanner_report_link: bool
    scanner_report_relpath: str


class RunScanOutputPayload(TypedDict):
    """Typed seam payload between run_scan orchestration and output rendering."""

    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata


class RunbookSidecarPayload(TypedDict):
    """Minimal runbook-stage payload containing only role identity and metadata."""

    role_name: str
    metadata: ScanMetadata


class EmitScanOutputsArgs(TypedDict):
    """Argument bundle for output emission to reduce argument-drift risk."""

    output: str
    output_format: str
    concise_readme: bool
    scanner_report_output: str | None
    include_scanner_report_link: bool
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata
    template: str | None
    dry_run: bool
    runbook_output: str | None
    runbook_csv_output: str | None


class ScanReportSidecarArgs(TypedDict):
    """Argument bundle for concise scanner-report sidecar emission."""

    concise_readme: bool
    scanner_report_output: str | None
    out_path: Path
    include_scanner_report_link: bool
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata
    dry_run: bool


class RunbookSidecarArgs(TypedDict):
    """Argument bundle for optional runbook emission."""

    runbook_output: str | None
    runbook_csv_output: str | None
    role_name: str
    metadata: ScanMetadata


class FinalOutputPayload(TypedDict):
    """Typed payload passed into final output rendering."""

    role_name: str
    description: str
    variables: dict[str, Any]
    requirements: list[Any]
    default_filters: list[dict[str, Any]]
    metadata: dict[str, Any]


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


class ScanPayloadBuilder:
    """Fluent builder for constructing immutable RunScanOutputPayload TypedDicts.

    Lives in this module because RunScanOutputPayload is defined here and
    builders should be co-located with the contracts they produce.
    """

    def __init__(self) -> None:
        self._payload: dict[str, Any] = {}

    def role_name(self, value: str) -> Self:
        self._payload["role_name"] = value
        return self

    def description(self, value: str) -> Self:
        self._payload["description"] = value
        return self

    def display_variables(self, value: dict[str, Any]) -> Self:
        self._payload["display_variables"] = value
        return self

    def requirements_display(self, value: list[Any]) -> Self:
        self._payload["requirements_display"] = value
        return self

    def undocumented_default_filters(self, value: list[Any]) -> Self:
        self._payload["undocumented_default_filters"] = value
        return self

    def metadata(self, value: ScanMetadata) -> Self:
        self._payload["metadata"] = value
        return self

    def build(self) -> RunScanOutputPayload:
        """Validate and return immutable RunScanOutputPayload TypedDict."""
        role_name = self._payload.get("role_name")
        if not role_name or not isinstance(role_name, str) or not role_name.strip():
            raise ValueError(
                "'role_name' is required and cannot be empty. " f"Got: {role_name!r}"
            )

        description = self._payload.get("description")
        if description is None or not isinstance(description, str):
            raise ValueError(
                "'description' is required and must be a string. "
                f"Got: {description!r}"
            )

        metadata = self._payload.get("metadata")
        if metadata is None or not isinstance(metadata, dict):
            raise ValueError(
                "'metadata' is required and must be a dict. " f"Got: {metadata!r}"
            )

        result: RunScanOutputPayload = {
            "role_name": role_name,
            "description": description,
            "display_variables": self._payload.get("display_variables", {}),
            "requirements_display": self._payload.get("requirements_display", []),
            "undocumented_default_filters": self._payload.get(
                "undocumented_default_filters", []
            ),
            "metadata": metadata,
        }
        return result


__all__ = [
    "AnnotationQualityCounters",
    "EmitScanOutputsArgs",
    "FinalOutputPayload",
    "NormalizedScannerReportMetadata",
    "OutputConfiguration",
    "ReadmeSectionRenderInput",
    "RunbookSidecarArgs",
    "RunbookSidecarPayload",
    "RunScanOutputPayload",
    "ScanPayloadBuilder",
    "ScanRenderPayload",
    "ScanReportSidecarArgs",
    "ScannerCounters",
    "ScannerReportIssueListRow",
    "ScannerReportMetadata",
    "ScannerReportSectionRenderInput",
    "ScannerReportYamlParseFailureRow",
    "SectionBodyRenderResult",
]
