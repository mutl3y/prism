"""Core scanner implementation.

This module provides utilities to scan an Ansible role for common
patterns (for example uses of the `default()` filter), load role
metadata and variables, and render a README using a Jinja2 template.
"""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path
import re
from typing import TypedDict

from .scanner_io import (
    render_final_output,
    write_output,
)
from .scanner_readme import build_doc_insights
from .scanner_config import (
    DEFAULT_DOC_MARKER_PREFIX as READMECFG_DEFAULT_DOC_MARKER_PREFIX,
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
    load_fail_on_unconstrained_dynamic_includes as _load_fail_on_unconstrained_dynamic_includes,
    load_fail_on_yaml_like_task_annotations as _load_fail_on_yaml_like_task_annotations,
    load_ignore_unresolved_internal_underscore_references as _load_ignore_unresolved_internal_underscore_references,
    load_non_authoritative_test_evidence_max_file_bytes as _load_non_authoritative_test_evidence_max_file_bytes,
    load_non_authoritative_test_evidence_max_files_scanned as _load_non_authoritative_test_evidence_max_files_scanned,
    load_non_authoritative_test_evidence_max_total_bytes as _load_non_authoritative_test_evidence_max_total_bytes,
    load_pattern_config,
    load_readme_marker_prefix as _load_readme_marker_prefix,
    load_readme_section_config as _load_readme_section_config,
    load_readme_section_visibility as _load_readme_section_visibility,
)
from .scanner_data.contracts import (
    EmitScanOutputsArgs as _scan_context_EmitScanOutputsArgs,
    ReferenceContext as _scan_context_ReferenceContext,
    RunScanOutputPayload as _scan_context_RunScanOutputPayload,
    ScanMetadata as _scan_context_ScanMetadata,
)
from .scanner_io.scan_output_emission import (
    write_optional_runbook_outputs as _scan_output_write_optional_runbook_outputs,
    write_concise_scanner_report_if_enabled as _scan_output_write_concise_scanner_report_if_enabled,
    emit_scan_outputs as _scan_output_emit_scan_outputs,
)
from .scanner_io.scan_output_primary import (
    render_and_write_scan_output as _scan_output_primary_render_and_write_scan_output,
    render_primary_scan_output as _scan_output_primary_render_primary_scan_output,
)
from .scanner_io.emit_output import (
    orchestrate_output_emission as _emit_output_orchestrate_output_emission,
)
from .scanner_core import DIContainer, ScanContextBuilder, ScannerContext
from .scanner_core import scan_request
from .scanner_core import scan_facade_helpers as _scan_facade_helpers
from .scanner_core import scan_runtime as _scan_runtime
from .scanner_core import variable_insights as _variable_insights
from .scanner_core import variable_pipeline as _variable_pipeline
from .scanner_analysis.metrics import (
    should_suppress_internal_unresolved_reference as _analysis_should_suppress_internal_unresolved_reference,
    build_referenced_variable_uncertainty_reason as _analysis_build_referenced_variable_uncertainty_reason,
    append_non_authoritative_test_evidence_uncertainty_reason as _analysis_append_non_authoritative_test_evidence_uncertainty_reason,
    collect_non_authoritative_test_variable_evidence as _analysis_collect_non_authoritative_test_variable_evidence,
    attach_non_authoritative_test_evidence as _analysis_attach_non_authoritative_test_evidence,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES as _ANALYSIS_MAX_FILE_BYTES,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED as _ANALYSIS_MAX_FILES_SCANNED,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES as _ANALYSIS_MAX_TOTAL_BYTES,
    NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT as _ANALYSIS_SATURATION_MATCH_COUNT,
)
from .scanner_config import (
    default_style_guide_user_paths as _config_default_style_guide_user_paths,
    load_section_display_titles as _config_load_section_display_titles,
    refresh_policy as _config_refresh_policy,
    resolve_default_style_guide_source as _config_resolve_default_style_guide_source,
    resolve_section_selector as _config_resolve_section_selector,
)
from .scanner_config.legacy_retirement import (
    LEGACY_RUNTIME_PATH_UNAVAILABLE as _RETIRED_RUNTIME_PATH_CODE,
    LEGACY_RUNTIME_PATH_UNAVAILABLE_MESSAGE as _RETIRED_RUNTIME_PATH_MESSAGE,
    LEGACY_RUNTIME_STYLE_SOURCE_ENV as _RETIRED_RUNTIME_STYLE_SOURCE_ENV,
    format_legacy_retirement_error as _format_retired_runtime_error,
)
from .scanner_io import (
    collect_yaml_parse_failures as _dataload_collect_yaml_parse_failures,
    iter_role_yaml_candidates as _dataload_iter_role_yaml_candidates,
    parse_yaml_candidate as _dataload_parse_yaml_candidate,
    map_argument_spec_type as _dataload_map_argument_spec_type,
)
from .scanner_extract import (
    load_role_variable_maps as _dataload_load_role_variable_maps,
    iter_role_argument_spec_entries as _dataload_iter_role_argument_spec_entries,
    format_requirement_line as _requirements_format_requirement_line,
    normalize_requirements as _requirements_normalize_requirements,
    normalize_meta_role_dependencies as _requirements_normalize_meta_role_dependencies,
    normalize_included_role_dependencies as _requirements_normalize_included_role_dependencies,
    extract_declared_collections_from_meta as _requirements_extract_declared_collections_from_meta,
    extract_declared_collections_from_requirements as _requirements_extract_declared_collections_from_requirements,
    build_collection_compliance_notes as _requirements_build_collection_compliance_notes,
    build_requirements_display as _runbook_report_build_requirements_display,
)
from .scanner_extract import (
    iter_role_variable_map_candidates as _scan_discovery_iter_role_variable_map_candidates,
    load_meta as _scan_discovery_load_meta,
    load_requirements as _scan_discovery_load_requirements,
    load_variables as _scan_discovery_load_variables,
    resolve_scan_identity as _scan_discovery_resolve_scan_identity,
)
from .scanner_analysis import (
    build_scanner_report_markdown as _runbook_report_build_scanner_report_markdown,
    extract_scanner_counters as _analysis_extract_scanner_counters,
    build_runbook_rows as _analysis_build_runbook_rows,
    classify_provenance_issue as _runbook_report_classify_provenance_issue,
    is_unresolved_noise_category as _runbook_report_is_unresolved_noise_category,
    render_runbook as _runbook_report_render_runbook,
    render_runbook_csv as _runbook_report_render_runbook_csv,
)
from .scanner_readme import (
    detect_style_section_level,
    format_heading,
    normalize_style_heading,
    parse_style_readme,
)
from .scanner_readme.input_parser import (
    collect_readme_input_variables as _readme_input_collect,
    extract_readme_input_variables as _readme_input_extract,
    extract_readme_variable_names_from_line as _readme_input_extract_names_from_line,
    is_readme_variable_section_heading_with as _readme_input_is_section_heading_with,
)
from ._jinja_analyzer import (
    _JINJA_AST_ENV as _JINJA_AST_ENV,
    _stringify_jinja_node as _stringify_jinja_node,
    _scan_text_for_all_filters_with_ast as _scan_text_for_all_filters_with_ast,
    _scan_text_for_default_filters_with_ast as _scan_text_for_default_filters_with_ast,
    _collect_undeclared_jinja_variables as _collect_undeclared_jinja_variables,
    _collect_undeclared_jinja_variables_from_ast as _collect_undeclared_jinja_variables_from_ast,
    _collect_jinja_local_bindings_from_text as _collect_jinja_local_bindings_from_text,
    _collect_jinja_local_bindings as _collect_jinja_local_bindings,
    _extract_jinja_name_targets as _extract_jinja_name_targets,
)
from .scanner_extract import (
    TASK_INCLUDE_KEYS as TASK_INCLUDE_KEYS,
    INCLUDE_VARS_KEYS as INCLUDE_VARS_KEYS,
    SET_FACT_KEYS as SET_FACT_KEYS,
    TASK_BLOCK_KEYS as TASK_BLOCK_KEYS,
    TASK_META_KEYS as TASK_META_KEYS,
    ROLE_NOTES_RE as ROLE_NOTES_RE,
    ROLE_NOTES_SHORT_RE as ROLE_NOTES_SHORT_RE,
    TASK_NOTES_LONG_RE as TASK_NOTES_LONG_RE,
    TASK_NOTES_SHORT_RE as TASK_NOTES_SHORT_RE,
    COMMENT_CONTINUATION_RE as COMMENT_CONTINUATION_RE,
    _normalize_exclude_patterns as _normalize_exclude_patterns,
    _is_relpath_excluded as _is_relpath_excluded,
    _is_path_excluded as _is_path_excluded,
    _format_inline_yaml as _format_inline_yaml,
    _load_yaml_file as _load_yaml_file,
    _iter_task_include_targets as _iter_task_include_targets,
    _iter_task_mappings as _iter_task_mappings,
    _resolve_task_include as _resolve_task_include,
    _collect_task_files as _collect_task_files,
    _extract_role_notes_from_comments as _extract_role_notes_from_comments,
    _split_task_annotation_label as _split_task_annotation_label,
    _extract_task_annotations_for_file as _extract_task_annotations_for_file,
    _task_anchor as _task_anchor,
    _detect_task_module as _detect_task_module,
    _extract_collection_from_module_name as _extract_collection_from_module_name,
    _compact_task_parameters as _compact_task_parameters,
    _collect_unconstrained_dynamic_role_includes as _collect_unconstrained_dynamic_role_includes,
    _collect_unconstrained_dynamic_task_includes as _collect_unconstrained_dynamic_task_includes,
    _collect_task_handler_catalog as _collect_task_handler_catalog,
    _collect_molecule_scenarios as _collect_molecule_scenarios,
    extract_role_features as extract_role_features,
)
from .scanner_extract import (
    DEFAULT_TARGET_RE as DEFAULT_TARGET_RE,
    JINJA_VAR_RE as JINJA_VAR_RE,
    JINJA_IDENTIFIER_RE as JINJA_IDENTIFIER_RE,
    VAULT_KEY_RE as VAULT_KEY_RE,
    IGNORED_IDENTIFIERS as IGNORED_IDENTIFIERS,
    _SECRET_NAME_TOKENS as _SECRET_NAME_TOKENS,
    _VAULT_MARKERS as _VAULT_MARKERS,
    _CREDENTIAL_PREFIXES as _CREDENTIAL_PREFIXES,
    _URL_PREFIXES as _URL_PREFIXES,
    _extract_default_target_var as _extract_default_target_var,
    _collect_include_vars_files as _collect_include_vars_files,
    _collect_set_fact_names as _collect_set_fact_names,
    _collect_register_names as _collect_register_names,
    _find_variable_line_in_yaml as _find_variable_line_in_yaml,
    _collect_dynamic_include_vars_refs as _collect_dynamic_include_vars_refs,
    _collect_dynamic_task_include_refs as _collect_dynamic_task_include_refs,
    _collect_referenced_variable_names as _collect_referenced_variable_names,
    _looks_secret_name as _looks_secret_name,
    _resembles_password_like as _resembles_password_like,
    _is_sensitive_variable as _is_sensitive_variable,
    _looks_secret_value as _looks_secret_value,
    _infer_variable_type as _infer_variable_type,
    _read_seed_yaml as _read_seed_yaml,
    _resolve_seed_var_files as _resolve_seed_var_files,
    load_seed_variables as load_seed_variables,
)
from .scanner_extract import filter_scanner as _filter_scanner
from .scanner_readme import (
    _describe_variable as _describe_variable,
    _is_role_local_variable_row as _is_role_local_variable_row,
    _render_role_notes_section as _render_role_notes_section,
    _render_role_variables_for_style as _render_role_variables_for_style,
    _render_template_overrides_section as _render_template_overrides_section,
    _render_variable_summary_section as _render_variable_summary_section,
    _render_variable_uncertainty_notes as _render_variable_uncertainty_notes,
)
from .scanner_readme import render_readme as _render_readme_mod_render_readme
from .scanner_compat import (
    append_scanner_report_section_if_enabled as _compat_append_scanner_report_section_if_enabled,
    compose_section_body as _compat_compose_section_body,
    generated_merge_markers as _compat_generated_merge_markers,
    render_guide_identity_sections as _compat_render_guide_identity_sections,
    render_guide_section_body as _compat_render_guide_section_body,
    render_readme_with_style_guide as _compat_render_readme_with_style_guide,
    resolve_ordered_style_sections as _compat_resolve_ordered_style_sections,
    resolve_section_content_mode as _compat_resolve_section_content_mode,
    strip_prior_generated_merge_block as _compat_strip_prior_generated_merge_block,
)


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


