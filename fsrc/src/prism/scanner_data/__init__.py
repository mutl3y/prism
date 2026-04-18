"""Scanner data contracts, builders, and types."""

from __future__ import annotations

from typing import Any, TypedDict

from prism.scanner_data.contracts_request import (
    FeaturesContext,
    ScanContextPayload,
    ScanMetadata,
    ScanOptionsDict,
)
from prism.scanner_data.contracts_output import (
    AnnotationQualityCounters,
    FinalOutputPayload,
    NormalizedScannerReportMetadata,
    ReadmeSectionRenderInput,
    RunScanOutputPayload,
    ScannerCounters,
    ScannerReportIssueListRow,
    ScannerReportMetadata,
    ScannerReportSectionRenderInput,
    ScannerReportYamlParseFailureRow,
    SectionBodyRenderResult,
)
from prism.scanner_data.contracts_variables import ReferenceContext, VariableRow
from prism.scanner_data.builders import VariableRowBuilder


class FailureDetail(TypedDict, total=False):
    code: str
    message: str
    category: str


class FailurePolicyContract(TypedDict, total=False):
    strict_phase_failures: bool
    fail_on_unconstrained_dynamic_includes: bool
    fail_on_yaml_like_task_annotations: bool


class RoleScanResult(TypedDict, total=False):
    role_name: str
    payload: dict[str, Any]


class RepoScanResult(TypedDict, total=False):
    repo_url: str
    payload: dict[str, Any]


class CollectionScanResult(TypedDict, total=False):
    collection: dict[str, Any]
    summary: dict[str, Any]


class ReportRenderingMetadata(TypedDict, total=False):
    scanner_counters: dict[str, Any]
    variable_insights: list[dict[str, Any]]
    features: dict[str, Any]


class RunbookSidecarPayload(TypedDict):
    role_name: str
    metadata: ScanMetadata


class RunbookSidecarArgs(TypedDict):
    runbook_output: str | None
    runbook_csv_output: str | None
    role_name: str
    metadata: ScanMetadata


class ScanRenderPayload(TypedDict):
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]


class ScanBaseContext(TypedDict, total=False):
    rp: str
    role_name: str
    description: str
    marker_prefix: str
    variables: dict[str, Any]
    found: list[Any]
    metadata: ScanMetadata
    requirements_display: list[Any]


class ScanContext(TypedDict):
    display_variables: dict[str, Any]
    metadata: ScanMetadata


class ScanPhaseError(TypedDict):
    phase: str
    error_type: str
    message: str


class EmitScanOutputsArgs(TypedDict, total=False):
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


class ScanReportSidecarArgs(TypedDict, total=False):
    concise_readme: bool
    scanner_report_output: str | None
    out_path: str
    include_scanner_report_link: bool
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata
    dry_run: bool


class OutputConfiguration(TypedDict, total=False):
    concise_readme: bool
    include_scanner_report_link: bool
    scanner_report_relpath: str


class ScanPhaseStatus(TypedDict, total=False):
    scan_errors: list[ScanPhaseError]
    scan_degraded: bool


class StyleGuideConfig(TypedDict, total=False):
    path: str
    title_text: str
    title_style: str
    section_style: str
    section_level: int
    sections: list[dict[str, Any]]


class Variable(TypedDict, total=False):
    name: str
    type: str
    default: str
    description: str
    required: bool
    secret: bool


class VariableProvenance(TypedDict, total=False):
    source_file: str
    line: int | None
    confidence: float
    source_type: str


class VariableRowWithMeta(VariableRow, total=False):
    external_evidence: list[dict[str, Any]]
    precedence_category: str


class VariableAnalysisResults(TypedDict, total=False):
    display_variables: dict[str, Any]
    undocumented_default_filters: list[dict[str, Any]]
    metadata: dict[str, Any]


class ScanPayloadBuilder:
    """Compatibility payload builder for scanner_data public surface."""

    def __init__(self) -> None:
        self._payload: dict[str, Any] = {}
        self._metadata: ScanMetadata = {}

    def role_name(self, value: str) -> "ScanPayloadBuilder":
        self._payload["role_name"] = value
        return self

    def description(self, value: str) -> "ScanPayloadBuilder":
        self._payload["description"] = value
        return self

    def display_variables(self, value: dict[str, Any]) -> "ScanPayloadBuilder":
        self._payload["display_variables"] = value
        return self

    def requirements_display(self, value: list[Any]) -> "ScanPayloadBuilder":
        self._payload["requirements_display"] = value
        return self

    def undocumented_default_filters(
        self,
        value: list[Any],
    ) -> "ScanPayloadBuilder":
        self._payload["undocumented_default_filters"] = value
        return self

    def metadata(self, value: ScanMetadata) -> "ScanPayloadBuilder":
        self._metadata = value
        return self

    def build(self) -> RunScanOutputPayload:
        return {
            "role_name": str(self._payload.get("role_name") or ""),
            "description": str(self._payload.get("description") or ""),
            "display_variables": dict(self._payload.get("display_variables") or {}),
            "requirements_display": list(
                self._payload.get("requirements_display") or []
            ),
            "undocumented_default_filters": list(
                self._payload.get("undocumented_default_filters") or []
            ),
            "metadata": self._metadata,
        }


__all__ = [
    "AnnotationQualityCounters",
    "CollectionScanResult",
    "EmitScanOutputsArgs",
    "FailureDetail",
    "FailurePolicyContract",
    "FeaturesContext",
    "FinalOutputPayload",
    "NormalizedScannerReportMetadata",
    "OutputConfiguration",
    "ReadmeSectionRenderInput",
    "ReferenceContext",
    "RepoScanResult",
    "ReportRenderingMetadata",
    "RoleScanResult",
    "RunbookSidecarPayload",
    "RunbookSidecarArgs",
    "RunScanOutputPayload",
    "ScanPayloadBuilder",
    "ScanRenderPayload",
    "ScanBaseContext",
    "ScanContext",
    "ScanContextPayload",
    "ScanMetadata",
    "ScanOptionsDict",
    "ScanPhaseError",
    "ScanPhaseStatus",
    "ScanReportSidecarArgs",
    "ScannerCounters",
    "ScannerReportIssueListRow",
    "ScannerReportMetadata",
    "ScannerReportSectionRenderInput",
    "ScannerReportYamlParseFailureRow",
    "SectionBodyRenderResult",
    "StyleGuideConfig",
    "Variable",
    "VariableAnalysisResults",
    "VariableProvenance",
    "VariableRow",
    "VariableRowBuilder",
    "VariableRowWithMeta",
]


def __getattr__(name: str) -> object:
    """Enforce module public API at runtime."""
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only public API in dir() and introspection."""
    return sorted(__all__)
