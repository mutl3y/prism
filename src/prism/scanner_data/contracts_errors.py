"""Error and public result contracts owned by API/runtime boundaries."""

from __future__ import annotations

from typing import Any, TypedDict

from prism.scanner_data.contracts_request import ScanMetadata, ScanPhaseError


class ScanPhaseStatus(TypedDict, total=False):
    """Phase-level scan status metadata separated from other concerns.

    Groups scan degradation flag and phase failure details, separate from
    variable analysis results, output configuration, and render hints.
    """

    scan_degraded: bool
    scan_errors: list[ScanPhaseError]


class FailurePolicyContract(TypedDict, total=False):
    """Request-scoped failure-policy envelope shared across runtime seams."""

    strict: bool


class FailureDetail(TypedDict, total=False):
    """Shared warning/failure detail format for role, collection, and repo scans."""

    code: str
    category: str
    message: str
    detail_code: str
    source: str
    cause_type: str
    traceback: str


class RoleScanResult(TypedDict, total=False):
    """Typed public role-scan envelope returned by prism.api.scan_role."""

    role_name: str
    description: str
    variables: dict[str, Any]
    requirements: list[Any]
    default_filters: list[Any]
    metadata: ScanMetadata
    warnings: list[FailureDetail]


class CollectionScanResult(TypedDict, total=False):
    """Typed public collection-scan envelope returned by prism.api.scan_collection."""

    collection: dict[str, Any]
    dependencies: dict[str, Any]
    plugin_catalog: dict[str, Any]
    roles: list[dict[str, Any]]
    failures: list[FailureDetail]
    summary: dict[str, Any]


class RepoScanResult(RoleScanResult, total=False):
    """Typed public repo-scan envelope returned by prism.api.scan_repo."""


__all__ = [
    "CollectionScanResult",
    "FailureDetail",
    "FailurePolicyContract",
    "RepoScanResult",
    "RoleScanResult",
    "ScanPhaseStatus",
]
