"""Collection and plugin inventory contracts.

Domain-owned contracts for collection scanning results, plugin catalogs,
and plugin record payloads. Used by api.scan_collection and re-export-safe
through scanner_data.contracts public surface.
"""

from __future__ import annotations

from typing import TypedDict


class PluginExtraction(TypedDict):
    """Plugin extraction method and confidence metadata."""

    method: str
    ast_version: str | None
    fallback_used: bool


class PluginRecord(TypedDict, total=False):
    """Single plugin record within a plugin catalog.

    Uses total=False to allow optional fields like capability_hints and
    documentation_blocks to be conditionally present.
    """

    type: str
    name: str
    relative_path: str
    language: str
    symbols: list[str]
    summary: str
    doc_source: str
    confidence: str
    confidence_score: float
    extraction: PluginExtraction
    capability_hints: list[str]
    documentation_blocks: dict[str, str]


class PluginScanFailure(TypedDict):
    """Failure record when plugin scanning encounters an error.

    Captures the stage, error type, and context needed to report or recover
    from plugin catalog collection failures.
    """

    relative_path: str
    type: str
    category: str
    error_type: str
    error: str
    stage: str


class PluginCatalogSummary(TypedDict):
    """Summary statistics for a plugin catalog scan."""

    total_plugins: int
    types_present: list[str]
    files_scanned: int
    files_failed: int


class PluginCatalog(TypedDict):
    """Complete collection plugin catalog payload.

    Typed schema for plugin inventory results, conforming to canonical
    scanner_data.contracts surface. Returned by scan_collection_plugins()
    and included in CollectionScanResult.
    """

    schema_version: int
    summary: PluginCatalogSummary
    by_type: dict[str, list[PluginRecord]]
    failures: list[PluginScanFailure]


__all__ = [
    "PluginCatalog",
    "PluginCatalogSummary",
    "PluginExtraction",
    "PluginRecord",
    "PluginScanFailure",
]
