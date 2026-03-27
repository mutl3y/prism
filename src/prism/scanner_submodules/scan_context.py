"""Scan-context and output-payload shaping helpers for scanner orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

if TYPE_CHECKING:
    pass


class _SectionTitleBucket(TypedDict):
    """Aggregated section title statistics from style guide parsing."""

    count: int
    """Number of occurrences of this section."""
    known: bool
    """True if section has a known/mapped identifier."""
    titles: list[str]
    """Observed section titles (original casing)."""
    normalized_titles: list[str]
    """Observed section titles (normalized for matching)."""


class _StyleSection(TypedDict):
    """Individual section parsed from a style guide README."""

    id: str
    """Canonical section identifier (mapped via STYLE_SECTION_ALIASES)."""
    title: str
    """Original section title text."""
    normalized_title: str
    """Normalized title for matching (lowercase, spaces normalized)."""
    body: str
    """Rendered section body content."""
    level: int
    """Markdown heading level (2-6)."""


class _SectionTitleStats(TypedDict):
    """Aggregated title statistics from all style guide sections."""

    total_sections: int
    """Total number of sections parsed."""
    known_sections: int
    """Count of sections with known/mapped identifiers."""
    unknown_sections: int
    """Count of sections with unknown identifiers."""
    by_section_id: dict[str, _SectionTitleBucket]
    """Aggregated statistics keyed by section identifier."""


class FeaturesContext(TypedDict):
    """Typed contract for role feature detection results.

    Captures adaptive role features extracted from task scanning and role structure,
    enabling type-safe feature access throughout scanner orchestration.

    **Task Analysis (always present):**
    - task_files_scanned: Number of task files discovered
    - tasks_scanned: Total task count across all scanned files
    - recursive_task_includes: Number of nested task includes (import_tasks/include_tasks)
    - unique_modules: Comma-separated list of distinct Ansible modules used
    - external_collections: Comma-separated list of non-ansible.builtin collections
    - handlers_notified: Comma-separated list of handlers notified by tasks

    **Task Metadata Counts (always present):**
    - privileged_tasks: Number of tasks using become/privilege escalation
    - conditional_tasks: Number of tasks with when conditions
    - tagged_tasks: Number of tasks with tags
    - included_role_calls: Count of static role includes (import_role/include_role)
    - included_roles: Comma-separated list of included role names
    - dynamic_included_role_calls: Count of dynamic role includes (variables in include_role)
    - dynamic_included_roles: Comma-separated list of dynamically included role names

    **Annotation Quality Metrics (always present):**
    - disabled_task_annotations: Count of disabled/commented task annotations
    - yaml_like_task_annotations: Count of YAML-like format violations

    Flow:
    1. extract_role_features() builds this dict from role paths
    2. Used for feature detection, doc insights, and capability inference
    3. Consumed by build_doc_insights() and collection compliance checking
    """

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
    """Typed contract for parsed style guide configuration.

    Captures rendered style guide metadata and configuration flowing through
    style-guide-based README rendering, enabling type-safe style configuration
    access and section ordering.

    **Source & Rendering (always present):**
    - path: Absolute path to source style guide markdown file
    - title_text: Parsed document title from style guide
    - title_style: Heading style for document title ('atx' or 'setext')
    - section_style: Heading style for section headings ('atx' or 'setext')
    - section_level: Markdown level for section headings (2-6)

    **Parsed Sections & Metadata (always present):**
    - sections: List of parsed section dicts (id, title, body, level, etc.)
    - section_title_stats: Aggregated title statistics by section identifier
    - variable_style: Variable section rendering format detected ('simple_list',
      'yaml_block', 'table', 'nested_bullets')
    - variable_intro: Optional introductory text for variable section

    Flow:
    1. parse_style_readme() builds this dict from style guide file path
    2. Used by _render_readme_with_style_guide() for section ordering/rendering
    3. Consumed by _resolve_ordered_style_sections() and section formatters
    """

    path: str
    title_text: str
    title_style: str
    section_style: str
    section_level: int
    sections: list[_StyleSection]
    section_title_stats: _SectionTitleStats
    variable_style: str
    variable_intro: NotRequired[str | None]


class ScanMetadata(TypedDict, total=False):
    """Comprehensive metadata contract flowing through scanner orchestration.

    This TypedDict captures all scan-related metadata that flows through the
    scanner pipeline, from initial artifact collection through output emission.

    **Core Identity & Configuration (always present):**
    - molecule_scenarios: Detected Molecule test scenarios in role
    - marker_prefix: Prefix for documentation markers (e.g., 'ansible_doc')
    - detailed_catalog: Whether to include detailed file catalogs
    - include_task_parameters: Include task module parameter documentation
    - include_task_runbooks: Include generated runbook content
    - inline_task_runbooks: Inline runbooks in role content (vs. separate)
    - keep_unknown_style_sections: Preserve unrecognized style guide sections

    **Role Contents (always present after discovery):**
    - handlers: List of handler file paths relative to role root
    - tasks: List of task file paths
    - templates: List of template file paths
    - files: List of static file paths
    - tests: List of test file paths
    - defaults: List of default variable file paths
    - vars: List of variable file paths
    - meta: Parsed role metadata (meta/main.yml as dict)
    - features: Extracted role features (tasks_scanned, unique_modules, etc.)

    **Dynamic Includes (always present):**
    - unconstrained_dynamic_task_includes: Tasks with dynamic includes
    - unconstrained_dynamic_role_includes: Roles with dynamic includes

    **README Section Configuration (always present):**
    - enabled_sections: List of enabled README section identifiers
    - section_title_overrides: Custom section title overrides (dict)
    - section_content_modes: Section rendering mode overrides (dict)

    **Variable & Issue Analysis (always present):**
    - variable_insights: Analyzed variable metadata (list of dicts)
    - yaml_parse_failures: YAML parsing error details
    - role_notes: Extracted role notes from comments
    - scanner_counters: Comprehensive scanning metrics (ScannerCounters dict)
    - external_vars_context: Non-authoritative external variable context

    **Output & Emission Control (set during output phase):**
    - concise_readme: Emit concise README mode
    - include_scanner_report_link: Link to scanner report from README
    - scanner_report_relpath: Relative path to emitted scanner report

    **Compliance & Styling (conditionally present):**
    - collection_compliance_notes: Notes on collection requirement compliance
    - style_guide: Parsed style guide documentation
    - style_guide_skeleton: Whether style guide is minimal skeleton
    - comparison: Comparison report against baseline role

    **Annotation & Error Policy (always present):**
    - fail_on_unconstrained_dynamic_includes: Strict enforcement mode
    - fail_on_yaml_like_task_annotations: Strict YAML-like annotation mode
    - ignore_unresolved_internal_underscore_references: Ignore pattern mode

    **Optional Detailed Catalogs (only if detailed_catalog=True):**
    - task_catalog: Detailed task-by-task catalog
    - handler_catalog: Detailed handler-by-handler catalog

    **Documentation Insights (always present):**
    - doc_insights: Aggregated documentation quality insights
    """

    # Core identity & configuration (runtime setters)
    molecule_scenarios: list[Any]
    marker_prefix: str
    detailed_catalog: bool
    include_task_parameters: bool
    include_task_runbooks: bool
    inline_task_runbooks: bool
    keep_unknown_style_sections: bool

    # Role contents (always present after discovery)
    handlers: list[str]
    tasks: list[str]
    templates: list[str]
    files: list[str]
    tests: list[str]
    defaults: list[str]
    vars: list[str]
    meta: dict[str, Any]
    features: FeaturesContext

    # Dynamic includes (always present after discovery)
    unconstrained_dynamic_task_includes: list[Any]
    unconstrained_dynamic_role_includes: list[Any]

    # README section configuration (always present after config load)
    enabled_sections: list[str]
    section_title_overrides: NotRequired[dict[str, str]]
    section_content_modes: NotRequired[dict[str, str]]

    # Variable & issue analysis (always present after enrichment)
    variable_insights: list[dict[str, Any]]
    yaml_parse_failures: list[dict[str, object]]
    role_notes: list[dict[str, Any]]
    scanner_counters: (
        dict[str, Any] | None
    )  # ScannerCounters (use dict for backward compat)
    external_vars_context: NotRequired[dict[str, Any]]

    # Output & emission control (set during output phase)
    concise_readme: NotRequired[bool]
    include_scanner_report_link: NotRequired[bool]
    scanner_report_relpath: NotRequired[str]

    # Compliance & styling (conditionally present)
    collection_compliance_notes: NotRequired[Any]
    style_guide: NotRequired[StyleGuideConfig]
    style_guide_skeleton: NotRequired[bool]
    comparison: NotRequired[dict[str, Any]]

    # Annotation & error policy (always present after policy load)
    fail_on_unconstrained_dynamic_includes: bool
    fail_on_yaml_like_task_annotations: bool
    ignore_unresolved_internal_underscore_references: bool

    # Optional detailed catalogs (only if detailed_catalog=True)
    task_catalog: NotRequired[list[Any]]
    handler_catalog: NotRequired[list[Any]]

    # Documentation insights (always present after enrichment)
    doc_insights: dict[str, Any]


class ReferenceContext(TypedDict):
    """Typed contract for variable reference context tracking and enrichment.

    Captures seed and dynamic variable reference data flowing through variable
    analysis pipelines, enabling type-safe access to reference metadata and
    uncertainty tracking.

    **Seed Variables (external/authoritative):**
    - seed_values: Dict mapping variable names to resolved default values,
      loaded from external seed variable files (e.g., defaults/main.yml).
    - seed_secrets: Set of variable names flagged as sensitive/vaulted based
      on name tokens or detected value markers (e.g., vault_ prefix).
    - seed_sources: Dict mapping variable names to their source file paths
      for provenance tracking and confidence scoring.

    **Dynamic Variable References (inferred from tasks/handlers/templates):**
    - dynamic_include_vars_refs: List of raw dynamic include variable
      references (e.g., "vars: var_name" lines extracted from include_vars tasks).
    - dynamic_include_var_tokens: Set of normalized variable name tokens
      extracted from dynamic_include_vars_refs for uncertainty suppression.
    - dynamic_task_include_tokens: Set of normalized variable name tokens
      referenced in dynamic task/role includes, used for uncertainty reasoning.

    Flow:
    1. _collect_variable_reference_context() builds this dict from role paths
    2. _populate_variable_rows() uses all fields for variable enrichment
    3. _build_referenced_variable_uncertainty_reason() consumes dynamic fields
       for uncertainty text generation

    Type guarantees:
    - seed_values: arbitrary JSON-serializable defaults (str, int, dict, etc.)
    - seed_secrets & dynamic_*_tokens: lowercase normalized identifiers
    - seed_sources & dynamic_include_vars_refs: non-empty strings when present
    """

    seed_values: dict[str, Any]
    seed_secrets: set[str]
    seed_sources: dict[str, str]
    dynamic_include_vars_refs: list[str]
    dynamic_include_var_tokens: set[str]
    dynamic_task_include_tokens: set[str]


class ScanContext(TypedDict):
    """Internal scan context consumed by output payload shaping."""

    display_variables: dict[str, Any]
    metadata: ScanMetadata


class ScanBaseContext(TypedDict):
    """Typed return contract for _collect_scan_base_context.

    Stabilizes the internal seam between base-context collection and the
    prepare-scan-context orchestration step, including all policy-enforcement outputs.
    """

    rp: str
    role_name: str
    description: str
    marker_prefix: str
    variables: dict[str, Any]
    found: list[Any]
    metadata: ScanMetadata
    requirements_display: list[Any]


class RunScanOutputPayload(TypedDict):
    """Typed seam payload between run_scan orchestration and output rendering."""

    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata


class EmitScanOutputsArgs(TypedDict):
    """Argument bundle for _emit_scan_outputs to reduce caller argument-drift risk."""

    output: str
    output_format: str
    concise_readme: bool
    scanner_report_output: str | None
    include_scanner_report_link: bool
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata
    template: str | None
    dry_run: bool
    runbook_output: str | None
    runbook_csv_output: str | None


class ScanReportSidecarArgs(TypedDict):
    """Argument bundle for _write_concise_scanner_report_if_enabled.

    Prevents argument-drift between _emit_scan_outputs and the sidecar emission
    helper.
    """

    concise_readme: bool
    scanner_report_output: str | None
    out_path: Path
    include_scanner_report_link: bool
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: ScanMetadata
    dry_run: bool


class RunbookSidecarArgs(TypedDict):
    """Argument bundle for _write_optional_runbook_outputs.

    Bundles the data fields so the call site in _emit_scan_outputs is a single
    structured object rather than scattered keyword arguments.
    """

    runbook_output: str | None
    runbook_csv_output: str | None
    role_name: str
    metadata: ScanMetadata


type PreparedScanContext = tuple[
    str,
    str,
    str,
    list[Any],
    list[Any],
    ScanContext,
]


def finalize_scan_context_payload(
    *,
    rp: str,
    role_name: str,
    description: str,
    requirements_display: list[Any],
    undocumented_default_filters: list[dict[str, Any]],
    display_variables: dict[str, Any],
    metadata: ScanMetadata,
) -> PreparedScanContext:
    """Return normalized context payload used by run_scan output emission."""
    return (
        rp,
        role_name,
        description,
        requirements_display,
        undocumented_default_filters,
        {
            "display_variables": display_variables,
            "metadata": metadata,
        },
    )


def build_scan_output_payload(
    *,
    role_name: str,
    description: str,
    display_variables: dict[str, Any],
    requirements_display: list[Any],
    undocumented_default_filters: list[Any],
    metadata: ScanMetadata,
) -> RunScanOutputPayload:
    """Build the shared payload used for scanner report and primary output rendering."""
    return {
        "role_name": role_name,
        "description": description,
        "display_variables": display_variables,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "metadata": metadata,
    }


def prepare_run_scan_payload(
    *,
    prepared_scan_context: PreparedScanContext,
) -> RunScanOutputPayload:
    """Shape prepared scan context into the output payload consumed by run_scan."""
    (
        _rp,
        role_name,
        description,
        requirements_display,
        undocumented_default_filters,
        scan_context,
    ) = prepared_scan_context
    return {
        "role_name": role_name,
        "description": description,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "display_variables": scan_context["display_variables"],
        "metadata": scan_context["metadata"],
    }


def build_scan_report_sidecar_args(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    payload: RunScanOutputPayload,
    dry_run: bool,
) -> ScanReportSidecarArgs:
    """Build the typed argument bundle for _write_concise_scanner_report_if_enabled."""
    return {
        "concise_readme": concise_readme,
        "scanner_report_output": scanner_report_output,
        "out_path": out_path,
        "include_scanner_report_link": include_scanner_report_link,
        "role_name": payload["role_name"],
        "description": payload["description"],
        "display_variables": payload["display_variables"],
        "requirements_display": payload["requirements_display"],
        "undocumented_default_filters": payload["undocumented_default_filters"],
        "metadata": payload["metadata"],
        "dry_run": dry_run,
    }


def build_emit_scan_outputs_args(
    *,
    output: str,
    output_format: str,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    payload: RunScanOutputPayload,
    template: str | None,
    dry_run: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> EmitScanOutputsArgs:
    """Build the typed argument bundle for _emit_scan_outputs from run_scan inputs."""
    return {
        "output": output,
        "output_format": output_format,
        "concise_readme": concise_readme,
        "scanner_report_output": scanner_report_output,
        "include_scanner_report_link": include_scanner_report_link,
        "role_name": payload["role_name"],
        "description": payload["description"],
        "display_variables": payload["display_variables"],
        "requirements_display": payload["requirements_display"],
        "undocumented_default_filters": payload["undocumented_default_filters"],
        "metadata": payload["metadata"],
        "template": template,
        "dry_run": dry_run,
        "runbook_output": runbook_output,
        "runbook_csv_output": runbook_csv_output,
    }


def build_runbook_sidecar_args(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    payload: RunScanOutputPayload,
) -> RunbookSidecarArgs:
    """Build the typed argument bundle for _write_optional_runbook_outputs."""
    return {
        "runbook_output": runbook_output,
        "runbook_csv_output": runbook_csv_output,
        "role_name": payload["role_name"],
        "metadata": payload["metadata"],
    }
