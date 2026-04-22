"""Scanner reporting package for fsrc sidecar and runbook renderers."""

from __future__ import annotations

from prism.scanner_reporting.report import (
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
    extract_scanner_counters,
    invoke_readme_section_renderer,
    is_unresolved_noise_category,
    normalize_section_body_render_result,
    render_scanner_report_issue_list_row,
    render_scanner_report_section,
    render_scanner_report_yaml_parse_failure_row,
)
from prism.scanner_reporting.runbook import (
    build_runbook_rows,
    render_runbook,
    render_runbook_csv,
)

__all__ = [
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
    "build_runbook_rows",
    "build_scanner_report_issue_list_row",
    "build_scanner_report_markdown",
    "build_scanner_report_section_render_input",
    "build_scanner_report_yaml_parse_failure_row",
    "classify_provenance_issue",
    "coerce_annotation_quality_counters_from_features",
    "coerce_optional_scanner_report_metadata_fields",
    "extract_scanner_counters",
    "invoke_readme_section_renderer",
    "is_unresolved_noise_category",
    "normalize_section_body_render_result",
    "render_runbook",
    "render_runbook_csv",
    "render_scanner_report_issue_list_row",
    "render_scanner_report_section",
    "render_scanner_report_yaml_parse_failure_row",
]


def __getattr__(name: str) -> object:
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(__all__)
