"""Scanner analysis package - reporting, metrics, and runbook utilities.

Current capability ownership:
- scanner counters, uncertainty reasoning, and provenance issue shaping
- scanner report row builders and markdown rendering helpers
- runbook and runbook CSV generation
- collection dependency aggregation helpers
"""

from __future__ import annotations

from .metrics import (
    append_non_authoritative_test_evidence_uncertainty_reason,
    build_referenced_variable_uncertainty_reason,
    extract_scanner_counters,
)
from .report import (
    AnnotationQualityCounters,
    NormalizedScannerReportMetadata,
    ReadmeSectionBodyRenderer,
    ReadmeSectionRenderInput,
    ScannerCounters,
    ScannerReportIssueListRow,
    ScannerReportMetadata,
    ScannerReportSectionRenderInput,
    ScannerReportYamlParseFailureRow,
    SectionBodyRenderResult,
    build_readme_section_render_input,
    build_scanner_report_issue_list_row,
    build_scanner_report_markdown,
    build_scanner_report_section_render_input,
    build_scanner_report_yaml_parse_failure_row,
    classify_provenance_issue,
    coerce_annotation_quality_counters_from_features,
    coerce_optional_scanner_report_metadata_fields,
    invoke_readme_section_renderer,
    is_unresolved_noise_category,
    normalize_section_body_render_result,
    render_scanner_report_issue_list_row,
    render_scanner_report_section,
    render_scanner_report_yaml_parse_failure_row,
)
from .runbook import (
    build_runbook_rows,
    render_runbook,
    render_runbook_csv,
)

__all__ = [
    "append_non_authoritative_test_evidence_uncertainty_reason",
    "build_referenced_variable_uncertainty_reason",
    "extract_scanner_counters",
    "AnnotationQualityCounters",
    "NormalizedScannerReportMetadata",
    "ReadmeSectionBodyRenderer",
    "ReadmeSectionRenderInput",
    "ScannerCounters",
    "ScannerReportIssueListRow",
    "ScannerReportMetadata",
    "ScannerReportSectionRenderInput",
    "ScannerReportYamlParseFailureRow",
    "SectionBodyRenderResult",
    "build_readme_section_render_input",
    "build_scanner_report_issue_list_row",
    "build_scanner_report_markdown",
    "build_scanner_report_section_render_input",
    "build_scanner_report_yaml_parse_failure_row",
    "classify_provenance_issue",
    "coerce_annotation_quality_counters_from_features",
    "coerce_optional_scanner_report_metadata_fields",
    "invoke_readme_section_renderer",
    "is_unresolved_noise_category",
    "normalize_section_body_render_result",
    "render_scanner_report_issue_list_row",
    "render_scanner_report_section",
    "render_scanner_report_yaml_parse_failure_row",
    "build_runbook_rows",
    "render_runbook",
    "render_runbook_csv",
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
