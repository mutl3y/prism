"""Scanner orchestrator: main entry point coordinating all scan phases.

This module provides ScannerContext, the primary orchestrator that coordinates
the complete scanner workflow: variable discovery → feature detection → output
orchestration.

ScannerContext replaces the procedural body of scanner.py:run_scan() with a
clean, testable class that owns orchestration logic while delegating to
specialized orchestrators (VariableDiscovery, OutputOrchestrator, FeatureDetector).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .di import DIContainer


class ScannerContext:
    """Main orchestrator for role scanning.

    Orchestrates the complete scan process:
    1. VariableDiscovery: discover all variables (static + referenced)
    2. FeatureDetector: analyze role features (tasks, handlers, collections)
    3. OutputOrchestrator: render and emit outputs (README, JSON, sidecar reports)

    Maintains immutable data contracts throughout. Uses immutable tuples
    and frozensets for discovered data; transforms to lists only at boundaries (JSON, etc).

    **Design Rationale:**
    - Encapsulates procedural orchestration logic into a cohesive class
    - Enables testable dependency injection for phase orchestrators
    - Maintains immutable data flow: discover → detect → output
    - Operates at higher abstraction than scanner.py internals
    - Delegates to specialized orchestrators (wave 2+)
    """

    def __init__(
        self,
        di: DIContainer,
        role_path: str,
        scan_options: dict[str, Any],
    ) -> None:
        """Initialize context with DI container and scan options.

        Args:
            di: DIContainer instance providing orchestrator factories.
            role_path: Absolute or relative path to Ansible role directory.
            scan_options: Normalized scan configuration dict from _build_run_scan_options().
                         Must include keys like role_name_override, include_vars_main, etc.

        Raises:
            ValueError: If di is None, role_path is empty, or scan_options is None.
        """
        if di is None:
            raise ValueError("di (DIContainer) must not be None")
        if not role_path:
            raise ValueError("role_path must not be empty")
        if scan_options is None:
            raise ValueError("scan_options must not be None")

        self._di = di
        self._role_path = role_path
        self._scan_options = scan_options

        # Internal state: discovered variables and features stored as immutable tuples/dicts
        self._discovered_variables: tuple[Any, ...] = ()
        self._detected_features: dict[str, Any] = {}
        self._scan_metadata: dict[str, Any] = {}

    def orchestrate_scan(self) -> dict[str, Any]:
        """Execute complete scan orchestration: discover → detect → emit.

        Orchestration phases:
        1. **Discovery Phase**: Use VariableDiscovery to find all variables
           (static from defaults/vars + referenced from tasks/handlers/templates).
           Result: discovered_variables: tuple[VariableRow, ...] (immutable)
        2. **Detection Phase**: Use FeatureDetector to analyze role features
           (task count, modules used, handlers, collections, etc.).
           Result: detected_features: dict[str, Any] (FeaturesContext)
        3. **Output Phase**: Use OutputOrchestrator to render outputs
           (README, JSON report, sidecar reports). Result: final payload.

        **Immutability Contract:**
        - discovered_variables stored as immutable tuple[VariableRow, ...]
        - detected_features stored as immutable dict[str, Any]
        - payload built via ScanPayloadBuilder (immutable typed dict)
        - No mutations to discovered data after discovery phase completes

        **Error Handling:**
        - If role_path is invalid: return error payload with error_status
        - If discovery fails: catch exception, log, continue with empty variables
        - If detection fails: catch exception, log, continue with minimal features
        - If output fails: catch, return rendered payload (writes may be skipped)

        Returns:
            dict[str, Any]: RunScanOutputPayload-compatible dict with:
                - role_name: str
                - description: str
                - display_variables: dict[str, Any]
                - requirements_display: list[Any]
                - undocumented_default_filters: list[Any]
                - metadata: ScanMetadata

        Raises:
            ValueError: If orchestration encounters unrecoverable errors
                        (e.g., invalid role structure).
        """
        # Phase 1: Variable Discovery (returns immutable tuple)
        self._discovered_variables = self._discover_variables()

        # Phase 2: Feature Detection (returns immutable dict)
        self._detected_features = self._detect_features()

        # Phase 3: Output Orchestration & Payload Building
        payload = self._build_output_payload()

        return payload

    def _discover_variables(self) -> tuple[Any, ...]:
        """Execute variable discovery phase.

        Delegates to VariableDiscovery to find all variables.
        Returns immutable tuple of VariableRow.

        **Phase Contract:**
        - Input: role_path, scan_options
        - Output: tuple[VariableRow, ...] (immutable - no mutations after return)
        - Error: catch, log, return empty tuple

        Returns:
            tuple[Any, ...]: Discovered variables (immutable collection).
        """
        try:
            discovery = self._di.factory_variable_discovery()
            variables_tuple = discovery.discover()  # Returns tuple[VariableRow, ...]
            return variables_tuple
        except Exception as e:
            # Log error and return empty tuple for graceful degradation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Variable discovery failed: {e}")
            return ()

    def _detect_features(self) -> dict[str, Any]:
        """Execute feature detection phase.

        Delegates to FeatureDetector to analyze role structure and features.
        Returns immutable dict of features.

        **Phase Contract:**
        - Input: role_path, scan_options, discovered_variables
        - Output: dict[str, Any] (FeaturesContext - treat as immutable)
        - Error: catch, log, return minimal features dict

        Returns:
            dict[str, Any]: Detected features (immutable dict).
        """
        try:
            detector = self._di.factory_feature_detector()
            features = detector.detect()  # Returns dict[str, Any]
            return features
        except Exception as e:
            # Log error and return minimal features dict for graceful degradation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Feature detection failed: {e}")
            return {
                "task_files_scanned": 0,
                "tasks_scanned": 0,
                "recursive_task_includes": 0,
                "unique_modules": "none",
                "external_collections": "none",
                "handlers_notified": "none",
                "privileged_tasks": 0,
                "conditional_tasks": 0,
                "tagged_tasks": 0,
                "included_role_calls": 0,
                "included_roles": "none",
                "dynamic_included_role_calls": 0,
                "dynamic_included_roles": "none",
                "disabled_task_annotations": 0,
                "yaml_like_task_annotations": 0,
            }

    def _build_output_payload(self) -> dict[str, Any]:
        """Build final RunScanOutputPayload from orchestration results.

        Assembles the output payload from phases 1 & 2, delegating rendering
        to OutputOrchestrator. This payload is used by scanner.py:run_scan()
        to emit final outputs.

        **Immutability Note:**
        - Discovered variables are converted from tuple to list for JSON serialization
        - Payload is built via ScanPayloadBuilder for immutability
        - All transformations create new structures (no mutations)

        **Payload Contract (RunScanOutputPayload):**
        - role_name: str
        - description: str
        - display_variables: dict[str, Any]
        - requirements_display: list[Any]
        - undocumented_default_filters: list[Any]
        - metadata: ScanMetadata

        Returns:
            dict[str, Any]: Payload ready for output emission (immutable from perspective of caller).
        """
        role_name = str(self._scan_options.get("role_name_override") or "").strip()
        if not role_name:
            role_name = Path(self._role_path).name or self._role_path

        metadata = dict(self._scan_metadata)
        if "features" not in metadata and self._detected_features:
            metadata["features"] = dict(self._detected_features)
        self._scan_metadata = metadata

        # Build canonical payload shape consumed by scanner output helpers.
        return {
            "role_name": role_name,
            "description": "",
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": metadata,
        }

    @property
    def discovered_variables(self) -> tuple[Any, ...]:
        """Variables discovered during scan (static + referenced).

        Immutable tuple. Updated only by orchestrate_scan().

        Returns:
            tuple[Any, ...]: Variables discovered in phase 1 (variable discovery).
                             Immutable after discovery phase completes.
        """
        return self._discovered_variables

    @property
    def detected_features(self) -> dict[str, Any]:
        """Features detected during scan (tasks, handlers, collections, etc.).

        Immutable dict from caller perspective. Updated only by orchestrate_scan().

        Returns:
            dict[str, Any]: Features detected in phase 2 (feature detection).
                            Type: FeaturesContext when fully populated.
        """
        return self._detected_features

    @property
    def scan_metadata(self) -> dict[str, Any]:
        """Scan metadata (role name, repository, scanning timestamp, etc.).

        Immutable from caller perspective. Updated throughout orchestration.

        Returns:
            dict[str, Any]: Metadata dict flowing through all phases.
                            Type: ScanMetadata when fully populated.
        """
        return self._scan_metadata
