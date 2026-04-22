"""Scanner core public surface for the fsrc lane."""

from __future__ import annotations

from prism.scanner_core.di import DIContainer
from prism.scanner_core.feature_detector import FeatureDetector
from prism.scanner_core.scanner_context import (
    NonCollectionRunScanExecutionRequest,
    ScannerContext,
    build_non_collection_run_scan_execution_request,
)

__all__ = [
    "DIContainer",
    "FeatureDetector",
    "NonCollectionRunScanExecutionRequest",
    "ScannerContext",
    "build_non_collection_run_scan_execution_request",
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
