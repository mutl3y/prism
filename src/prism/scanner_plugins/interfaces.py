"""Plugin protocol contracts used by scanner plugin ownership seams."""

from __future__ import annotations

import pathlib
from typing import Any, Protocol, TypeAlias, TypedDict, runtime_checkable

from prism.scanner_data import RunScanOutputPayload, VariableRow
from prism.scanner_data.contracts_request import (
    FeaturesContext,
    PreparedJinjaAnalysisPolicy,
    PreparedPolicyBundle,
    PreparedTaskLineParsingPolicy,
    ScanMetadata,
    ScanOptionsDict,
    YamlParseFailure,
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


class TaskCatalogEntry(TypedDict):
    """Per-file task catalog summary emitted by feature detection."""

    task_count: int
    async_count: int
    modules_used: list[str]
    collections_used: list[str]
    handlers_notified: list[str]
    privileged_tasks: int
    conditional_tasks: int
    tagged_tasks: int


TaskCatalog: TypeAlias = dict[str, TaskCatalogEntry]


class FeatureDetectionPlugin(Protocol):
    """Protocol for feature-detection plugin implementations."""

    def detect_features(
        self, role_path: str, options: dict[str, Any]
    ) -> FeaturesContext: ...

    def analyze_task_catalog(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> TaskCatalog: ...


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


ScanPipelinePayload: TypeAlias = dict[str, object]


class ScanPipelinePlugin(Protocol):
    """Protocol for plugins that can alter scan pipeline preflight context."""

    def process_scan_pipeline(
        self,
        scan_options: ScanOptionsDict,
        scan_context: ScanMetadata,
    ) -> ScanPipelinePreflightContext: ...


@runtime_checkable
class OrchestratingScanPipelinePlugin(ScanPipelinePlugin, Protocol):
    """Protocol for scan-pipeline plugins that also orchestrate payload output."""

    def orchestrate_scan_payload(
        self,
        *,
        payload: ScanPipelinePayload,
        scan_options: ScanOptionsDict,
        strict_mode: bool,
        preflight_context: ScanMetadata | None = None,
    ) -> ScanPipelinePayload: ...


class CommentDrivenDocumentationPlugin(Protocol):
    """Protocol for comment-driven role note extraction."""

    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]: ...


class ExtractPolicyPlugin(Protocol):
    """Protocol marker for extract-policy plugin slot.

    Extract policy plugins cover task-line parsing, task annotation parsing,
    task traversal, and variable extraction. Each sub-type has its own
    specific interface; this Protocol serves as the registry slot type.
    """


class YAMLParsingPolicyPlugin(Protocol):
    """Protocol for YAML parsing/loading policy implementations."""

    def load_yaml_file(self, path: str | pathlib.Path) -> object: ...

    def parse_yaml_candidate(
        self,
        candidate: str | pathlib.Path,
        role_root: str | pathlib.Path,
    ) -> YamlParseFailure | None: ...


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
        self, scan_options: ScanOptionsDict
    ) -> PlatformExecutionBundle: ...


