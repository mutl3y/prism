"""Curated public compatibility surface for scanner data contracts.

Domain-owned contracts live in dedicated modules so unrelated contract changes
do not converge in a single god-file. This module preserves the stable
import surface for existing consumers by re-exporting the curated public set.
"""

from .contracts_errors import (
    CollectionScanResult as CollectionScanResult,
    FailureDetail as FailureDetail,
    FailurePolicyContract as FailurePolicyContract,
    RepoScanResult as RepoScanResult,
    RoleScanResult as RoleScanResult,
    ScanPhaseStatus as ScanPhaseStatus,
)
from .contracts_extraction import (
    VariableAnalysisResults as VariableAnalysisResults,
)
from .contracts_output import (
    AnnotationQualityCounters as AnnotationQualityCounters,
    EmitScanOutputsArgs as EmitScanOutputsArgs,
    FinalOutputPayload as FinalOutputPayload,
    NormalizedScannerReportMetadata as NormalizedScannerReportMetadata,
    OutputConfiguration as OutputConfiguration,
    ReadmeSectionRenderInput as ReadmeSectionRenderInput,
    RunbookSidecarArgs as RunbookSidecarArgs,
    RunbookSidecarPayload as RunbookSidecarPayload,
    RunScanOutputPayload as RunScanOutputPayload,
    ScanPayloadBuilder as ScanPayloadBuilder,
    ScanRenderPayload as ScanRenderPayload,
    ScanReportSidecarArgs as ScanReportSidecarArgs,
    ScannerCounters as ScannerCounters,
    ScannerReportIssueListRow as ScannerReportIssueListRow,
    ScannerReportMetadata as ScannerReportMetadata,
    ScannerReportSectionRenderInput as ScannerReportSectionRenderInput,
    ScannerReportYamlParseFailureRow as ScannerReportYamlParseFailureRow,
    SectionBodyRenderResult as SectionBodyRenderResult,
)
from .contracts_report import (
    ReportRenderingMetadata as ReportRenderingMetadata,
)
from .contracts_request import (
    FeaturesContext as FeaturesContext,
    PolicyContext as PolicyContext,
    ScanBaseContext as ScanBaseContext,
    ScanContext as ScanContext,
    ScanContextPayload as ScanContextPayload,
    ScanMetadata as ScanMetadata,
    ScanOptionsDict as ScanOptionsDict,
    ScanPhaseError as ScanPhaseError,
    StyleGuideConfig as StyleGuideConfig,
    _SectionTitleBucket as _SectionTitleBucket,
    _StyleSection as _StyleSection,
)
from .contracts_variables import (
    ReferenceContext as ReferenceContext,
    Variable as Variable,
    VariableProvenance as VariableProvenance,
    VariableRow as VariableRow,
    VariableRowBuilder as VariableRowBuilder,
    VariableRowWithMeta as VariableRowWithMeta,
)


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
    "ScanPayloadBuilder",
    "SectionBodyRenderResult",
    "StyleGuideConfig",
    "Variable",
    "VariableAnalysisResults",
    "VariableProvenance",
    "VariableRow",
    "VariableRowBuilder",
    "VariableRowWithMeta",
    "_SectionTitleBucket",
    "_StyleSection",
]
