"""Scanner core module: dependency injection and orchestrator wiring.

Current capability ownership:
- request normalization and scan context assembly
- DI container wiring for scanner orchestrators
- variable discovery orchestration and feature detection
- output orchestration handoff into rendering and emission layers

This module provides:
- DIContainer: Lightweight hand-crafted dependency injection for scanner orchestrators
- ScannerContext: Main orchestrator coordinating all scan phases
- VariableDiscovery: Variable discovery and analysis orchestrator
- OutputOrchestrator: Output rendering and emission orchestrator
- FeatureDetector: Feature detection and analysis orchestrator

**Composition Pattern (Normalized):**

All scanner_core modules use a consistent explicit-injection composition pattern:

1. **Orchestrator Classes** (ScannerContext, VariableDiscovery, OutputOrchestrator,
   FeatureDetector):
   - Receive DIContainer via __init__, store as self._di
   - All dependencies are injected explicitly
   - No inline construction of collaborators
   - Defined in scanner_core, created via DIContainer factory methods

2. **Dependency Flow**:
   - DIContainer creates and caches orchestrators (factory methods pattern)
   - Orchestrators store the DIContainer reference for accessing other services
   - All composition is explicitly configured before use

3. **Usage Pattern** (from execute_scan_with_context):
   ```python
   container = DIContainer(role_path, scan_options, scanner_context_wiring=...)
   context = container.factory_scanner_context()
   discovery = container.factory_variable_discovery()
   detector = container.factory_feature_detector()
   orchestrator = container.factory_output_orchestrator(output_path)
   ```

4. **Testing**:
   - DIContainer supports factory_overrides for test mocks
   - All composition is testable without filesystem I/O
   - See test_scanner_core_composition.py for composition validation

**Public API Guardrails:**
Only symbols in __all__ are considered public. Accessing private symbols (e.g.,
prefixed with _) will raise AttributeError at runtime. This enforces module boundaries
without relying solely on tests.

**Principle:**
No module in scanner_core should construct orchestrator collaborators inline.
All composition goes through explicit wiring (parameter injection) or the
DIContainer factory methods.
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