# Load pattern policy (built-in defaults, optionally merged with a repo override).
# Pass override_path to load_pattern_config() if you want to merge a local file.
_POLICY = load_pattern_config()

STYLE_SECTION_ALIASES: dict[str, str] = _POLICY["section_aliases"]

# Sensitivity detection tokens extracted from policy for fast tuple lookup
_SENSITIVITY = _POLICY["sensitivity"]

# Variable guidance priority keywords
_VARIABLE_GUIDANCE_KEYWORDS: tuple[str, ...] = tuple(
    _POLICY["variable_guidance"]["priority_keywords"]
)

DEFAULT_SECTION_SPECS = [
    ("galaxy_info", "Galaxy Info"),
    ("requirements", "Requirements"),
    ("purpose", "Role purpose and capabilities"),
    ("role_notes", "Role notes"),
    ("variable_summary", "Inputs / variables summary"),
    ("task_summary", "Task/module usage summary"),
    ("example_usage", "Inferred example usage"),
    ("role_variables", "Role Variables"),
    ("role_contents", "Role contents summary"),
    ("features", "Auto-detected role features"),
    ("comparison", "Comparison against local baseline role"),
    ("default_filters", "Detected usages of the default() filter"),
]

SCANNER_STATS_SECTION_IDS = {
    "task_summary",
    "role_contents",
    "features",
    "comparison",
    "default_filters",
}

