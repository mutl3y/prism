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


def validate_variable_discovery_inputs(
    *,
    role_path: object,
    options: object,
) -> None:
    """Validate VariableDiscovery constructor inputs at the request seam."""
    if not isinstance(role_path, str) or not role_path.strip():
        raise ValueError(f"'role_path' must be a non-empty string. Got: {role_path!r}")
    if not isinstance(options, dict):
        raise ValueError(f"'options' must be a dict. Got: {options!r}")

    option_role_path = options.get("role_path")
    if option_role_path is not None and (
        not isinstance(option_role_path, str) or not option_role_path.strip()
    ):
        raise ValueError(
            "'options.role_path' must be a non-empty string when provided. "
            f"Got: {option_role_path!r}"
        )

    include_vars_main = options.get("include_vars_main")
    if include_vars_main is not None and not isinstance(include_vars_main, bool):
        raise ValueError(
            "'options.include_vars_main' must be a bool when provided. "
            f"Got: {include_vars_main!r}"
        )

    ignore_internal = options.get("ignore_unresolved_internal_underscore_references")
    if ignore_internal is not None and not isinstance(ignore_internal, bool):
        raise ValueError(
            "'options.ignore_unresolved_internal_underscore_references' "
            f"must be a bool when provided. Got: {ignore_internal!r}"
        )

    for field_name in ("exclude_path_patterns", "vars_seed_paths"):
        field_value = options.get(field_name)
        if field_value is None:
            continue
        if not isinstance(field_value, list):
            raise ValueError(
                f"'options.{field_name}' must be a list[str] or None. "
                f"Got: {field_value!r}"
            )
        if any(not isinstance(item, str) for item in field_value):
            raise ValueError(
                f"'options.{field_name}' must contain only strings when provided. "
                f"Got: {field_value!r}"
            )


def validate_feature_detector_inputs(
    *,
    di: object,
    role_path: object,
    options: object,
) -> None:
    """Validate FeatureDetector constructor inputs at the request seam."""
    if di is None:
        raise ValueError("'di' must not be None.")
    if not isinstance(role_path, str) or not role_path.strip():
        raise ValueError(f"'role_path' must be a non-empty string. Got: {role_path!r}")
    if not isinstance(options, dict):
        raise ValueError(f"'options' must be a dict. Got: {options!r}")

    exclude_path_patterns = options.get("exclude_path_patterns")
    if exclude_path_patterns is not None:
        if not isinstance(exclude_path_patterns, list):
            raise ValueError(
                "'options.exclude_path_patterns' must be a list[str] or None. "
                f"Got: {exclude_path_patterns!r}"
            )
        if any(not isinstance(item, str) for item in exclude_path_patterns):
            raise ValueError(
                "'options.exclude_path_patterns' must contain only strings when "
                f"provided. Got: {exclude_path_patterns!r}"
            )


