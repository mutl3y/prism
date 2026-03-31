"""Scanner data contracts and types.

This module consolidates all TypedDict data contracts used throughout the scanner
pipeline, providing a single source of truth for data structure definitions.

All contracts are defined here with no imports from scanner.py or submodules
to prevent circular dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NotRequired, TypedDict

# ============================================================================
# Variable & Provenance Contracts
# ============================================================================


class Variable(TypedDict, total=False):
    """A variable metadata entry with type, default, and description."""

    name: str
    """Variable name."""
    type: str
    """Inferred type: string, list, dict, int, bool, computed, documented, required."""
    default: str
    """Formatted default value or placeholder."""
    description: str
    """Documentation or inferred description."""
    required: bool
    """True if variable appears required (no default found)."""
    secret: bool
    """True if variable looks like a credential or sensitive value."""


class VariableProvenance(TypedDict, total=False):
    """Metadata tracking the source and confidence of a variable."""

    source_file: str
    """Relative path to source file (e.g. 'defaults/main.yml')."""
    line: int | None
    """Line number in source file, if determinable."""
    confidence: float
    """Confidence level (0.0-1.0): explicit=0.95, inferred=0.5-0.7, dynamic_unknown=0.4."""
    source_type: str
    """Source type: defaults, vars, meta, include_vars, set_fact, readme."""


class VariableRow(TypedDict, total=False):
    """A variable discovered during role scanning with provenance metadata."""

    name: str
    """Variable name."""
    type: str
    """Inferred type: string, list, dict, int, bool, computed, documented, required."""
    default: str
    """Formatted default value or placeholder."""
    source: str
    """Human-readable source description."""
    documented: bool
    """True if variable is explicitly documented somewhere."""
    required: bool
    """True if variable appears required (no default found)."""
    secret: bool
    """True if variable looks like a credential or sensitive value."""
    provenance_source_file: str
    """Relative path to source file (e.g. 'defaults/main.yml')."""
    provenance_line: int | None
    """Line number in source file, if determinable."""
    provenance_confidence: float
    """Confidence level (0.0-1.0) for this variable's accuracy."""
    uncertainty_reason: str | None
    """Explanation if confidence is below 1.0 or variable is ambiguous."""
    is_unresolved: bool
    """True if variable cannot be resolved to a static definition."""
    is_ambiguous: bool
    """True if variable has multiple possible sources or values."""
    readme_documented: NotRequired[bool]
    """True if variable is documented in the role README."""
    non_authoritative_test_evidence: NotRequired[dict[str, Any]]
    """Non-authoritative test evidence attached during pipeline enrichment."""


class VariableRowWithMeta(TypedDict, total=False):
    """VariableRow augmented with provenance and intermediate metadata.

    Extends VariableRow with detailed provenance tracking and uncertainty metadata
    used during variable enrichment and discovery phases.
    """

    name: str
    """Variable name."""
    type: str
    """Inferred type."""
    default: str
    """Formatted default value."""
    source: str
    """Human-readable source description."""
    documented: bool
    """True if explicitly documented."""
    required: bool
    """True if required."""
    secret: bool
    """True if sensitive/vaulted."""
    provenance_source_file: str
    """Source file path."""
    provenance_line: int | None
    """Line number in source."""
    provenance_confidence: float
    """Confidence (0.0-1.0)."""
    uncertainty_reason: str | None
    """Uncertainty explanation."""
    is_unresolved: bool
    """True if unresolved."""
    is_ambiguous: bool
    """True if ambiguous."""
    external_evidence: NotRequired[list[dict[str, Any]]]
    """Non-authoritative test evidence matches."""
    precedence_category: NotRequired[str]
    """Precedence classification for unresolved/ambiguous cases."""


