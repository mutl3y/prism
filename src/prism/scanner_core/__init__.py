"""Scanner core module: dependency injection and orchestrator wiring.

This module provides:
- DIContainer: Lightweight hand-crafted dependency injection for scanner orchestrators
- ScannerContext: Main orchestrator coordinating all scan phases
- VariableDiscovery: Variable discovery and analysis orchestrator
- OutputOrchestrator: Output rendering and emission orchestrator
- FeatureDetector: Feature detection and analysis orchestrator
"""

from __future__ import annotations

from .di import DIContainer
from .feature_detector import FeatureDetector
from .output_orchestrator import OutputOrchestrator
from .scan_context_builder import ScanContextBuilder
from .scanner_context import ScannerContext
from .variable_discovery import VariableDiscovery

__all__ = [
    "DIContainer",
    "FeatureDetector",
    "OutputOrchestrator",
    "ScanContextBuilder",
    "ScannerContext",
    "VariableDiscovery",
]