_EXTRA_SECTION_IDS = {
    "basic_authorization",
    "handlers",
    "installation",
    "license",
    "author_information",
    "license_author",
    "sponsors",
    "template_overrides",
    "variable_guidance",
    "local_testing",
    "faq_pitfalls",
    "contributing",
    "scanner_report",
    "role_notes",
}
ALL_SECTION_IDS = {
    section_id for section_id, _ in DEFAULT_SECTION_SPECS
} | _EXTRA_SECTION_IDS

IGNORED_DIRS = (".git", "__pycache__", "venv", ".venv", "node_modules")
DEFAULT_RE = re.compile(
    r"""(?P<context>.{0,40}?)(\|\s*default\b|\bdefault\s*\()\s*(?P<args>[^)\n]{0,200})""",
    flags=re.IGNORECASE,
)
ANY_FILTER_RE = re.compile(r"""\|\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)""")

DEFAULT_STYLE_GUIDE_SOURCE_PATH = (
    Path(__file__).parent / "templates" / "STYLE_GUIDE_SOURCE.md"
)
DEFAULT_STYLE_GUIDE_SOURCE_FILENAME = "STYLE_GUIDE_SOURCE.md"
ENV_STYLE_GUIDE_SOURCE_PATH = "PRISM_STYLE_SOURCE"
XDG_DATA_HOME_ENV = "XDG_DATA_HOME"
STYLE_GUIDE_DATA_DIRNAME = "prism"
SYSTEM_STYLE_GUIDE_SOURCE_PATH = (
    Path("/var/lib") / STYLE_GUIDE_DATA_DIRNAME / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME
)
DEFAULT_SECTION_DISPLAY_TITLES_PATH = (
    Path(__file__).parent / "data" / "section_display_titles.yml"
)
DEFAULT_DOC_MARKER_PREFIX = READMECFG_DEFAULT_DOC_MARKER_PREFIX

NON_AUTHORITATIVE_TEST_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NON_AUTHORITATIVE_TEST_EVIDENCE_ALLOWED_SUFFIXES = {
    ".yml",
    ".yaml",
    ".j2",
    ".jinja2",
    ".json",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
}
# Note: these constants are now defined in scanner_analysis/metrics.py
# and re-exported here for backward compatibility.
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES = _ANALYSIS_MAX_FILE_BYTES
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED = _ANALYSIS_MAX_FILES_SCANNED
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES = _ANALYSIS_MAX_TOTAL_BYTES
NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT = (
    _ANALYSIS_SATURATION_MATCH_COUNT
)


def _refresh_policy(override_path: str | None = None) -> None:
    """Reload policy-derived globals with an optional explicit override path."""
    global _POLICY
    global STYLE_SECTION_ALIASES
    global _SENSITIVITY
    global _SECRET_NAME_TOKENS
    global _VAULT_MARKERS
    global _CREDENTIAL_PREFIXES
    global _URL_PREFIXES
    global _VARIABLE_GUIDANCE_KEYWORDS
    global IGNORED_IDENTIFIERS

    (
        _POLICY,
        STYLE_SECTION_ALIASES,
        _SECRET_NAME_TOKENS,
        _VAULT_MARKERS,
        _CREDENTIAL_PREFIXES,
        _URL_PREFIXES,
        _VARIABLE_GUIDANCE_KEYWORDS,
        IGNORED_IDENTIFIERS,
    ) = _config_refresh_policy(override_path=override_path)
    _SENSITIVITY = _POLICY["sensitivity"]

    from .scanner_extract import variable_extractor as _ve

    _ve._refresh_policy_derived_state(_POLICY)
    IGNORED_IDENTIFIERS = _ve.IGNORED_IDENTIFIERS


def _normalize_style_heading(heading: str) -> str:
    """Backward-compatible alias for style heading normalization."""
    return normalize_style_heading(heading)


def _detect_style_section_level(lines: list[str]) -> int:
    """Backward-compatible alias for style section-level detection."""
    return detect_style_section_level(lines)


def _format_heading(text: str, level: int, style: str) -> str:
    """Backward-compatible alias for heading formatting."""
    return format_heading(text, level, style)


def _default_style_guide_user_paths() -> list[Path]:
    """Return user-level style guide paths honoring XDG conventions."""
    return _config_default_style_guide_user_paths(
        xdg_data_home_env=XDG_DATA_HOME_ENV,
        style_guide_data_dirname=STYLE_GUIDE_DATA_DIRNAME,
        style_guide_source_filename=DEFAULT_STYLE_GUIDE_SOURCE_FILENAME,
    )


def resolve_default_style_guide_source(explicit_path: str | None = None) -> str:
    """Resolve default style guide source path using Linux-aware precedence.

    Precedence (first existing path wins):

     1. ``$PRISM_STYLE_SOURCE``
         2. ``./STYLE_GUIDE_SOURCE.md``
         3. ``$XDG_DATA_HOME/prism/STYLE_GUIDE_SOURCE.md``
       (or ``~/.local/share/...`` fallback)
         4. ``/var/lib/prism/STYLE_GUIDE_SOURCE.md``
         5. bundled package template path
    """
    return _config_resolve_default_style_guide_source(
        explicit_path=explicit_path,
        env_style_guide_source_path=ENV_STYLE_GUIDE_SOURCE_PATH,
        xdg_data_home_env=XDG_DATA_HOME_ENV,
        style_guide_data_dirname=STYLE_GUIDE_DATA_DIRNAME,
        style_guide_source_filename=DEFAULT_STYLE_GUIDE_SOURCE_FILENAME,
        system_style_guide_source_path=SYSTEM_STYLE_GUIDE_SOURCE_PATH,
        default_style_guide_source_path=DEFAULT_STYLE_GUIDE_SOURCE_PATH,
    )


