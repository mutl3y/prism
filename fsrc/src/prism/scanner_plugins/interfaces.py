"""Plugin protocol contracts used by scanner plugin ownership seams."""

from __future__ import annotations

from typing import Any, Protocol

from prism.scanner_data import RunScanOutputPayload, VariableRow


class VariableDiscoveryPlugin(Protocol):
    """Protocol for variable-discovery plugin implementations."""

    def discover_static_variables(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> tuple[VariableRow, ...]: ...

    def discover_referenced_variables(
        self,
        role_path: str,
        options: dict[str, Any],
        readme_content: str | None = None,
    ) -> frozenset[str]: ...

    def resolve_unresolved_variables(
        self,
        static_names: frozenset[str],
        referenced: frozenset[str],
        options: dict[str, Any],
    ) -> dict[str, str]: ...


class FeatureDetectionPlugin(Protocol):
    """Protocol for feature-detection plugin implementations."""

    def detect_features(
        self, role_path: str, options: dict[str, Any]
    ) -> dict[str, Any]: ...

    def analyze_task_catalog(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> dict[str, Any]: ...


class OutputOrchestrationPlugin(Protocol):
    """Protocol for output-orchestration plugin implementations."""

    def orchestrate_output(
        self,
        scan_payload: RunScanOutputPayload,
        metadata: dict[str, Any],
        discovered_variables: list[VariableRow],
    ) -> RunScanOutputPayload: ...


class ScanPipelinePlugin(Protocol):
    """Protocol for plugins that can alter scan pipeline context."""

    def process_scan_pipeline(
        self,
        scan_options: dict[str, Any],
        scan_context: dict[str, Any],
    ) -> dict[str, Any]: ...


class CommentDrivenDocumentationPlugin(Protocol):
    """Protocol for comment-driven role note extraction."""

    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]: ...
