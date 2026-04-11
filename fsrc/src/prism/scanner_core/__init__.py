"""Scanner core public surface for the fsrc lane."""

from __future__ import annotations

from prism.scanner_core.di import DIContainer
from prism.scanner_core.feature_detector import FeatureDetector
from prism.scanner_core.output_orchestrator import OutputOrchestrator
from prism.scanner_core.scan_context_builder import ScanContextBuilder
from prism.scanner_core.scanner_context import ScannerContext

__all__ = [
    "DIContainer",
    "FeatureDetector",
    "OutputOrchestrator",
    "ScanContextBuilder",
    "ScannerContext",
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
