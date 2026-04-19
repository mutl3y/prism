"""Plugin protocol contracts used by scanner plugin ownership seams."""

from __future__ import annotations

from typing import Any, Protocol, TypedDict

from prism.scanner_data import RunScanOutputPayload, VariableRow
from prism.scanner_data.contracts_request import (
    PreparedJinjaAnalysisPolicy,
    PreparedPolicyBundle,
    PreparedTaskLineParsingPolicy,
)


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


class ScanPipelinePreflightContext(TypedDict, total=False):
    """Typed preflight context contract emitted by scan-pipeline plugins."""

    plugin_name: str
    plugin_platform: str
    plugin_enabled: bool
    ansible_plugin_enabled: bool
    role_path: str


class ScanPipelinePlugin(Protocol):
    """Protocol for plugins that can alter scan pipeline context."""

    def process_scan_pipeline(
        self,
        scan_options: dict[str, Any],
        scan_context: dict[str, Any],
    ) -> ScanPipelinePreflightContext: ...


class CommentDrivenDocumentationPlugin(Protocol):
    """Protocol for comment-driven role note extraction."""

    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]: ...


class YAMLParsingPolicyPlugin(Protocol):
    """Protocol for YAML parsing/loading policy implementations."""

    def load_yaml_file(self, path: str | Any) -> object: ...

    def parse_yaml_candidate(
        self,
        candidate: str | Any,
        role_root: str | Any,
    ) -> dict[str, object] | None: ...


class JinjaAnalysisPolicyPlugin(Protocol):
    """Protocol for Jinja variable analysis policy implementations."""

    def collect_undeclared_jinja_variables(self, text: str) -> set[str]: ...


class PlatformParticipants(TypedDict, total=False):
    """Named execution participant instances provided by the platform after request-prep."""

    task_line_parsing: PreparedTaskLineParsingPolicy
    jinja_analysis: PreparedJinjaAnalysisPolicy


class PlatformExecutionBundle(TypedDict):
    """Typed contract for what a platform plugin produces after request-prep.

    Carries the assembled prepared_policy bundle for scanner_core ingress and
    the named participant instances so consumers can request collaborators
    through the generic contract without accessing Ansible-concrete types.
    """

    prepared_policy: PreparedPolicyBundle
    platform_participants: PlatformParticipants


class PlatformExecutionBundleProvider(Protocol):
    """Protocol for plugins that can produce a platform execution bundle."""

    def build_execution_bundle(
        self, scan_options: dict[str, Any]
    ) -> PlatformExecutionBundle: ...