# ============================================================================
# Style Guide & Section Contracts
# ============================================================================


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
    """

    task_files_scanned: int
    """Number of task files discovered."""
    tasks_scanned: int
    """Total task count across all scanned files."""
    recursive_task_includes: int
    """Number of nested task includes (import_tasks/include_tasks)."""
    unique_modules: str
    """Comma-separated list of distinct Ansible modules used."""
    external_collections: str
    """Comma-separated list of non-ansible.builtin collections."""
    handlers_notified: str
    """Comma-separated list of handlers notified by tasks."""
    privileged_tasks: int
    """Number of tasks using become/privilege escalation."""
    conditional_tasks: int
    """Number of tasks with when conditions."""
    tagged_tasks: int
    """Number of tasks with tags."""
    included_role_calls: int
    """Count of static role includes (import_role/include_role)."""
    included_roles: str
    """Comma-separated list of included role names."""
    dynamic_included_role_calls: int
    """Count of dynamic role includes (variables in include_role)."""
    dynamic_included_roles: str
    """Comma-separated list of dynamically included role names."""
    disabled_task_annotations: int
    """Count of disabled/commented task annotations."""
    yaml_like_task_annotations: int
    """Count of YAML-like format violations in task annotations."""


class StyleGuideConfig(TypedDict):
    """Typed contract for parsed style guide configuration.

    Captures rendered style guide metadata and configuration flowing through
    style-guide-based README rendering.
    """

    path: str
    """Absolute path to source style guide markdown file."""
    title_text: str
    """Parsed document title from style guide."""
    title_style: str
    """Heading style for document title ('atx' or 'setext')."""
    section_style: str
    """Heading style for section headings ('atx' or 'setext')."""
    section_level: int
    """Markdown level for section headings (2-6)."""
    sections: list[_StyleSection]
    """List of parsed section dicts (id, title, body, level, etc.)."""
    section_title_stats: _SectionTitleStats
    """Aggregated title statistics by section identifier."""
    variable_style: str
    """Variable section rendering format ('simple_list', 'yaml_block', 'table', 'nested_bullets')."""
    variable_intro: NotRequired[str | None]
    """Optional introductory text for variable section."""


# ============================================================================
# Scan Metadata & Context Contracts
# ============================================================================


class ReferenceContext(TypedDict):
    """Typed contract for variable reference context tracking and enrichment.

    Captures seed and dynamic variable reference data flowing through variable
    analysis pipelines.
    """

    seed_values: dict[str, Any]
    """Dict mapping variable names to resolved default values from external seed files."""
    seed_secrets: set[str]
    """Set of variable names flagged as sensitive/vaulted."""
    seed_sources: dict[str, str]
    """Dict mapping variable names to their source file paths."""
    dynamic_include_vars_refs: list[str]
    """List of raw dynamic include variable references."""
    dynamic_include_var_tokens: set[str]
    """Set of normalized variable name tokens from dynamic includes."""
    dynamic_task_include_tokens: set[str]
    """Set of normalized variable name tokens in dynamic task includes."""


class ScanPhaseError(TypedDict):
    """Structured scan phase failure metadata for degraded scan payloads."""

    phase: str
    """Logical scanner phase that failed (e.g., discovery, feature_detection)."""
    error_type: str
    """Exception class name."""
    message: str
    """Human-readable exception message."""


class ScanMetadata(TypedDict, total=False):
    """Comprehensive metadata contract flowing through scanner orchestration.

    Captures all scan-related metadata from initial artifact collection through
    output emission.
    """

    # Core identity & configuration
    molecule_scenarios: list[Any]
    """Detected Molecule test scenarios in role."""
    marker_prefix: str
    """Prefix for documentation markers (e.g., 'ansible_doc')."""
    detailed_catalog: bool
    """Whether to include detailed file catalogs."""
    include_task_parameters: bool
    """Include task module parameter documentation."""
    include_task_runbooks: bool
    """Include generated runbook content."""
    inline_task_runbooks: bool
    """Inline runbooks in role content (vs. separate)."""
    keep_unknown_style_sections: bool
    """Preserve unrecognized style guide sections."""

    # Role contents
    handlers: list[str]
    """List of handler file paths relative to role root."""
    tasks: list[str]
    """List of task file paths."""
    templates: list[str]
    """List of template file paths."""
    files: list[str]
    """List of static file paths."""
    tests: list[str]
    """List of test file paths."""
    defaults: list[str]
    """List of default variable file paths."""
    vars: list[str]
    """List of variable file paths."""
    meta: dict[str, Any]
    """Parsed role metadata (meta/main.yml as dict)."""
    features: FeaturesContext
    """Extracted role features."""

    # Dynamic includes
    unconstrained_dynamic_task_includes: list[Any]
    """Tasks with dynamic includes."""
    unconstrained_dynamic_role_includes: list[Any]
    """Roles with dynamic includes."""

    # README section configuration
    enabled_sections: list[str]
    """List of enabled README section identifiers."""
    section_title_overrides: NotRequired[dict[str, str]]
    """Custom section title overrides."""
    section_content_modes: NotRequired[dict[str, str]]
    """Section rendering mode overrides."""
    readme_section_config_warnings: NotRequired[list[str]]
    """Non-strict README section config parse warnings."""

    # Variable & issue analysis
    variable_insights: list[dict[str, Any]]
    """Analyzed variable metadata."""
    yaml_parse_failures: list[dict[str, object]]
    """YAML parsing error details."""
    role_notes: list[dict[str, Any]]
    """Extracted role notes from comments."""
    scanner_counters: dict[str, Any] | None
    """Comprehensive scanning metrics."""
    external_vars_context: NotRequired[dict[str, Any]]
    """Non-authoritative external variable context."""

    # Output & emission control
    concise_readme: NotRequired[bool]
    """Emit concise README mode."""
    include_scanner_report_link: NotRequired[bool]
    """Link to scanner report from README."""
    scanner_report_relpath: NotRequired[str]
    """Relative path to emitted scanner report."""

    # Compliance & styling
    collection_compliance_notes: NotRequired[Any]
    """Notes on collection requirement compliance."""
    style_guide: NotRequired[StyleGuideConfig]
    """Parsed style guide documentation."""
    style_guide_skeleton: NotRequired[bool]
    """Whether style guide is minimal skeleton."""
    comparison: NotRequired[dict[str, Any]]
    """Comparison report against baseline role."""

    # Annotation & error policy
    fail_on_unconstrained_dynamic_includes: bool
    """Strict enforcement mode."""
    fail_on_yaml_like_task_annotations: bool
    """Strict YAML-like annotation mode."""
    ignore_unresolved_internal_underscore_references: bool
    """Ignore pattern mode."""
    scan_errors: NotRequired[list[ScanPhaseError]]
    """Structured scan phase errors captured in best-effort mode."""
    scan_degraded: NotRequired[bool]
    """True when one or more scan phases failed and degraded output is emitted."""

    # Optional detailed catalogs
    task_catalog: NotRequired[list[Any]]
    """Detailed task-by-task catalog (only if detailed_catalog=True)."""
    handler_catalog: NotRequired[list[Any]]
    """Detailed handler-by-handler catalog (only if detailed_catalog=True)."""

    # Documentation insights
    doc_insights: dict[str, Any]
    """Aggregated documentation quality insights."""


class ScanContext(TypedDict):
    """Internal scan context consumed by output payload shaping."""

    display_variables: dict[str, Any]
    """Rendered variable list for output."""
    metadata: ScanMetadata
    """Scan metadata."""


class ScanBaseContext(TypedDict):
    """Typed return contract for _collect_scan_base_context.

    Stabilizes the internal seam between base-context collection and the
    prepare-scan-context orchestration step.
    """

    rp: str
    """Role path."""
    role_name: str
    """Role name."""
    description: str
    """Role description."""
    marker_prefix: str
    """Documentation marker prefix."""
    variables: dict[str, Any]
    """Discovered variables."""
    found: list[Any]
    """Found items (metadata, etc.)."""
    metadata: ScanMetadata
    """Scan metadata."""
    requirements_display: list[Any]
    """Rendered requirements list."""


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


# ============================================================================
# Output Payload Contracts
# ============================================================================


class RunScanOutputPayload(TypedDict):
    """Typed seam payload between run_scan orchestration and output rendering."""

    role_name: str
    """Role name."""
    description: str
    """Role description."""
    display_variables: dict[str, Any]
    """Rendered variable list."""
    requirements_display: list[Any]
    """Rendered requirements list."""
    undocumented_default_filters: list[Any]
    """Default filters without documentation."""
    metadata: ScanMetadata
    """Scan metadata."""


class EmitScanOutputsArgs(TypedDict):
    """Argument bundle for _emit_scan_outputs to reduce argument-drift risk."""

    output: str
    """Output file path."""
    output_format: str
    """Output format (markdown, html, json, etc.)."""
    concise_readme: bool
    """Emit concise README mode."""
    scanner_report_output: str | None
    """Scanner report output path (optional)."""
    include_scanner_report_link: bool
    """Link to scanner report from README."""
    role_name: str
    """Role name."""
    description: str
    """Role description."""
    display_variables: dict[str, Any]
    """Rendered variable list."""
    requirements_display: list[Any]
    """Rendered requirements list."""
    undocumented_default_filters: list[Any]
    """Default filters without documentation."""
    metadata: ScanMetadata
    """Scan metadata."""
    template: str | None
    """Template override path (optional)."""
    dry_run: bool
    """Perform dry run (no file writes)."""
    runbook_output: str | None
    """Runbook output path (optional)."""
    runbook_csv_output: str | None
    """Runbook CSV output path (optional)."""


class ScanReportSidecarArgs(TypedDict):
    """Argument bundle for _write_concise_scanner_report_if_enabled.

    Prevents argument-drift between _emit_scan_outputs and the sidecar emission
    helper.
    """

    concise_readme: bool
    """Emit concise README mode."""
    scanner_report_output: str | None
    """Scanner report output path (optional)."""
    out_path: Path
    """Main output path."""
    include_scanner_report_link: bool
    """Link to scanner report from README."""
    role_name: str
    """Role name."""
    description: str
    """Role description."""
    display_variables: dict[str, Any]
    """Rendered variable list."""
    requirements_display: list[Any]
    """Rendered requirements list."""
    undocumented_default_filters: list[Any]
    """Default filters without documentation."""
    metadata: ScanMetadata
    """Scan metadata."""
    dry_run: bool
    """Perform dry run (no file writes)."""


class RunbookSidecarArgs(TypedDict):
    """Argument bundle for _write_optional_runbook_outputs.

    Bundles the data fields so the call site in _emit_scan_outputs is a single
    structured object rather than scattered keyword arguments.
    """

    runbook_output: str | None
    """Runbook output path (optional)."""
    runbook_csv_output: str | None
    """Runbook CSV output path (optional)."""
    role_name: str
    """Role name."""
    metadata: ScanMetadata
    """Scan metadata."""


class FinalOutputPayload(TypedDict):
    """Typed payload passed into final output rendering."""

    role_name: str
    """Role name."""
    description: str
    """Role description."""
    variables: dict[str, Any]
    """Variable dictionary."""
    requirements: list[Any]
    """Requirements list."""
    default_filters: list[dict[str, Any]]
    """Default filter list."""
    metadata: dict[str, Any]
    """Metadata dictionary."""


# ============================================================================
# Scanner Report Contracts
# ============================================================================


class ScannerCounters(TypedDict):
    """Typed scanner counter payload used by report rendering and sidecars."""

    total_variables: int
    """Total variable count."""
    documented_variables: int
    """Documented variable count."""
    undocumented_variables: int
    """Undocumented variable count."""
    unresolved_variables: int
    """Unresolved variable count."""
    unresolved_noise_variables: int
    """Unresolved noise variable count."""
    ambiguous_variables: int
    """Ambiguous variable count."""
    secret_variables: int
    """Secret/sensitive variable count."""
    required_variables: int
    """Required variable count."""
    high_confidence_variables: int
    """High confidence variable count."""
    medium_confidence_variables: int
    """Medium confidence variable count."""
    low_confidence_variables: int
    """Low confidence variable count."""
    total_default_filters: int
    """Total default filter count."""
    undocumented_default_filters: int
    """Undocumented default filter count."""
    included_role_calls: int
    """Static role include count."""
    dynamic_included_role_calls: int
    """Dynamic role include count."""
    disabled_task_annotations: int
    """Disabled task annotation count."""
    yaml_like_task_annotations: int
    """YAML-like task annotation count."""
    yaml_parse_failures: int
    """YAML parse failure count."""
    non_authoritative_test_evidence_variables: int
    """Variables with non-authoritative test evidence."""
    non_authoritative_test_evidence_saturation_hits: int
    """Saturation hits in test evidence."""
    non_authoritative_test_evidence_budget_hits: int
    """Budget hits in test evidence."""
    provenance_issue_categories: dict[str, int]
    """Provenance issue counts by category."""


class ScannerReportMetadata(TypedDict, total=False):
    """Typed metadata contract consumed by scanner-report rendering helpers."""

    scanner_counters: ScannerCounters
    """Scanner counter payload."""
    variable_insights: list[dict[str, Any]]
    """Variable insights list."""
    features: dict[str, Any]
    """Features dictionary."""
    yaml_parse_failures: list[dict[str, object]]
    """YAML parse failure list."""


class ReadmeSectionRenderInput(TypedDict):
    """Typed contract for readme section rendering invocation inputs."""

    section_id: str
    """Section identifier."""
    role_name: str
    """Role name."""
    description: str
    """Role description."""
    variables: dict[str, Any]
    """Variables dictionary."""
    requirements: list[Any]
    """Requirements list."""
    default_filters: list[Any]
    """Default filters list."""
    metadata: ScannerReportMetadata
    """Scanner report metadata."""


class ScannerReportIssueListRow(TypedDict):
    """Typed contract for scanner report issue-list row rendering."""

    name: str
    """Variable/issue name."""
    uncertainty_reason: str | None
    """Uncertainty reason explanation."""


class ScannerReportYamlParseFailureRow(TypedDict):
    """Typed contract for scanner report YAML parse-failure row rendering."""

    location: str
    """File location of parse failure."""
    error: str
    """Error message."""


class AnnotationQualityCounters(TypedDict):
    """Typed annotation-quality counter payload extracted from scan features."""

    disabled_task_annotations: int
    """Disabled task annotation count."""
    yaml_like_task_annotations: int
    """YAML-like task annotation count."""


class ScannerReportSectionRenderInput(TypedDict):
    """Typed contract for scanner report section-title/body rendering."""

    title: str
    """Section title."""
    body: str
    """Section body content."""


class NormalizedScannerReportMetadata(TypedDict):
    """Typed optional-field normalization result for scanner-report metadata."""

    scanner_counters: ScannerCounters | None
    """Scanner counter payload (may be None)."""
    variable_insights: list[dict[str, Any]]
    """Variable insights list."""
    features: dict[str, Any]
    """Features dictionary."""
    yaml_parse_failures: list[dict[str, object]]
    """YAML parse failure list."""


class SectionBodyRenderResult(TypedDict):
    """Typed result of a readme section body renderer invocation."""

    body: str
    """Rendered section body."""
    has_content: bool
    """True if section has content to render."""


__all__ = [
    "AnnotationQualityCounters",
    "EmitScanOutputsArgs",
    "FeaturesContext",
    "FinalOutputPayload",
    "NormalizedScannerReportMetadata",
    "ReadmeSectionRenderInput",
    "ReferenceContext",
    "RunbookSidecarArgs",
    "RunScanOutputPayload",
    "ScanBaseContext",
    "ScanContext",
    "ScanContextPayload",
    "ScanMetadata",
    "ScanOptionsDict",
    "ScanPhaseError",
    "ScanReportSidecarArgs",
    "ScannerCounters",
    "ScannerReportIssueListRow",
    "ScannerReportMetadata",
    "ScannerReportSectionRenderInput",
    "ScannerReportYamlParseFailureRow",
    "SectionBodyRenderResult",
    "StyleGuideConfig",
    "Variable",
    "VariableProvenance",
    "VariableRow",
    "VariableRowWithMeta",
    "_SectionTitleBucket",
    "_StyleSection",
]