def scan_for_default_filters(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list:
    """Scan files under ``role_path`` for uses of the ``default()`` filter.

    Returns a list of occurrence dictionaries with keys: ``file``,
    ``line_no``, ``line``, ``match`` and ``args``.
    """
    return _filter_scanner.scan_for_default_filters(
        role_path,
        exclude_paths=exclude_paths,
        ignored_dirs=IGNORED_DIRS,
        collect_task_files=_collect_task_files,
        is_relpath_excluded=_is_relpath_excluded,
        is_path_excluded=_is_path_excluded,
        scan_file_for_default_filters=_scan_file_for_default_filters,
    )


def scan_for_all_filters(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict]:
    """Scan files under ``role_path`` for all discovered Jinja filters.

    Returns a list of occurrence dictionaries with keys: ``file``,
    ``line_no``, ``line``, ``match``, ``args`` and ``filter_name``.
    """
    return _filter_scanner.scan_for_all_filters(
        role_path,
        exclude_paths=exclude_paths,
        ignored_dirs=IGNORED_DIRS,
        collect_task_files=_collect_task_files,
        is_relpath_excluded=_is_relpath_excluded,
        is_path_excluded=_is_path_excluded,
        scan_file_for_all_filters=_scan_file_for_all_filters,
    )


def _scan_file_for_default_filters(file_path: Path, role_root: Path) -> list[dict]:
    """Scan a single file for uses of the ``default()`` filter."""
    return _filter_scanner.scan_file_for_default_filters(
        file_path,
        role_root,
        default_re=DEFAULT_RE,
        scan_text_for_default_filters_with_ast=_scan_text_for_default_filters_with_ast,
    )


def _scan_file_for_all_filters(file_path: Path, role_root: Path) -> list[dict]:
    """Scan a single file for uses of any Jinja filter."""
    return _filter_scanner.scan_file_for_all_filters(
        file_path,
        role_root,
        any_filter_re=ANY_FILTER_RE,
        scan_text_for_all_filters_with_ast=_scan_text_for_all_filters_with_ast,
    )


def _collect_yaml_parse_failures(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, object]]:
    """Collect YAML parse failures with file/line context across a role tree."""
    return _dataload_collect_yaml_parse_failures(
        role_path,
        exclude_paths,
        iter_yaml_candidates_fn=lambda role_root, exclude_paths: _dataload_iter_role_yaml_candidates(
            role_root,
            exclude_paths=exclude_paths,
            ignored_dirs=IGNORED_DIRS,
            is_relpath_excluded_fn=_is_relpath_excluded,
            is_path_excluded_fn=_is_path_excluded,
        ),
    )


def _iter_role_yaml_candidates(
    role_root: Path,
    *,
    exclude_paths: list[str] | None,
):
    """Yield role-local YAML files while honoring ignored and excluded paths."""
    yield from _dataload_iter_role_yaml_candidates(
        role_root,
        exclude_paths=exclude_paths,
        ignored_dirs=IGNORED_DIRS,
        is_relpath_excluded_fn=_is_relpath_excluded,
        is_path_excluded_fn=_is_path_excluded,
    )


def _parse_yaml_candidate(candidate: Path, role_root: Path) -> dict[str, object] | None:
    """Parse one YAML candidate and return a failure payload when parsing fails."""
    return _dataload_parse_yaml_candidate(candidate, role_root)


def _is_readme_variable_section_heading(title: str) -> bool:
    return _readme_input_is_section_heading_with(
        title,
        normalize_heading=normalize_style_heading,
        section_aliases=STYLE_SECTION_ALIASES,
    )


_extract_readme_input_variables = _readme_input_extract
_extract_readme_variable_names_from_line = _readme_input_extract_names_from_line
_collect_readme_input_variables = _readme_input_collect


load_meta = _scan_discovery_load_meta


def _iter_role_argument_spec_entries(role_path: str):
    """Yield argument spec variable entries discovered in role metadata files.

    Supported layouts:
    - ``meta/argument_specs.yml`` with top-level ``argument_specs`` mapping
    - ``meta/main.yml`` with embedded ``argument_specs`` mapping
    """
    yield from _dataload_iter_role_argument_spec_entries(
        role_path,
        load_yaml_file_fn=_load_yaml_file,
        load_meta_fn=load_meta,
    )


def _map_argument_spec_type(spec_type: object) -> str:
    """Map argument-spec type labels into scanner variable type labels."""
    return _dataload_map_argument_spec_type(spec_type)


_iter_role_variable_map_candidates = _scan_discovery_iter_role_variable_map_candidates