def validate_run_scan_option_inputs(
    *,
    role_path: object,
    role_name_override: object,
    readme_config_path: object,
    include_vars_main: object,
    exclude_path_patterns: object,
    detailed_catalog: object,
    include_task_parameters: object,
    include_task_runbooks: object,
    inline_task_runbooks: object,
    include_collection_checks: object,
    keep_unknown_style_sections: object,
    adopt_heading_mode: object,
    vars_seed_paths: object,
    style_readme_path: object,
    style_source_path: object,
    style_guide_skeleton: object,
    compare_role_path: object,
    fail_on_unconstrained_dynamic_includes: object,
    fail_on_yaml_like_task_annotations: object,
    ignore_unresolved_internal_underscore_references: object,
    policy_context: object,
) -> None:
    """Validate request-boundary scan options before runtime orchestration."""

    def _require_non_empty_string(field_name: str, value: object) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"'{field_name}' must be a non-empty string. Got: {value!r}"
            )

    def _require_optional_string(field_name: str, value: object) -> None:
        if value is not None and not isinstance(value, str):
            raise ValueError(f"'{field_name}' must be a string or None. Got: {value!r}")

    def _require_bool(field_name: str, value: object) -> None:
        if not isinstance(value, bool):
            raise ValueError(f"'{field_name}' must be a bool. Got: {value!r}")

    def _require_optional_bool(field_name: str, value: object) -> None:
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"'{field_name}' must be a bool or None. Got: {value!r}")

    def _require_optional_string_list(field_name: str, value: object) -> None:
        if value is None:
            return
        if not isinstance(value, list):
            raise ValueError(
                f"'{field_name}' must be a list[str] or None. Got: {value!r}"
            )
        if any(not isinstance(item, str) for item in value):
            raise ValueError(
                f"'{field_name}' must contain only strings when provided. "
                f"Got: {value!r}"
            )

    def _require_policy_context(value: object) -> None:
        if value is None:
            return
        if not isinstance(value, dict):
            raise ValueError(f"'policy_context' must be a dict or None. Got: {value!r}")

        section_aliases = value.get("section_aliases")
        if not isinstance(section_aliases, dict) or any(
            not isinstance(key, str) or not isinstance(alias, str)
            for key, alias in section_aliases.items()
        ):
            raise ValueError(
                "'policy_context.section_aliases' must be a dict[str, str]. "
                f"Got: {section_aliases!r}"
            )

        ignored_identifiers = value.get("ignored_identifiers")
        if not isinstance(ignored_identifiers, frozenset) or any(
            not isinstance(token, str) for token in ignored_identifiers
        ):
            raise ValueError(
                "'policy_context.ignored_identifiers' must be a frozenset[str]. "
                f"Got: {ignored_identifiers!r}"
            )

        guidance_keywords = value.get("variable_guidance_keywords")
        if not isinstance(guidance_keywords, tuple) or any(
            not isinstance(token, str) for token in guidance_keywords
        ):
            raise ValueError(
                "'policy_context.variable_guidance_keywords' must be a tuple[str, ...]. "
                f"Got: {guidance_keywords!r}"
            )

    _require_non_empty_string("role_path", role_path)

    for field_name, field_value in (
        ("role_name_override", role_name_override),
        ("readme_config_path", readme_config_path),
        ("adopt_heading_mode", adopt_heading_mode),
        ("style_readme_path", style_readme_path),
        ("style_source_path", style_source_path),
        ("compare_role_path", compare_role_path),
    ):
        _require_optional_string(field_name, field_value)

    for field_name, field_value in (
        ("include_vars_main", include_vars_main),
        ("detailed_catalog", detailed_catalog),
        ("include_task_parameters", include_task_parameters),
        ("include_task_runbooks", include_task_runbooks),
        ("inline_task_runbooks", inline_task_runbooks),
        ("include_collection_checks", include_collection_checks),
        ("keep_unknown_style_sections", keep_unknown_style_sections),
        ("style_guide_skeleton", style_guide_skeleton),
    ):
        _require_bool(field_name, field_value)

    for field_name, field_value in (
        (
            "fail_on_unconstrained_dynamic_includes",
            fail_on_unconstrained_dynamic_includes,
        ),
        ("fail_on_yaml_like_task_annotations", fail_on_yaml_like_task_annotations),
        (
            "ignore_unresolved_internal_underscore_references",
            ignore_unresolved_internal_underscore_references,
        ),
    ):
        _require_optional_bool(field_name, field_value)

    for field_name, field_value in (
        ("exclude_path_patterns", exclude_path_patterns),
        ("vars_seed_paths", vars_seed_paths),
    ):
        _require_optional_string_list(field_name, field_value)

    _require_policy_context(policy_context)


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
    "validate_feature_detector_inputs",
    "validate_variable_discovery_inputs",
    "validate_run_scan_option_inputs",
    "_SectionTitleBucket",
    "_StyleSection",
]
