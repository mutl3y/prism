"""scanner_kernel — Plugin routing and scan-phase orchestration engine.

Owns:
  - Plugin routing: selects and dispatches the correct scan plugin for a given target
  - Scan-phase orchestration: coordinates preflight, route, and runtime carrier phases
  - Blocker-fact translation: converts ScannerContext blocker facts into strict failures
    or non-strict warnings based on policy enforcement mode
  - repo_context and collection_context: scan target binding for role and collection scans

Does NOT own:
  - DI wiring or ScannerContext lifecycle (owned by scanner_core)
  - Plugin implementations (owned by scanner_plugins.*)
"""

from __future__ import annotations

from prism.scanner_kernel.orchestrator import (
    RoutePreflightRuntimeCarrier,
    orchestrate_scan_payload_with_selected_plugin,
    route_scan_payload_orchestration,
)

__all__ = [
    "RoutePreflightRuntimeCarrier",
    "orchestrate_scan_payload_with_selected_plugin",
    "route_scan_payload_orchestration",
]