def load_variables(
    role_path: str,
    include_vars_main: bool = True,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Load variables from ``defaults/main.yml``, ``vars/main.yml``, and any
    additional vars files referenced by static ``include_vars`` tasks.

    Values from ``vars`` override values from ``defaults`` when both are
    present.  ``include_vars``-referenced files are merged last (later files
    override earlier ones).  Returns a flat dict of all discovered variables.
    """
    return _scan_discovery_load_variables(
        role_path,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_paths,
        collect_include_vars_files=lambda resolved_role_path, resolved_exclude_paths: _collect_include_vars_files(
            resolved_role_path,
            exclude_paths=resolved_exclude_paths,
        ),
    )


load_requirements = _scan_discovery_load_requirements


_format_requirement_line = _requirements_format_requirement_line


normalize_requirements = _requirements_normalize_requirements


_normalize_meta_role_dependencies = _requirements_normalize_meta_role_dependencies
_normalize_included_role_dependencies = (
    _requirements_normalize_included_role_dependencies
)
_extract_declared_collections_from_meta = (
    _requirements_extract_declared_collections_from_meta
)
_extract_declared_collections_from_requirements = (
    _requirements_extract_declared_collections_from_requirements
)
_build_collection_compliance_notes = _requirements_build_collection_compliance_notes


def collect_role_contents(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Collect lists of files from common role subdirectories."""
    return _scan_facade_helpers.collect_role_contents(
        role_path=role_path,
        exclude_paths=exclude_paths,
        is_path_excluded=_is_path_excluded,
        load_meta=load_meta,
        extract_role_features=extract_role_features,
    )


def _compute_quality_metrics(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    return _scan_facade_helpers.compute_quality_metrics(
        role_path=role_path,
        exclude_paths=exclude_paths,
        collect_role_contents=collect_role_contents,
        load_variables=load_variables,
        scan_for_default_filters=scan_for_default_filters,
    )


def build_comparison_report(
    target_role_path: str,
    baseline_role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    return _scan_facade_helpers.build_comparison_report(
        target_role_path=target_role_path,
        baseline_role_path=baseline_role_path,
        exclude_paths=exclude_paths,
        compute_quality_metrics=_compute_quality_metrics,
    )


def _load_role_variable_maps(
    role_path: str,
    include_vars_main: bool,
) -> tuple[dict, dict, dict[str, Path], dict[str, Path]]:
    """Load defaults/vars variable maps from conventional role paths."""
    return _dataload_load_role_variable_maps(
        role_path,
        include_vars_main,
        iter_variable_map_candidates_fn=_iter_role_variable_map_candidates,
        load_yaml_file_fn=_load_yaml_file,
    )


def _collect_dynamic_task_include_tokens(
    role_path: str,
    exclude_paths: list[str] | None,
) -> set[str]:
    """Collect unresolved Jinja identifier tokens from dynamic task includes."""
    return _variable_pipeline.collect_dynamic_task_include_tokens(
        role_path=role_path,
        exclude_paths=exclude_paths,
    )


def _collect_dynamic_include_var_tokens(
    dynamic_include_vars_refs: list[str],
) -> set[str]:
    """Collect unresolved Jinja identifier tokens from dynamic include_vars refs."""
    return _variable_pipeline.collect_dynamic_include_var_tokens(
        dynamic_include_vars_refs=dynamic_include_vars_refs,
    )


def _build_static_variable_rows(
    *,
    role_root: Path,
    defaults_data: dict,
    vars_data: dict,
    defaults_sources: dict[str, Path],
    vars_sources: dict[str, Path],
) -> tuple[list[dict], dict[str, dict]]:
    """Build baseline rows from defaults/main.yml and vars/main.yml."""
    return _variable_pipeline.build_static_variable_rows(
        role_root=role_root,
        defaults_data=defaults_data,
        vars_data=vars_data,
        defaults_sources=defaults_sources,
        vars_sources=vars_sources,
    )


def _append_include_vars_rows(
    *,
    role_path: str,
    role_root: Path,
    rows: list[dict],
    rows_by_name: dict[str, dict],
    exclude_paths: list[str] | None,
) -> set[str]:
    """Merge include_vars-derived values into variable insight rows."""
    return _variable_pipeline.append_include_vars_rows(
        role_path=role_path,
        role_root=role_root,
        rows=rows,
        rows_by_name=rows_by_name,
        exclude_paths=exclude_paths,
    )


def _collect_include_var_sources(
    *,
    role_path: str,
    role_root: Path,
    exclude_paths: list[str] | None,
) -> dict[str, list[dict]]:
    """Collect include_vars value sources keyed by variable name."""
    return _variable_pipeline.collect_include_var_sources(
        role_path=role_path,
        role_root=role_root,
        exclude_paths=exclude_paths,
    )


def _mark_existing_row_as_include_vars_ambiguous(
    row: dict, entries: list[dict]
) -> None:
    """Downgrade confidence for rows that can be overridden by include_vars."""
    _variable_pipeline.mark_existing_row_as_include_vars_ambiguous(row, entries)


def _build_include_vars_row(name: str, entries: list[dict]) -> dict:
    """Build a variable insight row for include_vars-discovered variables."""
    return _variable_pipeline.build_include_vars_row(name=name, entries=entries)


def _append_set_fact_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
    exclude_paths: list[str] | None,
) -> None:
    """Append computed variable placeholders discovered from set_fact usage."""
    _variable_pipeline.append_set_fact_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        exclude_paths=exclude_paths,
    )


def _append_register_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
    exclude_paths: list[str] | None,
) -> None:
    """Append runtime placeholders for task-level register variables."""
    _variable_pipeline.append_register_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        exclude_paths=exclude_paths,
    )


def _append_readme_documented_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
    style_readme_path: str | None = None,
) -> None:
    """Enrich existing variable rows with README documentation.

    README is used for enrichment only - it does NOT create new variable rows.
    Variables must exist in defaults/vars/meta/references to be tracked.
    """
    _variable_pipeline.append_readme_documented_rows(
        role_path=role_path,
        rows=rows,
        style_readme_path=style_readme_path,
    )


def _append_argument_spec_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
) -> set[str]:
    """Append argument_specs-declared inputs not yet present in row set."""
    return _variable_pipeline.append_argument_spec_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        map_argument_spec_type=_map_argument_spec_type,
    )


def _append_referenced_variable_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
    seed_values: dict,
    seed_secrets: set[str],
    seed_sources: dict,
    dynamic_include_vars_refs: list[str],
    dynamic_include_var_tokens: set[str],
    dynamic_task_include_tokens: set[str],
    ignore_unresolved_internal_underscore_references: bool,
    exclude_paths: list[str] | None,
) -> None:
    """Append rows for referenced-but-undefined variable names."""
    _variable_pipeline.append_referenced_variable_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        seed_values=seed_values,
        seed_secrets=seed_secrets,
        seed_sources=seed_sources,
        dynamic_include_vars_refs=dynamic_include_vars_refs,
        dynamic_include_var_tokens=dynamic_include_var_tokens,
        dynamic_task_include_tokens=dynamic_task_include_tokens,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        exclude_paths=exclude_paths,
    )


_should_suppress_internal_unresolved_reference = (
    _analysis_should_suppress_internal_unresolved_reference
)


_build_referenced_variable_uncertainty_reason = (
    _analysis_build_referenced_variable_uncertainty_reason
)


_append_non_authoritative_test_evidence_uncertainty_reason = (
    _analysis_append_non_authoritative_test_evidence_uncertainty_reason
)


_collect_non_authoritative_test_variable_evidence = (
    _analysis_collect_non_authoritative_test_variable_evidence
)


_attach_non_authoritative_test_evidence = (
    _analysis_attach_non_authoritative_test_evidence
)


def _collect_variable_reference_context(
    *,
    role_path: str,
    seed_paths: list[str] | None,
    exclude_paths: list[str] | None,
) -> _scan_context_ReferenceContext:
    """Collect seed and dynamic-reference context for inferred variable rows."""
    return _variable_pipeline.collect_variable_reference_context(
        role_path=role_path,
        seed_paths=seed_paths,
        exclude_paths=exclude_paths,
        load_seed_variables=load_seed_variables,
    )


