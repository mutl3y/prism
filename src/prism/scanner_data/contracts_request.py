"""Minimal request contracts for fsrc scanner context orchestration."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from pathlib import Path
from typing import (
    Any,
    NotRequired,
    Protocol,
    Required,
    TypeAlias,
    TypedDict,
    runtime_checkable,
)


class ScanErrorEntry(TypedDict):
    """Structured scan-phase error emitted during best-effort execution."""

    phase: str
    error_type: str
    message: str


class ScanPolicyWarning(TypedDict, total=False):
    """Structured warning emitted for scan-policy compatibility behavior."""

    code: str
    message: str
    detail: dict[str, object]


class ScanPolicyDynamicIncludeFacts(TypedDict):
    """Dynamic-include blocker facts emitted by scanner_context."""

    enabled: bool
    task_count: int
    role_count: int
    total_count: int


class ScanPolicyYamlLikeAnnotationFacts(TypedDict):
    """YAML-like annotation blocker facts emitted by scanner_context."""

    enabled: bool
    count: int


class ScanPolicyBlockerProvenance(TypedDict):
    """Provenance for scanner_context-emitted blocker facts."""

    role_path: str
    exclude_path_patterns: list[str] | None
    metadata_feature_source: str
    dynamic_include_sources: list[str]


class ScanPolicyBlockerFacts(TypedDict):
    """Typed blocker-facts handoff carried after payload assembly."""

    dynamic_includes: ScanPolicyDynamicIncludeFacts
    yaml_like_annotations: ScanPolicyYamlLikeAnnotationFacts
    provenance: ScanPolicyBlockerProvenance


class VariableInsight(TypedDict, total=False):
    """Typed variable-insight payload carried in scan metadata."""

    name: str
    type: object
    default: object
    source: str | None
    required: bool
    documented: bool
    secret: bool
    is_unresolved: bool
    is_ambiguous: bool
    uncertainty_reason: str | None
    provenance_confidence: float


class YamlParseFailure(TypedDict):
    """Structured YAML parse-failure row used across scan/report flows.

    Success remains signaled by None. Failure rows always carry the existing
    four-key payload and preserve error-string boundaries such as read_error:.
    """

    file: str
    line: int | None
    column: int | None
    error: str


class RoleNotes(TypedDict):
    """Structured role-note buckets extracted from comment-doc parsing."""

    warnings: list[str]
    deprecations: list[str]
    notes: list[str]
    additionals: list[str]


class RequirementsDisplayEntry(TypedDict):
    """Single requirements-display entry emitted by scan orchestration."""

    collection: str


class DisplayVariableEntry(TypedDict, total=False):
    """Canonical display-variable row emitted by scan orchestration."""

    type: object
    default: object
    source: str | None
    required: bool
    documented: bool
    secret: bool
    is_unresolved: bool
    is_ambiguous: bool
    uncertainty_reason: str | None


DisplayVariables = dict[str, DisplayVariableEntry]


class ScanMetadata(TypedDict, total=False):
    """Metadata payload attached to scanner outputs."""

    plugin_name: str
    features: dict[str, object]
    scan_errors: list[ScanErrorEntry]
    scan_degraded: bool
    scan_policy_warnings: list[ScanPolicyWarning]
    scan_policy_blocker_facts: ScanPolicyBlockerFacts
    variable_insights: list[VariableInsight]
    yaml_parse_failures: list[YamlParseFailure]
    role_notes: RoleNotes
    ignore_unresolved_internal_underscore_references: bool
    underscore_filtered_unresolved_count: int
    concise_readme: bool
    include_scanner_report_link: bool
    scanner_report_relpath: str


class CommentDocMarkerContext(TypedDict, total=False):
    """Canonical comment-doc marker configuration."""

    prefix: str


class PolicyContext(TypedDict):
    """Per-scan immutable policy snapshot used to avoid shared global reads."""

    section_aliases: dict[str, str]
    ignored_identifiers: frozenset[str]
    variable_guidance_keywords: tuple[str, ...]


class CommentDocPolicyContext(TypedDict, total=False):
    """Optional comment-doc behavior overrides within policy context."""

    marker_prefix: str
    marker: CommentDocMarkerContext | str


class SelectionPolicyContext(TypedDict, total=False):
    """Optional scan-pipeline selection overrides within policy context."""

    plugin: str


TaskMapping: TypeAlias = Mapping[str, object]


class PreparedTaskLineParsingPolicy(Protocol):
    """Minimum task-line parsing capability surface required after ingress."""

    TASK_INCLUDE_KEYS: Collection[str]
    ROLE_INCLUDE_KEYS: Collection[str]
    INCLUDE_VARS_KEYS: Collection[str]
    SET_FACT_KEYS: Collection[str]
    TASK_BLOCK_KEYS: Collection[str]
    TASK_META_KEYS: Collection[str]

    def detect_task_module(self, task: TaskMapping) -> str | None: ...


class PreparedJinjaAnalysisPolicy(Protocol):
    """Minimum Jinja analysis capability surface required after ingress."""

    def collect_undeclared_jinja_variables(self, text: str) -> set[str]: ...


@runtime_checkable
class CacheFingerprintProvider(Protocol):
    """Optional semantic fingerprint contract for cache-sensitive opaque values."""

    def cache_fingerprint(self) -> object: ...


class PreparedTaskTraversalPolicy(Protocol):
    """Minimum task-traversal capability surface required after ingress."""

    def iter_task_mappings(self, data: object) -> Iterable[TaskMapping]: ...
    def iter_task_include_targets(self, data: object) -> list[str]: ...
    def iter_task_include_edges(self, data: object) -> list[dict[str, str]]: ...
    def expand_include_target_candidates(
        self, task: TaskMapping, include_target: str
    ) -> list[str]: ...
    def iter_role_include_targets(self, task: TaskMapping) -> list[str]: ...
    def iter_dynamic_role_include_targets(self, task: TaskMapping) -> list[str]: ...
    def collect_unconstrained_dynamic_task_includes(
        self, *, role_root: object, task_files: list[object], load_yaml_file: object
    ) -> list[dict[str, str]]: ...
    def collect_unconstrained_dynamic_role_includes(
        self, *, role_root: object, task_files: list[object], load_yaml_file: object
    ) -> list[dict[str, str]]: ...


class TaskAnnotation(TypedDict, total=False):
    """Typed shape for a single task annotation produced by extract_task_annotations_for_file."""

    kind: Required[str]
    text: Required[str]
    disabled: bool
    format_warning: str
    task_index: int


class PreparedTaskAnnotationPolicy(Protocol):
    """Minimum task-annotation capability surface required after ingress."""

    def split_task_annotation_label(self, text: str) -> tuple[str, str]: ...
    def split_task_target_payload(self, text: str) -> tuple[str, str]: ...
    def annotation_payload_looks_yaml(self, payload: str) -> bool: ...
    def normalize_marker_prefix(self, marker_prefix: str | None) -> str: ...
    def get_marker_line_re(self, marker_prefix: str = ...) -> object: ...
    def extract_task_annotations_for_file(
        self,
        lines: list[str],
        marker_prefix: str = ...,
        include_task_index: bool = ...,
    ) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]: ...
    def task_anchor(self, file_path: str, task_name: str, index: int) -> str: ...


class PreparedYAMLParsingPolicy(Protocol):
    """Minimum YAML parsing capability surface required after ingress."""

    def load_yaml_file(self, path: str | Path) -> object: ...
    def parse_yaml_candidate(
        self, candidate: str | Path, role_root: str | Path
    ) -> YamlParseFailure | None: ...


class PreparedVariableExtractorPolicy(Protocol):
    """Minimum variable-extractor capability surface required after ingress."""

    def collect_include_vars_files(
        self,
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files: object,
        load_yaml_file: object,
    ) -> list[object]: ...


class PreparedPolicyBundle(TypedDict, total=False):
    """Runtime-scoped prepared policy instances carried with scan options."""

    task_line_parsing: Required[PreparedTaskLineParsingPolicy]
    jinja_analysis: Required[PreparedJinjaAnalysisPolicy]
    task_traversal: NotRequired[PreparedTaskTraversalPolicy]
    yaml_parsing: NotRequired[PreparedYAMLParsingPolicy]
    variable_extractor: NotRequired[PreparedVariableExtractorPolicy]
    task_annotation_parsing: NotRequired[PreparedTaskAnnotationPolicy]
    comment_doc_marker_prefix: str
    ignore_unresolved_internal_underscore_references: bool


class DynamicIncludesPolicyContext(TypedDict, total=False):
    """Optional dynamic-includes behavior overrides within policy context."""

    fail_on_unconstrained: bool


class AnnotationsPolicyContext(TypedDict, total=False):
    """Optional annotations behavior overrides within policy context."""

    fail_on_yaml_like: bool


class ReferencesPolicyContext(TypedDict, total=False):
    """Optional references behavior overrides within policy context."""

    include_underscore_prefixed: bool


class PluginRuntimePolicyContext(TypedDict, total=False):
    """Optional plugin-runtime behavior overrides within policy context."""

    strict_phase_failures: bool


class ScanPolicyContext(TypedDict, total=False):
    """Optional policy-context overrides carried with scan options."""

    include_underscore_prefixed_references: bool
    comment_doc_marker_prefix: str
    comment_doc: CommentDocPolicyContext
    selection: SelectionPolicyContext
    dynamic_includes: DynamicIncludesPolicyContext
    annotations: AnnotationsPolicyContext
    references: ReferencesPolicyContext
    plugin_runtime: PluginRuntimePolicyContext


class ScanOptionsDict(TypedDict):
    """Canonical scan options used by scanner context wiring."""

    role_path: str
    role_name_override: str | None
    readme_config_path: str | None
    policy_config_path: str | None
    include_vars_main: bool
    exclude_path_patterns: list[str] | None
    detailed_catalog: bool
    include_task_parameters: bool
    include_task_runbooks: bool
    inline_task_runbooks: bool
    include_collection_checks: bool
    keep_unknown_style_sections: bool
    adopt_heading_mode: str | None
    vars_seed_paths: list[str] | None
    style_readme_path: str | None
    style_source_path: str | None
    style_guide_skeleton: bool
    compare_role_path: str | None
    fail_on_unconstrained_dynamic_includes: bool | None
    fail_on_yaml_like_task_annotations: bool | None
    ignore_unresolved_internal_underscore_references: bool | None
    comment_doc_marker_prefix: NotRequired[str | None]
    policy_context: NotRequired[ScanPolicyContext | None]
    prepared_policy_bundle: NotRequired[PreparedPolicyBundle | None]
    scan_policy_warnings: NotRequired[list[ScanPolicyWarning]]
    strict_phase_failures: NotRequired[bool]
    concise_readme: NotRequired[bool]
    scanner_report_output: NotRequired[str | None]
    include_scanner_report_link: NotRequired[bool]
    scan_pipeline_plugin: NotRequired[str]
    yaml_parse_failures: NotRequired[list[YamlParseFailure]]


class ScanContextPayload(TypedDict):
    """Prepared context payload returned by prepare_scan_context runtime seam."""

    rp: str
    role_name: str
    description: str
    requirements_display: list[RequirementsDisplayEntry]
    undocumented_default_filters: list[dict[str, object]]
    display_variables: DisplayVariables
    metadata: ScanMetadata


class FeaturesContext(TypedDict):
    """Canonical feature summary shape for detector output."""

    task_files_scanned: int
    tasks_scanned: int
    recursive_task_includes: int
    unique_modules: str
    external_collections: str
    handlers_notified: str
    privileged_tasks: int
    conditional_tasks: int
    tagged_tasks: int
    included_role_calls: int
    included_roles: str
    dynamic_included_role_calls: int
    dynamic_included_roles: str
    disabled_task_annotations: int
    yaml_like_task_annotations: int


def require_strict_phase_failures(
    value: object,
    *,
    field_name: str = "strict_phase_failures",
) -> bool:
    """Reject non-bool strict-phase values instead of truthifying them."""
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a bool when provided")
    return value


def resolve_strict_phase_failures(
    scan_options: Mapping[str, object],
    *,
    default: bool = True,
    field_name: str = "scan_options.strict_phase_failures",
) -> bool:
    """Read strict-phase mode from scan_options without reopening bool(...) coercion."""
    if "strict_phase_failures" not in scan_options:
        return default
    return require_strict_phase_failures(
        scan_options.get("strict_phase_failures"),
        field_name=field_name,
    )


def validate_variable_discovery_inputs(
    *,
    role_path: str,
    options: dict[str, Any],
) -> None:
    """Validate foundational input contracts for fsrc VariableDiscovery."""
    if not isinstance(role_path, str) or not role_path.strip():
        raise ValueError("'role_path' must be a non-empty string")
    if not isinstance(options, dict):
        raise ValueError("'options' must be a dict")

    if "role_path" in options:
        candidate = options["role_path"]
        if not isinstance(candidate, str) or not candidate.strip():
            raise ValueError(
                "'options.role_path' must be a non-empty string when provided"
            )

    include_vars_main = options.get("include_vars_main")
    if include_vars_main is not None and not isinstance(include_vars_main, bool):
        raise ValueError("'options.include_vars_main' must be a bool when provided")

    ignore_internal = options.get("ignore_unresolved_internal_underscore_references")
    if ignore_internal is not None and not isinstance(ignore_internal, bool):
        raise ValueError(
            "'options.ignore_unresolved_internal_underscore_references' "
            "must be a bool when provided"
        )

    exclude_paths = options.get("exclude_path_patterns")
    if exclude_paths is not None and not isinstance(exclude_paths, list):
        raise ValueError("'options.exclude_path_patterns' must be a list[str] or None")
    if isinstance(exclude_paths, list) and any(
        not isinstance(item, str) for item in exclude_paths
    ):
        raise ValueError(
            "'options.exclude_path_patterns' must contain only strings when provided"
        )

    vars_seed_paths = options.get("vars_seed_paths")
    if vars_seed_paths is not None and not isinstance(vars_seed_paths, list):
        raise ValueError("'options.vars_seed_paths' must be a list[str] or None")
    if isinstance(vars_seed_paths, list) and any(
        not isinstance(item, str) for item in vars_seed_paths
    ):
        raise ValueError(
            "'options.vars_seed_paths' must contain only strings when provided"
        )

    prepared_policy_bundle = options.get("prepared_policy_bundle")
    if prepared_policy_bundle is not None and not isinstance(
        prepared_policy_bundle,
        dict,
    ):
        raise ValueError(
            "'options.prepared_policy_bundle' must be a dict when provided"
        )


def validate_feature_detector_inputs(
    *,
    di: Any,
    role_path: str,
    options: dict[str, Any],
) -> None:
    """Validate foundational input contracts for fsrc FeatureDetector."""
    if di is None:
        raise ValueError("'di' must not be None")
    if not isinstance(role_path, str) or not role_path.strip():
        raise ValueError("'role_path' must be a non-empty string")
    if not isinstance(options, dict):
        raise ValueError("'options' must be a dict")

    if "role_path" in options:
        candidate = options["role_path"]
        if not isinstance(candidate, str) or not candidate.strip():
            raise ValueError(
                "'options.role_path' must be a non-empty string when provided"
            )

    exclude_paths = options.get("exclude_path_patterns")
    if exclude_paths is not None and not isinstance(exclude_paths, list):
        raise ValueError("'options.exclude_path_patterns' must be a list[str] or None")
    if isinstance(exclude_paths, list) and any(
        not isinstance(item, str) for item in exclude_paths
    ):
        raise ValueError(
            "'options.exclude_path_patterns' must contain only strings when provided"
        )
