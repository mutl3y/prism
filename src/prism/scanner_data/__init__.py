"""Scanner data contracts, builders, and types.

This module consolidates all TypedDict data contracts used throughout the scanner
pipeline, providing a single source of truth for data structure definitions.
It also exports builder classes for fluent, type-safe construction of immutable data.

Current capability ownership:
- request, context, output, report, collection, error, and variable contracts
- payload and variable-row builder helpers
- canonical typed seam definitions shared across scanner and API boundaries

**Public API Guardrails:**
Only symbols in __all__ are considered public. Accessing private symbols (e.g.,
prefixed with _) will raise AttributeError at runtime. This enforces module boundaries
without relying solely on tests.
"""

from __future__ import annotations

from .contracts_output import ScanPayloadBuilder as ScanPayloadBuilder
from .contracts_variables import VariableRowBuilder as VariableRowBuilder
from .contracts import (
    AnnotationQualityCounters as AnnotationQualityCounters,
    CollectionScanResult as CollectionScanResult,
    EmitScanOutputsArgs as EmitScanOutputsArgs,
    FailureDetail as FailureDetail,
    FailurePolicyContract as FailurePolicyContract,
    FeaturesContext as FeaturesContext,
    FinalOutputPayload as FinalOutputPayload,
    NormalizedScannerReportMetadata as NormalizedScannerReportMetadata,
    OutputConfiguration as OutputConfiguration,
    ReadmeSectionRenderInput as ReadmeSectionRenderInput,
    ReferenceContext as ReferenceContext,
    RepoScanResult as RepoScanResult,
    ReportRenderingMetadata as ReportRenderingMetadata,
    RoleScanResult as RoleScanResult,
    RunbookSidecarPayload as RunbookSidecarPayload,
    RunbookSidecarArgs as RunbookSidecarArgs,
    RunScanOutputPayload as RunScanOutputPayload,
    ScanRenderPayload as ScanRenderPayload,
    ScanBaseContext as ScanBaseContext,
    ScanContext as ScanContext,
    ScanContextPayload as ScanContextPayload,
    ScanMetadata as ScanMetadata,
    ScanOptionsDict as ScanOptionsDict,
    ScanPhaseError as ScanPhaseError,
    ScanPhaseStatus as ScanPhaseStatus,
    ScanReportSidecarArgs as ScanReportSidecarArgs,
    ScannerCounters as ScannerCounters,
    ScannerReportIssueListRow as ScannerReportIssueListRow,
    ScannerReportMetadata as ScannerReportMetadata,
    ScannerReportSectionRenderInput as ScannerReportSectionRenderInput,
    ScannerReportYamlParseFailureRow as ScannerReportYamlParseFailureRow,
    SectionBodyRenderResult as SectionBodyRenderResult,
    StyleGuideConfig as StyleGuideConfig,
    Variable as Variable,
    VariableAnalysisResults as VariableAnalysisResults,
    VariableProvenance as VariableProvenance,
    VariableRow as VariableRow,
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
    """Enforce module public API at runtime.

    Prevents access to private symbols (prefixed with _) that are not in __all__.
    This reduces reliance on test-only architecture enforcement by making
    boundary violations raise AttributeError immediately at import/access time.
    """
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only public API in dir() and introspection."""
    return sorted(__all__)