def _populate_variable_rows(
    *,
    role_path: str,
    rows: list[dict],
    rows_by_name: dict,
    exclude_paths: list[str] | None,
    reference_context: _scan_context_ReferenceContext,
    style_readme_path: str | None = None,
    ignore_unresolved_internal_underscore_references: bool = True,
    non_authoritative_test_evidence_max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    non_authoritative_test_evidence_max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    non_authoritative_test_evidence_max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> None:
    """Populate dynamic, documented, and inferred variable rows in-place."""
    _variable_pipeline.populate_variable_rows(
        role_path=role_path,
        rows=rows,
        rows_by_name=rows_by_name,
        exclude_paths=exclude_paths,
        reference_context=reference_context,
        map_argument_spec_type=_map_argument_spec_type,
        style_readme_path=style_readme_path,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        non_authoritative_test_evidence_max_file_bytes=(
            non_authoritative_test_evidence_max_file_bytes
        ),
        non_authoritative_test_evidence_max_files_scanned=(
            non_authoritative_test_evidence_max_files_scanned
        ),
        non_authoritative_test_evidence_max_total_bytes=(
            non_authoritative_test_evidence_max_total_bytes
        ),
    )


def _refresh_known_names(rows: list[dict]) -> set[str]:
    """Return a set of known variable names from row payloads."""
    return _variable_pipeline.refresh_known_names(rows)


def _redact_secret_defaults(rows: list[dict]) -> None:
    """Mask secret defaults in-place before rendering/output."""
    _variable_pipeline.redact_secret_defaults(rows)


def build_variable_insights(
    role_path: str,
    seed_paths: list[str] | None = None,
    include_vars_main: bool = True,
    exclude_paths: list[str] | None = None,
    style_readme_path: str | None = None,
    ignore_unresolved_internal_underscore_references: bool = True,
    non_authoritative_test_evidence_max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    non_authoritative_test_evidence_max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    non_authoritative_test_evidence_max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> list[dict]:
    """Build variable rows with inferred type/default/source details."""
    return _variable_insights.build_variable_insights(
        role_path,
        seed_paths=seed_paths,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_paths,
        style_readme_path=style_readme_path,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        non_authoritative_test_evidence_max_file_bytes=(
            non_authoritative_test_evidence_max_file_bytes
        ),
        non_authoritative_test_evidence_max_files_scanned=(
            non_authoritative_test_evidence_max_files_scanned
        ),
        non_authoritative_test_evidence_max_total_bytes=(
            non_authoritative_test_evidence_max_total_bytes
        ),
        load_role_variable_maps=_load_role_variable_maps,
        collect_variable_reference_context=_collect_variable_reference_context,
        build_static_variable_rows=_build_static_variable_rows,
        populate_variable_rows=_populate_variable_rows,
        redact_secret_defaults=_redact_secret_defaults,
    )


_resolve_section_selector = partial(
    _config_resolve_section_selector,
    all_section_ids=ALL_SECTION_IDS,
    style_section_aliases=STYLE_SECTION_ALIASES,
    normalize_heading_fn=normalize_style_heading,
)


def _load_section_display_titles() -> dict[str, str]:
    return _config_load_section_display_titles(DEFAULT_SECTION_DISPLAY_TITLES_PATH)


load_readme_marker_prefix = partial(
    _load_readme_marker_prefix,
    default_prefix=DEFAULT_DOC_MARKER_PREFIX,
    config_filenames=SECTION_CONFIG_FILENAMES,
    default_filename=SECTION_CONFIG_FILENAME,
)


def load_fail_on_unconstrained_dynamic_includes(
    role_path: str,
    config_path: str | None = None,
    default: bool = False,
) -> bool:
    return _load_fail_on_unconstrained_dynamic_includes(
        role_path,
        config_path=config_path,
        default=default,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_fail_on_yaml_like_task_annotations(
    role_path: str,
    config_path: str | None = None,
    default: bool = False,
) -> bool:
    return _load_fail_on_yaml_like_task_annotations(
        role_path,
        config_path=config_path,
        default=default,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_ignore_unresolved_internal_underscore_references(
    role_path: str,
    config_path: str | None = None,
    default: bool = True,
) -> bool:
    return _load_ignore_unresolved_internal_underscore_references(
        role_path,
        config_path=config_path,
        default=default,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_non_authoritative_test_evidence_max_file_bytes(
    role_path: str,
    config_path: str | None = None,
    default: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
) -> int:
    return _load_non_authoritative_test_evidence_max_file_bytes(
        role_path,
        config_path=config_path,
        default=default,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_non_authoritative_test_evidence_max_files_scanned(
    role_path: str,
    config_path: str | None = None,
    default: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
) -> int:
    return _load_non_authoritative_test_evidence_max_files_scanned(
        role_path,
        config_path=config_path,
        default=default,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_non_authoritative_test_evidence_max_total_bytes(
    role_path: str,
    config_path: str | None = None,
    default: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> int:
    return _load_non_authoritative_test_evidence_max_total_bytes(
        role_path,
        config_path=config_path,
        default=default,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_readme_section_visibility(
    role_path: str,
    config_path: str | None = None,
) -> set[str] | None:
    return _load_readme_section_visibility(
        role_path=role_path,
        config_path=config_path,
        adopt_heading_mode=None,
        all_section_ids=ALL_SECTION_IDS,
        section_aliases=STYLE_SECTION_ALIASES,
        normalize_heading=normalize_style_heading,
        display_titles_path=DEFAULT_SECTION_DISPLAY_TITLES_PATH,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_readme_section_config(
    role_path: str,
    config_path: str | None = None,
    adopt_heading_mode: str | None = None,
) -> dict | None:
    return _load_readme_section_config(
        role_path=role_path,
        config_path=config_path,
        adopt_heading_mode=adopt_heading_mode,
        all_section_ids=ALL_SECTION_IDS,
        section_aliases=STYLE_SECTION_ALIASES,
        normalize_heading=normalize_style_heading,
        display_titles_path=DEFAULT_SECTION_DISPLAY_TITLES_PATH,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


_render_guide_identity_sections = _compat_render_guide_identity_sections


_render_guide_section_body = partial(
    _compat_render_guide_section_body,
    variable_guidance_keywords=_VARIABLE_GUIDANCE_KEYWORDS,
)


_generated_merge_markers = _compat_generated_merge_markers
_strip_prior_generated_merge_block = _compat_strip_prior_generated_merge_block
_resolve_section_content_mode = _compat_resolve_section_content_mode
_compose_section_body = _compat_compose_section_body
_resolve_ordered_style_sections = _compat_resolve_ordered_style_sections
_append_scanner_report_section_if_enabled = (
    _compat_append_scanner_report_section_if_enabled
)
_render_readme_with_style_guide = _compat_render_readme_with_style_guide


_build_scanner_report_markdown = partial(
    _runbook_report_build_scanner_report_markdown,
    render_section_body=_render_guide_section_body,
)


_extract_scanner_counters = _analysis_extract_scanner_counters


_classify_provenance_issue = _runbook_report_classify_provenance_issue


_is_unresolved_noise_category = _runbook_report_is_unresolved_noise_category


def render_readme(
    output: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    template: str | None = None,
    metadata: dict | None = None,
    write: bool = True,
) -> str:
    """Compatibility wrapper for extracted README rendering helpers."""
    return _render_readme_mod_render_readme(
        output=output,
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        template=template,
        metadata=metadata,
        write=write,
    )


render_runbook = _runbook_report_render_runbook


_build_runbook_rows = _analysis_build_runbook_rows


render_runbook_csv = _runbook_report_render_runbook_csv


_build_requirements_display = _runbook_report_build_requirements_display


def _write_concise_scanner_report_if_enabled(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    role_name: str,
    description: str,
    display_variables: dict,
    requirements_display: list,
    undocumented_default_filters: list,
    metadata: dict,
    dry_run: bool,
) -> Path | None:
    """Write scanner sidecar report when concise mode is enabled."""
    return _scan_output_write_concise_scanner_report_if_enabled(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        role_name=role_name,
        description=description,
        display_variables=display_variables,
        requirements_display=requirements_display,
        undocumented_default_filters=undocumented_default_filters,
        metadata=metadata,
        dry_run=dry_run,
        build_scanner_report_markdown=_build_scanner_report_markdown,
    )


_resolve_scan_identity = partial(
    _scan_discovery_resolve_scan_identity,
    load_meta_fn=load_meta,
)


_collect_scan_artifacts = partial(
    _scan_facade_helpers.collect_scan_artifacts,
    load_variables=load_variables,
    load_requirements=load_requirements,
    scan_for_default_filters=scan_for_default_filters,
    collect_role_contents=collect_role_contents,
    collect_molecule_scenarios=_collect_molecule_scenarios,
    collect_unconstrained_dynamic_task_includes=(
        _collect_unconstrained_dynamic_task_includes
    ),
    collect_unconstrained_dynamic_role_includes=(
        _collect_unconstrained_dynamic_role_includes
    ),
    collect_task_handler_catalog=_collect_task_handler_catalog,
)


def _write_optional_runbook_outputs(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    role_name: str,
    metadata: dict,
) -> None:
    """Write standalone runbook outputs when requested."""
    _scan_output_write_optional_runbook_outputs(
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        role_name=role_name,
        metadata=metadata,
        render_runbook=render_runbook,
        render_runbook_csv=render_runbook_csv,
    )


def _emit_output_orchestration(args: dict) -> str:
    """Orchestrate output emission (primary + sidecars) for a scanner run."""
    return _emit_output_orchestrate_output_emission(
        args=args,
        render_and_write=_render_and_write_scan_output,
        render_scanner_report=_build_scanner_report_markdown,
        render_runbook=render_runbook,
        render_runbook_csv=render_runbook_csv,
    )


_write_concise_scanner_report_if_enabled = partial(
    _scan_output_write_concise_scanner_report_if_enabled,
    build_scanner_report_markdown=_build_scanner_report_markdown,
)


_write_optional_runbook_outputs = partial(
    _scan_output_write_optional_runbook_outputs,
    render_runbook=render_runbook,
    render_runbook_csv=render_runbook_csv,
)


def _apply_readme_section_config(
    metadata: _scan_context_ScanMetadata, readme_section_config: dict | None
) -> None:
    """Apply resolved README section configuration into scan metadata."""
    if readme_section_config is None:
        return
    metadata["enabled_sections"] = sorted(readme_section_config["enabled_sections"])
    if readme_section_config["section_title_overrides"]:
        metadata["section_title_overrides"] = dict(
            readme_section_config["section_title_overrides"]
        )
    if readme_section_config["section_content_modes"]:
        metadata["section_content_modes"] = dict(
            readme_section_config["section_content_modes"]
        )


_attach_external_vars_context = _variable_insights.attach_external_vars_context


_build_undocumented_default_filters = partial(
    _variable_insights.build_undocumented_default_filters,
    extract_default_target_var=_extract_default_target_var,
    looks_secret_name=_looks_secret_name,
    resembles_password_like=_resembles_password_like,
)


_build_display_variables = _variable_insights.build_display_variables


_collect_variable_insights_and_default_filter_findings = partial(
    _variable_insights.collect_variable_insights_and_default_filter_findings,
    build_variable_insights=build_variable_insights,
    attach_external_vars_context=_attach_external_vars_context,
    collect_yaml_parse_failures=_collect_yaml_parse_failures,
    extract_role_notes_from_comments=_extract_role_notes_from_comments,
    build_undocumented_default_filters=_build_undocumented_default_filters,
    extract_scanner_counters=_extract_scanner_counters,
    build_display_variables=_build_display_variables,
)


_apply_style_and_comparison_metadata = partial(
    _scan_facade_helpers.apply_style_and_comparison_metadata,
    resolve_default_style_guide_source=resolve_default_style_guide_source,
    parse_style_readme=parse_style_readme,
    build_comparison_report=build_comparison_report,
)


def _render_and_write_scan_output(
    *,
    out_path: Path,
    output_format: str,
    role_name: str,
    description: str,
    display_variables: dict,
    requirements_display: list,
    undocumented_default_filters: list[dict],
    metadata: dict,
    template: str | None,
    dry_run: bool,
) -> str:
    """Render final output payload and write it unless dry-run is enabled."""
    return _scan_output_primary_render_and_write_scan_output(
        out_path=out_path,
        output_format=output_format,
        role_name=role_name,
        description=description,
        display_variables=display_variables,
        requirements_display=requirements_display,
        undocumented_default_filters=undocumented_default_filters,
        metadata=metadata,
        template=template,
        dry_run=dry_run,
        render_readme=render_readme,
        render_final_output=render_final_output,
        write_output=write_output,
    )


_apply_unconstrained_dynamic_include_policy = partial(
    _scan_runtime.apply_unconstrained_dynamic_include_policy,
    load_fail_on_unconstrained_dynamic_includes=(
        load_fail_on_unconstrained_dynamic_includes
    ),
)


_apply_yaml_like_task_annotation_policy = partial(
    _scan_runtime.apply_yaml_like_task_annotation_policy,
    load_fail_on_yaml_like_task_annotations=(load_fail_on_yaml_like_task_annotations),
)


_finalize_scan_context_payload = _scan_runtime.finalize_scan_context_payload


_collect_scan_identity_and_artifacts = partial(
    _scan_runtime.collect_scan_identity_and_artifacts,
    resolve_scan_identity=_resolve_scan_identity,
    load_readme_marker_prefix=load_readme_marker_prefix,
    collect_scan_artifacts=_collect_scan_artifacts,
)


_apply_scan_metadata_configuration = partial(
    _scan_runtime.apply_scan_metadata_configuration,
    build_requirements_display=_build_requirements_display,
    load_readme_section_config=load_readme_section_config,
    apply_readme_section_config=_apply_readme_section_config,
)


_collect_scan_base_context = partial(
    _scan_runtime.collect_scan_base_context,
    collect_scan_identity_and_artifacts=_collect_scan_identity_and_artifacts,
    apply_scan_metadata_configuration=_apply_scan_metadata_configuration,
    apply_unconstrained_dynamic_include_policy=_apply_unconstrained_dynamic_include_policy,
    apply_yaml_like_task_annotation_policy=_apply_yaml_like_task_annotation_policy,
)


_enrich_scan_context_with_insights = partial(
    _scan_runtime.enrich_scan_context_with_insights,
    collect_variable_insights_and_default_filter_findings=(
        _collect_variable_insights_and_default_filter_findings
    ),
    build_doc_insights=build_doc_insights,
    apply_style_and_comparison_metadata=_apply_style_and_comparison_metadata,
)


_prepare_scan_context = partial(
    _scan_runtime.prepare_scan_context,
    scan_context_builder_cls=ScanContextBuilder,
    collect_scan_base_context=_collect_scan_base_context,
    load_ignore_unresolved_internal_underscore_references=(
        load_ignore_unresolved_internal_underscore_references
    ),
    load_non_authoritative_test_evidence_max_file_bytes=(
        load_non_authoritative_test_evidence_max_file_bytes
    ),
    load_non_authoritative_test_evidence_max_files_scanned=(
        load_non_authoritative_test_evidence_max_files_scanned
    ),
    load_non_authoritative_test_evidence_max_total_bytes=(
        load_non_authoritative_test_evidence_max_total_bytes
    ),
    enrich_scan_context_with_insights=_enrich_scan_context_with_insights,
    finalize_scan_context_payload=_finalize_scan_context_payload,
    non_authoritative_test_evidence_max_file_bytes=(
        NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES
    ),
    non_authoritative_test_evidence_max_files_scanned=(
        NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED
    ),
    non_authoritative_test_evidence_max_total_bytes=(
        NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES
    ),
)


_build_scan_output_payload = _scan_runtime.build_scan_output_payload


_build_emit_scan_outputs_args = _scan_runtime.build_emit_scan_outputs_args


_build_scan_report_sidecar_args = _scan_runtime.build_scan_report_sidecar_args


_build_runbook_sidecar_args = _scan_runtime.build_runbook_sidecar_args


def _render_primary_scan_output(
    *,
    out_path: Path,
    output_format: str,
    template: str | None,
    dry_run: bool,
    output_payload: _scan_context_RunScanOutputPayload,
) -> str:
    """Render and optionally write the primary scan output."""
    return _scan_runtime.render_primary_scan_output(
        out_path=out_path,
        output_format=output_format,
        template=template,
        dry_run=dry_run,
        output_payload=output_payload,
        render_primary_scan_output_fn=_scan_output_primary_render_primary_scan_output,
        render_and_write_scan_output=_render_and_write_scan_output,
    )


def _emit_scan_outputs(
    args: _scan_context_EmitScanOutputsArgs,
) -> str:
    """Render primary outputs and optional sidecars for a scanner run."""
    return _scan_runtime.emit_scan_outputs(
        args,
        emit_scan_outputs_fn=_scan_output_emit_scan_outputs,
        build_scanner_report_markdown=_build_scanner_report_markdown,
        render_and_write_scan_output=_render_and_write_scan_output,
        render_runbook=render_runbook,
        render_runbook_csv=render_runbook_csv,
    )


def _execute_scan_with_context(
    *,
    role_path: str,
    scan_options: dict,
    output: str,
    output_format: str,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    template: str | None,
    dry_run: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> str:
    """Execute scan using ScannerContext orchestration and emit final outputs."""
    container = DIContainer(role_path=role_path, scan_options=scan_options)
    context = ScannerContext(
        di=container,
        role_path=role_path,
        scan_options=scan_options,
        build_run_scan_options_fn=_build_run_scan_options,
        prepare_scan_context_fn=_prepare_scan_context,
    )
    payload = context.orchestrate_scan()

    emit_args = _build_emit_scan_outputs_args(
        output=output,
        output_format=output_format,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_scanner_report_link=include_scanner_report_link,
        payload=payload,
        template=template,
        dry_run=dry_run,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )
    return _emit_scan_outputs(emit_args)


def run_scan(
    role_path: str,
    output: str = "README.md",
    template: str | None = None,
    output_format: str = "md",
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    role_name_override: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    detailed_catalog: bool = False,
    dry_run: bool = False,
    include_collection_checks: bool = True,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    runbook_output: str | None = None,
    runbook_csv_output: str | None = None,
) -> str:
    """Scan an Ansible role and render documentation.

    Delegates scan orchestration to ScannerContext and then emits outputs.
    """
    if os.environ.get(_RETIRED_RUNTIME_STYLE_SOURCE_ENV):
        raise RuntimeError(
            _format_retired_runtime_error(
                _RETIRED_RUNTIME_PATH_CODE,
                _RETIRED_RUNTIME_PATH_MESSAGE,
            )
        )

    _refresh_policy(policy_config_path)
    detailed_catalog = _resolve_detailed_catalog_flag(
        detailed_catalog=detailed_catalog,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )
    scan_options = _build_run_scan_options(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        include_vars_main=include_vars_main,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=detailed_catalog,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        include_collection_checks=include_collection_checks,
        keep_unknown_style_sections=keep_unknown_style_sections,
        adopt_heading_mode=adopt_heading_mode,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
    )
    return _execute_scan_with_context(
        role_path=role_path,
        scan_options=scan_options,
        output=output,
        output_format=output_format,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_scanner_report_link=include_scanner_report_link,
        template=template,
        dry_run=dry_run,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )


def _resolve_detailed_catalog_flag(
    *,
    detailed_catalog: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> bool:
    """Ensure task catalog collection is enabled when standalone runbooks are requested."""
    return scan_request.resolve_scan_request_for_runtime(
        detailed_catalog=detailed_catalog,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )


def _build_run_scan_options(
    *,
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
    include_task_parameters: bool,
    include_task_runbooks: bool,
    inline_task_runbooks: bool,
    include_collection_checks: bool,
    keep_unknown_style_sections: bool,
    adopt_heading_mode: str | None,
    vars_seed_paths: list[str] | None,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
    fail_on_unconstrained_dynamic_includes: bool | None,
    fail_on_yaml_like_task_annotations: bool | None,
    ignore_unresolved_internal_underscore_references: bool | None,
) -> dict:
    """Build normalized scan options consumed by scan orchestration helpers."""
    return scan_request.build_run_scan_options(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        include_vars_main=include_vars_main,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=detailed_catalog,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        include_collection_checks=include_collection_checks,
        keep_unknown_style_sections=keep_unknown_style_sections,
        adopt_heading_mode=adopt_heading_mode,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        fail_on_unconstrained_dynamic_includes=(fail_on_unconstrained_dynamic_includes),
        fail_on_yaml_like_task_annotations=(fail_on_yaml_like_task_annotations),
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
    )


def _prepare_run_scan_payload(
    scan_options: dict,
) -> _scan_context_RunScanOutputPayload:
    """Prepare role metadata and display payloads used by scan output emission."""
    prepared_scan_context = _prepare_scan_context(scan_options)
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
