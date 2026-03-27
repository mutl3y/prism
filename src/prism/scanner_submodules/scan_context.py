"""Scan-context and output-payload shaping helpers for scanner orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

if TYPE_CHECKING:
    from .scanner_report import ScannerCounters


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
    features: dict[str, Any]

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
    scanner_counters: dict[str, Any] | None  # ScannerCounters (use dict for backward compat)
    external_vars_context: NotRequired[dict[str, Any]]

    # Output & emission control (set during output phase)
    concise_readme: NotRequired[bool]
    include_scanner_report_link: NotRequired[bool]
    scanner_report_relpath: NotRequired[str]

    # Compliance & styling (conditionally present)
    collection_compliance_notes: NotRequired[Any]
    style_guide: NotRequired[dict[str, Any]]
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
