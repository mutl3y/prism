"""Scanner data contracts, builders, and types.

This module consolidates all TypedDict data contracts used throughout the scanner
pipeline, providing a single source of truth for data structure definitions.
It also exports builder classes for fluent, type-safe construction of immutable data.
"""

from .builders import ScanPayloadBuilder as ScanPayloadBuilder
from .builders import VariableRowBuilder as VariableRowBuilder
from .contracts import (
    AnnotationQualityCounters as AnnotationQualityCounters,
    EmitScanOutputsArgs as EmitScanOutputsArgs,
    FeaturesContext as FeaturesContext,
    FinalOutputPayload as FinalOutputPayload,
    ReadmeSectionRenderInput as ReadmeSectionRenderInput,
    ReferenceContext as ReferenceContext,
    RunbookSidecarArgs as RunbookSidecarArgs,
    RunScanOutputPayload as RunScanOutputPayload,
    ScanBaseContext as ScanBaseContext,
    ScanContext as ScanContext,
    ScanMetadata as ScanMetadata,
    ScanReportSidecarArgs as ScanReportSidecarArgs,
    ScannerCounters as ScannerCounters,
    ScannerReportIssueListRow as ScannerReportIssueListRow,
    ScannerReportMetadata as ScannerReportMetadata,
    ScannerReportSectionRenderInput as ScannerReportSectionRenderInput,
    ScannerReportYamlParseFailureRow as ScannerReportYamlParseFailureRow,
    SectionBodyRenderResult as SectionBodyRenderResult,
    StyleGuideConfig as StyleGuideConfig,
    Variable as Variable,
    VariableProvenance as VariableProvenance,
    VariableRow as VariableRow,
    VariableRowWithMeta as VariableRowWithMeta,
    _StyleSection as _StyleSection,
    _SectionTitleBucket as _SectionTitleBucket,
)

__all__ = [
    "AnnotationQualityCounters",
    "EmitScanOutputsArgs",
    "FeaturesContext",
    "FinalOutputPayload",
    "ReadmeSectionRenderInput",
    "ReferenceContext",
    "RunbookSidecarArgs",
    "RunScanOutputPayload",
    "ScanBaseContext",
    "ScanContext",
    "ScanMetadata",
    "ScanPayloadBuilder",
    "ScannerCounters",
    "ScannerReportIssueListRow",
    "ScannerReportMetadata",
    "ScannerReportSectionRenderInput",
    "ScannerReportYamlParseFailureRow",
    "SectionBodyRenderResult",
    "StyleGuideConfig",
    "Variable",
    "VariableProvenance",
    "VariableRow",
    "VariableRowBuilder",
    "VariableRowWithMeta",
    "ScanReportSidecarArgs",
]