@runtime_checkable
class ReadmeRendererPlugin(Protocol):
    """Protocol for platform-specific README renderer plugin implementations.

    Each platform plugin owns its full README rendering vertical: section
    taxonomy, identity blocks, legacy marker prefixes, template path, and
    scanner-report blurb. All signatures are platform-neutral; platform-
    specific dict keys flow through the generic ``identity_metadata`` and
    ``metadata`` parameters.
    """

    PRISM_PLUGIN_API_VERSION: tuple[int, int]
    PLUGIN_IS_STATELESS: bool

    def default_section_specs(self) -> tuple[tuple[str, str], ...]: ...

    def extra_section_ids(self) -> frozenset[str]: ...

    def scanner_stats_section_ids(self) -> frozenset[str]: ...

    def merge_eligible_section_ids(self) -> frozenset[str]: ...

    def legacy_merge_marker_prefixes(self) -> tuple[str, ...]: ...

    def render_section_body(
        self,
        section_id: str,
        role_name: str,
        description: str,
        variables: dict[str, Any],
        requirements: list[Any],
        default_filters: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> str | None: ...

    def render_identity_section(
        self,
        section_id: str,
        role_name: str,
        description: str,
        requirements: list[Any],
        identity_metadata: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str | None: ...

    def default_template_path(self) -> pathlib.Path | None: ...

    def scanner_report_blurb(self, scanner_report_relpath: str) -> str: ...


class ScanPipelinePluginFactory(Protocol):
    """Factory contract for scan-pipeline plugin construction."""

    def __call__(self) -> ScanPipelinePlugin: ...


ScanPipelinePluginFactoryLike: TypeAlias = (
    type[ScanPipelinePlugin] | ScanPipelinePluginFactory
)


KernelPayload: TypeAlias = dict[str, object]


class KernelRequest(TypedDict, total=False):
    """Plugin-layer kernel request contract."""

    scan_id: str
    platform: str
    target_path: str
    options: ScanOptionsDict
    context: ScanMetadata


class KernelPhaseOutput(TypedDict, total=False):
    """Plugin-layer kernel phase output contract."""

    payload: RunScanOutputPayload | KernelPayload
    metadata: KernelPayload
    warnings: list[object]
    errors: list[object]
    provenance: list[object]


class KernelResponse(TypedDict, total=False):
    """Plugin-layer kernel response contract."""

    scan_id: str
    platform: str
    phase_results: dict[str, object]
    metadata: KernelPayload
    payload: RunScanOutputPayload | KernelPayload
    warnings: list[object]
    errors: list[object]
    provenance: list[object]


class KernelScanPayloadOrchestrator(Protocol):
    """Plugin-owned callable used by kernel plugins to build scan payloads."""

    def __call__(
        self,
        *,
        role_path: str,
        scan_options: ScanOptionsDict | None,
    ) -> RunScanOutputPayload: ...


@runtime_checkable
class KernelLifecyclePlugin(Protocol):
    """Plugin-layer kernel lifecycle contract."""

    def prepare(self, request: KernelRequest) -> KernelPhaseOutput | None: ...

    def scan(self, request: KernelRequest) -> KernelPhaseOutput | None: ...

    def analyze(
        self, request: KernelRequest, response: KernelResponse
    ) -> KernelPhaseOutput | None: ...

    def finalize(
        self, request: KernelRequest, response: KernelResponse
    ) -> KernelPhaseOutput | None: ...


class ScanPipelineRuntimeRegistry(Protocol):
    """Registry surface needed by API run_scan scan-pipeline orchestration."""

    def get_scan_pipeline_plugin(
        self, name: str
    ) -> ScanPipelinePluginFactoryLike | None: ...

    def list_scan_pipeline_plugins(self) -> list[str]: ...

    def get_default_platform_key(self) -> str | None: ...

    def is_reserved_unsupported_platform(self, name: str) -> bool: ...

    def get_variable_discovery_plugin(
        self,
        name: str,
    ) -> type[VariableDiscoveryPlugin] | None: ...

    def get_feature_detection_plugin(
        self,
        name: str,
    ) -> type[FeatureDetectionPlugin] | None: ...

    def get_output_orchestration_plugin(
        self,
        name: str,
    ) -> type[OutputOrchestrationPlugin] | None: ...

    def get_comment_driven_doc_plugin(
        self,
        name: str,
    ) -> type[CommentDrivenDocumentationPlugin] | None: ...

    def get_extract_policy_plugin(
        self,
        name: str,
    ) -> type[ExtractPolicyPlugin] | None: ...

    def get_yaml_parsing_policy_plugin(
        self,
        name: str,
    ) -> type[YAMLParsingPolicyPlugin] | None: ...

    def get_jinja_analysis_policy_plugin(
        self,
        name: str,
    ) -> type[JinjaAnalysisPolicyPlugin] | None: ...

    def get_readme_renderer_plugin(
        self,
        name: str,
    ) -> type[ReadmeRendererPlugin] | None: ...

    def list_variable_discovery_plugins(self) -> list[str]: ...

    def list_feature_detection_plugins(self) -> list[str]: ...

    def list_output_orchestration_plugins(self) -> list[str]: ...

    def list_comment_driven_doc_plugins(self) -> list[str]: ...

    def list_extract_policy_plugins(self) -> list[str]: ...

    def list_yaml_parsing_policy_plugins(self) -> list[str]: ...

    def list_jinja_analysis_policy_plugins(self) -> list[str]: ...

    def list_readme_renderer_plugins(self) -> dict[str, type[ReadmeRendererPlugin]]: ...
