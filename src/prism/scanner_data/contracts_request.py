"""Request and scan-context contracts owned by the scan orchestration domain."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class _SectionTitleBucket(TypedDict):
    """Aggregated section title statistics from style guide parsing."""

    count: int
    known: bool
    titles: list[str]
    normalized_titles: list[str]


class _StyleSection(TypedDict):
    """Individual section parsed from a style guide README."""

    id: str
    title: str
    normalized_title: str
    body: str
    level: int


class _SectionTitleStats(TypedDict):
    """Aggregated title statistics from all style guide sections."""

    total_sections: int
    known_sections: int
    unknown_sections: int
    by_section_id: dict[str, _SectionTitleBucket]


class FeaturesContext(TypedDict):
    """Typed contract for role feature detection results."""

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


class StyleGuideConfig(TypedDict):
    """Typed contract for parsed style guide configuration."""

    path: str
    title_text: str
    title_style: str
    section_style: str
    section_level: int
    sections: list[_StyleSection]
    section_title_stats: _SectionTitleStats
    variable_style: str
    variable_intro: NotRequired[str | None]


class ScanPhaseError(TypedDict):
    """Structured scan phase failure metadata for degraded scan payloads."""

    phase: str
    error_type: str
    message: str


class ScanMetadata(TypedDict, total=False):
    """Comprehensive metadata contract flowing through scanner orchestration."""

    molecule_scenarios: list[Any]
    marker_prefix: str
    detailed_catalog: bool
    include_task_parameters: bool
    include_task_runbooks: bool
    inline_task_runbooks: bool
    keep_unknown_style_sections: bool
    handlers: list[str]
    tasks: list[str]
    templates: list[str]
    files: list[str]
    tests: list[str]
    defaults: list[str]
    vars: list[str]
    meta: dict[str, Any]
    features: FeaturesContext
    unconstrained_dynamic_task_includes: list[Any]
    unconstrained_dynamic_role_includes: list[Any]
    enabled_sections: list[str]
    section_title_overrides: NotRequired[dict[str, str]]
    section_content_modes: NotRequired[dict[str, str]]
    readme_section_config_warnings: NotRequired[list[str]]
    readme_marker_config_warnings: NotRequired[list[str]]
    meta_load_warnings: NotRequired[list[str]]
    variable_insights: list[dict[str, Any]]
    yaml_parse_failures: list[dict[str, object]]
    role_notes: list[dict[str, Any]]
    scanner_counters: dict[str, Any] | None
    external_vars_context: NotRequired[dict[str, Any]]
    concise_readme: NotRequired[bool]
    include_scanner_report_link: NotRequired[bool]
    scanner_report_relpath: NotRequired[str]
    collection_compliance_notes: NotRequired[Any]
    style_guide: NotRequired[StyleGuideConfig]
    style_guide_skeleton: NotRequired[bool]
    comparison: NotRequired[dict[str, Any]]
    fail_on_unconstrained_dynamic_includes: bool
    fail_on_yaml_like_task_annotations: bool
    ignore_unresolved_internal_underscore_references: bool
    scan_errors: NotRequired[list[ScanPhaseError]]
    scan_degraded: NotRequired[bool]
    task_catalog: NotRequired[list[Any]]
    handler_catalog: NotRequired[list[Any]]
    doc_insights: dict[str, Any]


class ScanContext(TypedDict):
    """Internal scan context consumed by output payload shaping."""

    display_variables: dict[str, Any]
    metadata: ScanMetadata


class ScanBaseContext(TypedDict):
    """Typed return contract for base-context collection."""

    rp: str
    role_name: str
    description: str
    marker_prefix: str
    variables: dict[str, Any]
    found: list[Any]
    metadata: ScanMetadata
    requirements_display: list[Any]


class PolicyContext(TypedDict):
    """Per-scan immutable policy snapshot used to avoid shared global reads."""

    section_aliases: dict[str, str]
    ignored_identifiers: frozenset[str]
    variable_guidance_keywords: tuple[str, ...]


class ScanOptionsDict(TypedDict):
    """Normalized scan configuration passed through the scanner pipeline."""

    role_path: str
    role_name_override: str | None
    readme_config_path: str | None
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
    policy_context: NotRequired[PolicyContext | None]
    strict_phase_failures: NotRequired[bool]


class ScanContextPayload(TypedDict):
    """Assembled scan context payload ready for output orchestration."""

    rp: str
    role_name: str
    description: str
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    display_variables: dict[str, Any]
    metadata: ScanMetadata


__all__ = [
    "FeaturesContext",
    "PolicyContext",
    "ScanBaseContext",
    "ScanContext",
    "ScanContextPayload",
    "ScanMetadata",
    "ScanOptionsDict",
    "ScanPhaseError",
    "StyleGuideConfig",
    "_SectionTitleBucket",
    "_StyleSection",
]
