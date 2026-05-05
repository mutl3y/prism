"""scanner_core — DI wiring, execution context, and infrastructure primitives.

Owns:
  - DIContainer: dependency injection container and plugin registry wiring
  - ScannerContext: per-scan execution context lifecycle (creation, mutation, finalization)
  - VariableDiscovery: variable extraction coordination
  - FeatureDetector: per-task feature classification
  - EventBus: intra-scan event propagation
  - Telemetry, scan cache seam, path safety, and error boundary helpers

Does NOT own:
  - Scan orchestration or plugin routing (owned by scanner_kernel)
  - Plugin implementations (owned by scanner_plugins.*)
"""

from __future__ import annotations

from prism.scanner_core.di import DIContainer
from prism.scanner_core.feature_detector import FeatureDetector
from prism.scanner_core.scan_request import build_run_scan_options_canonical
from prism.scanner_core.scanner_context import (
    NonCollectionRunScanExecutionRequest,
    ScannerContext,
    build_non_collection_run_scan_execution_request,
)
from prism.scanner_core.variable_discovery import VariableDiscovery
from prism.scanner_core.scan_cache import ScanCacheBackend

__all__ = [
    "DIContainer",
    "FeatureDetector",
    "NonCollectionRunScanExecutionRequest",
    "ScanCacheBackend",
    "ScannerContext",
    "VariableDiscovery",
    "build_non_collection_run_scan_execution_request",
    "build_run_scan_options_canonical",
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
