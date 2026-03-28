"""Core scanner implementation.

This module provides utilities to scan an Ansible role for common
patterns (for example uses of the `default()` filter), load role
metadata and variables, and render a README using a Jinja2 template.
"""

from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
import re
from typing import TypedDict

from .scanner_submodules.doc_insights import build_doc_insights
from .scanner_submodules.output import (
    render_final_output,
    write_output,
)
from .pattern_config import load_pattern_config
from .scanner_submodules.readme_config import (
    DEFAULT_DOC_MARKER_PREFIX as READMECFG_DEFAULT_DOC_MARKER_PREFIX,
    load_fail_on_unconstrained_dynamic_includes as _load_fail_on_unconstrained_dynamic_includes,
    load_fail_on_yaml_like_task_annotations as _load_fail_on_yaml_like_task_annotations,
    load_ignore_unresolved_internal_underscore_references as _load_ignore_unresolved_internal_underscore_references,
    load_non_authoritative_test_evidence_max_file_bytes as _load_non_authoritative_test_evidence_max_file_bytes,
    load_non_authoritative_test_evidence_max_files_scanned as _load_non_authoritative_test_evidence_max_files_scanned,
    load_non_authoritative_test_evidence_max_total_bytes as _load_non_authoritative_test_evidence_max_total_bytes,
    load_readme_marker_prefix as _load_readme_marker_prefix,
    load_readme_section_config as _load_readme_section_config,
    load_readme_section_visibility as _load_readme_section_visibility,
)
from .scanner_submodules.scan_request import (
    build_run_scan_options as _scan_request_build_run_scan_options,
    resolve_detailed_catalog_flag as _scan_request_resolve_detailed_catalog_flag,
)
from .scanner_submodules.scan_context import (
    RunScanOutputPayload as _scan_context_RunScanOutputPayload,
    EmitScanOutputsArgs as _scan_context_EmitScanOutputsArgs,
    ScanReportSidecarArgs as _scan_context_ScanReportSidecarArgs,
    ScanBaseContext as _scan_context_ScanBaseContext,
    ScanMetadata as _scan_context_ScanMetadata,
    ReferenceContext as _scan_context_ReferenceContext,
    FeaturesContext as _scan_context_FeaturesContext,
    StyleGuideConfig as _scan_context_StyleGuideConfig,
    finalize_scan_context_payload as _scan_context_finalize_scan_context_payload,
    build_scan_output_payload as _scan_context_build_scan_output_payload,
    prepare_run_scan_payload as _scan_context_prepare_run_scan_payload,
    build_emit_scan_outputs_args as _scan_context_build_emit_scan_outputs_args,
    RunbookSidecarArgs as _scan_context_RunbookSidecarArgs,
)
from .scanner_submodules.scan_output_emission import (
    write_optional_runbook_outputs as _scan_output_write_optional_runbook_outputs,
    emit_scan_outputs as _scan_output_emit_scan_outputs,
)
from .scanner_submodules.scan_output_primary import (
    render_and_write_scan_output as _scan_output_primary_render_and_write_scan_output,
    render_primary_scan_output as _scan_output_primary_render_primary_scan_output,
)
from .scanner_submodules.scanner_errorhandling import (
    should_suppress_internal_unresolved_reference as _errorhandling_should_suppress_internal_unresolved_reference,
    build_referenced_variable_uncertainty_reason as _errorhandling_build_referenced_variable_uncertainty_reason,
    append_non_authoritative_test_evidence_uncertainty_reason as _errorhandling_append_non_authoritative_test_evidence_uncertainty_reason,
    collect_non_authoritative_test_variable_evidence as _errorhandling_collect_non_authoritative_test_variable_evidence,
    test_evidence_probability as _errorhandling_test_evidence_probability,
    attach_non_authoritative_test_evidence as _errorhandling_attach_non_authoritative_test_evidence,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES as _ERRORHANDLING_MAX_FILE_BYTES,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED as _ERRORHANDLING_MAX_FILES_SCANNED,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES as _ERRORHANDLING_MAX_TOTAL_BYTES,
    NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT as _ERRORHANDLING_SATURATION_MATCH_COUNT,
)
from .scanner_submodules.scanner_config import (
    resolve_default_style_guide_source as _config_resolve_default_style_guide_source,
    default_style_guide_user_paths as _config_default_style_guide_user_paths,
    load_section_display_titles as _config_load_section_display_titles,
    resolve_section_selector as _config_resolve_section_selector,
)
from .scanner_submodules.scanner_dataload import (
    iter_role_yaml_candidates as _dataload_iter_role_yaml_candidates,
    parse_yaml_candidate as _dataload_parse_yaml_candidate,
    collect_yaml_parse_failures as _dataload_collect_yaml_parse_failures,
    map_argument_spec_type as _dataload_map_argument_spec_type,
    load_role_variable_maps as _dataload_load_role_variable_maps,
    iter_role_argument_spec_entries as _dataload_iter_role_argument_spec_entries,
)
from .scanner_submodules.scanner_requirements import (
    format_requirement_line as _requirements_format_requirement_line,
    normalize_requirements as _requirements_normalize_requirements,
    normalize_meta_role_dependencies as _requirements_normalize_meta_role_dependencies,
    normalize_included_role_dependencies as _requirements_normalize_included_role_dependencies,
    extract_declared_collections_from_meta as _requirements_extract_declared_collections_from_meta,
    extract_declared_collections_from_requirements as _requirements_extract_declared_collections_from_requirements,
    build_collection_compliance_notes as _requirements_build_collection_compliance_notes,
)
from .scanner_submodules.scan_discovery import (
    iter_role_variable_map_candidates as _scan_discovery_iter_role_variable_map_candidates,
    load_meta as _scan_discovery_load_meta,
    load_requirements as _scan_discovery_load_requirements,
    load_variables as _scan_discovery_load_variables,
    resolve_scan_identity as _scan_discovery_resolve_scan_identity,
)
from .scanner_submodules.scanner_runbook_report import (
    build_scanner_report_markdown as _runbook_report_build_scanner_report_markdown,
    extract_scanner_counters as _runbook_report_extract_scanner_counters,
    classify_provenance_issue as _runbook_report_classify_provenance_issue,
    is_unresolved_noise_category as _runbook_report_is_unresolved_noise_category,
    render_runbook as _runbook_report_render_runbook,
    build_runbook_rows as _runbook_report_build_runbook_rows,
    render_runbook_csv as _runbook_report_render_runbook_csv,
    build_requirements_display as _runbook_report_build_requirements_display,
    write_concise_scanner_report_if_enabled as _runbook_report_write_concise_scanner_report_if_enabled,
    build_scan_report_sidecar_args as _runbook_report_build_scan_report_sidecar_args,
    build_runbook_sidecar_args as _runbook_report_build_runbook_sidecar_args,
)
from .scanner_submodules.style_guide import (
    detect_style_section_level,
    format_heading,
    normalize_style_heading,
    parse_style_readme,
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
from .scanner_submodules.task_parser import (
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
from .scanner_submodules.variable_extractor import (
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
from .scanner_submodules.style_vars import (
    _describe_variable as _describe_variable,
    _is_role_local_variable_row as _is_role_local_variable_row,
    _render_role_notes_section as _render_role_notes_section,
    _render_role_variables_for_style as _render_role_variables_for_style,
    _render_template_overrides_section as _render_template_overrides_section,
    _render_variable_summary_section as _render_variable_summary_section,
    _render_variable_uncertainty_notes as _render_variable_uncertainty_notes,
)
from .scanner_submodules.render_guide import (
    _render_guide_identity_sections as _render_guide_mod_identity_sections,
    _render_guide_section_body as _render_guide_mod_section_body,
)
from .scanner_submodules.render_readme import (
    _append_scanner_report_section_if_enabled as _render_readme_mod_append_scanner_report_section_if_enabled,
    _compose_section_body as _render_readme_mod_compose_section_body,
    _generated_merge_markers as _render_readme_mod_generated_merge_markers,
    _render_readme_with_style_guide as _render_readme_mod_render_readme_with_style_guide,
    _resolve_ordered_style_sections as _render_readme_mod_resolve_ordered_style_sections,
    _resolve_section_content_mode as _render_readme_mod_resolve_section_content_mode,
    _strip_prior_generated_merge_block as _render_readme_mod_strip_prior_generated_merge_block,
    render_readme as _render_readme_mod_render_readme,
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

SECTION_CONFIG_FILENAME = ".prism.yml"
LEGACY_SECTION_CONFIG_FILENAME = ".ansible_role_doc.yml"
SECTION_CONFIG_FILENAMES = (
    SECTION_CONFIG_FILENAME,
    LEGACY_SECTION_CONFIG_FILENAME,
)
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
LEGACY_ENV_STYLE_GUIDE_SOURCE_PATH = "ANSIBLE_ROLE_DOC_STYLE_SOURCE"
XDG_DATA_HOME_ENV = "XDG_DATA_HOME"
STYLE_GUIDE_DATA_DIRNAME = "prism"
LEGACY_STYLE_GUIDE_DATA_DIRNAME = "ansible_role_doc"
SYSTEM_STYLE_GUIDE_SOURCE_PATH = (
    Path("/var/lib") / STYLE_GUIDE_DATA_DIRNAME / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME
)
LEGACY_SYSTEM_STYLE_GUIDE_SOURCE_PATH = (
    Path("/var/lib")
    / LEGACY_STYLE_GUIDE_DATA_DIRNAME
    / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME
)
DEFAULT_SECTION_DISPLAY_TITLES_PATH = (
    Path(__file__).parent / "data" / "section_display_titles.yml"
)
DEFAULT_DOC_MARKER_PREFIX = READMECFG_DEFAULT_DOC_MARKER_PREFIX

MARKDOWN_VAR_BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
MARKDOWN_VAR_TABLE_RE = re.compile(r"^\|\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\|")
MARKDOWN_VAR_BULLET_RE = re.compile(
    r"^[-*+]\s+`?([A-Za-z_][A-Za-z0-9_]*)`?(?:\s|$|:|-)"
)
MARKDOWN_VAR_PROSE_CONTEXT_RE = re.compile(
    r"\b(variable|variables|set|define|configured|configure|default|defaults|override|overrides|use|documented)\b",
    flags=re.IGNORECASE,
)
MARKDOWN_VAR_NESTED_KEY_HINT_RE = re.compile(
    r"\b(attribute|attributes|key|keys|field|fields|dictionary|map|list item|sub-?key)\b",
    flags=re.IGNORECASE,
)

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
# Note: these constants are now defined in scanner_submodules/scanner_errorhandling.py
# and re-exported here for backward compatibility
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES = _ERRORHANDLING_MAX_FILE_BYTES
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED = _ERRORHANDLING_MAX_FILES_SCANNED
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES = _ERRORHANDLING_MAX_TOTAL_BYTES
NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT = (
    _ERRORHANDLING_SATURATION_MATCH_COUNT
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

    _POLICY = load_pattern_config(override_path=override_path)
    STYLE_SECTION_ALIASES = _POLICY["section_aliases"]
    _SENSITIVITY = _POLICY["sensitivity"]
    _SECRET_NAME_TOKENS = tuple(_SENSITIVITY["name_tokens"])
    _VAULT_MARKERS = tuple(_SENSITIVITY["vault_markers"])
    _CREDENTIAL_PREFIXES = tuple(_SENSITIVITY["credential_prefixes"])
    _URL_PREFIXES = tuple(_SENSITIVITY["url_prefixes"])
    _VARIABLE_GUIDANCE_KEYWORDS = tuple(
        _POLICY["variable_guidance"]["priority_keywords"]
    )
    IGNORED_IDENTIFIERS = _POLICY["ignored_identifiers"]

    from .scanner_submodules import variable_extractor as _ve

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
        legacy_style_guide_data_dirname=LEGACY_STYLE_GUIDE_DATA_DIRNAME,
        style_guide_source_filename=DEFAULT_STYLE_GUIDE_SOURCE_FILENAME,
    )


def resolve_default_style_guide_source(explicit_path: str | None = None) -> str:
    """Resolve default style guide source path using Linux-aware precedence.

    Precedence (first existing path wins):

     1. ``$PRISM_STYLE_SOURCE``
     2. ``$ANSIBLE_ROLE_DOC_STYLE_SOURCE`` (legacy compatibility)
     3. ``./STYLE_GUIDE_SOURCE.md``
     4. ``$XDG_DATA_HOME/prism/STYLE_GUIDE_SOURCE.md``
       (or ``~/.local/share/...`` fallback)
     5. ``$XDG_DATA_HOME/ansible_role_doc/STYLE_GUIDE_SOURCE.md`` (legacy)
     6. ``/var/lib/prism/STYLE_GUIDE_SOURCE.md``
     7. ``/var/lib/ansible_role_doc/STYLE_GUIDE_SOURCE.md`` (legacy)
     8. bundled package template path
    """
    return _config_resolve_default_style_guide_source(
        explicit_path=explicit_path,
        env_style_guide_source_path=ENV_STYLE_GUIDE_SOURCE_PATH,
        legacy_env_style_guide_source_path=LEGACY_ENV_STYLE_GUIDE_SOURCE_PATH,
        xdg_data_home_env=XDG_DATA_HOME_ENV,
        style_guide_data_dirname=STYLE_GUIDE_DATA_DIRNAME,
        legacy_style_guide_data_dirname=LEGACY_STYLE_GUIDE_DATA_DIRNAME,
        style_guide_source_filename=DEFAULT_STYLE_GUIDE_SOURCE_FILENAME,
        system_style_guide_source_path=SYSTEM_STYLE_GUIDE_SOURCE_PATH,
        legacy_system_style_guide_source_path=LEGACY_SYSTEM_STYLE_GUIDE_SOURCE_PATH,
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
    occurrences: list[dict] = []
    role_root = Path(role_path).resolve()
    scanned_files: set[Path] = set()

    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        scanned_files.add(task_file.resolve())
        occurrences.extend(_scan_file_for_default_filters(task_file, role_root))

    role_path = str(role_root)
    for root, dirs, files in os.walk(role_path):
        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRS
            and not _is_relpath_excluded(
                str((Path(root) / d).resolve().relative_to(role_root)),
                exclude_paths,
            )
        ]
        for fname in files:
            fpath = Path(root) / fname
            if _is_path_excluded(fpath, role_root, exclude_paths):
                continue
            if fpath.resolve() in scanned_files:
                continue
            occurrences.extend(_scan_file_for_default_filters(fpath, role_root))

    return sorted(occurrences, key=lambda item: (item["file"], item["line_no"]))


def scan_for_all_filters(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict]:
    """Scan files under ``role_path`` for all discovered Jinja filters.

    Returns a list of occurrence dictionaries with keys: ``file``,
    ``line_no``, ``line``, ``match``, ``args`` and ``filter_name``.
    """
    occurrences: list[dict] = []
    role_root = Path(role_path).resolve()
    scanned_files: set[Path] = set()

    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        scanned_files.add(task_file.resolve())
        occurrences.extend(_scan_file_for_all_filters(task_file, role_root))

    role_path = str(role_root)
    for root, dirs, files in os.walk(role_path):
        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRS
            and not _is_relpath_excluded(
                str((Path(root) / d).resolve().relative_to(role_root)),
                exclude_paths,
            )
        ]
        for fname in files:
            fpath = Path(root) / fname
            if _is_path_excluded(fpath, role_root, exclude_paths):
                continue
            if fpath.resolve() in scanned_files:
                continue
            occurrences.extend(_scan_file_for_all_filters(fpath, role_root))

    return sorted(occurrences, key=lambda item: (item["file"], item["line_no"]))


def _scan_file_for_default_filters(file_path: Path, role_root: Path) -> list[dict]:
    """Scan a single file for uses of the ``default()`` filter."""
    occurrences: list[dict] = []
    seen: set[tuple[int, str, str]] = set()
    try:
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        ast_rows = _scan_text_for_default_filters_with_ast(text, lines)
        ast_line_numbers = {row["line_no"] for row in ast_rows}

        for row in ast_rows:
            key = (row["line_no"], row["match"], row["args"])
            if key in seen:
                continue
            seen.add(key)
            row["file"] = str(file_path.relative_to(role_root))
            occurrences.append(row)

        for idx, line in enumerate(lines, start=1):
            if idx in ast_line_numbers and ("{{" in line or "{%" in line):
                continue
            for match in DEFAULT_RE.finditer(line):
                args = (match.group("args") or "").strip()
                excerpt = line[max(0, match.start() - 80) : match.end() + 80].strip()
                key = (idx, excerpt, args)
                if key in seen:
                    continue
                seen.add(key)
                occurrences.append(
                    {
                        "file": str(file_path.relative_to(role_root)),
                        "line_no": idx,
                        "line": line,
                        "match": excerpt,
                        "args": args,
                    }
                )
    except (UnicodeDecodeError, PermissionError, OSError):
        return []
    return occurrences


def _scan_file_for_all_filters(file_path: Path, role_root: Path) -> list[dict]:
    """Scan a single file for uses of any Jinja filter."""
    occurrences: list[dict] = []
    seen: set[tuple[int, str, str, str]] = set()
    try:
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        ast_rows = _scan_text_for_all_filters_with_ast(text, lines)
        ast_line_numbers = {row["line_no"] for row in ast_rows}

        for row in ast_rows:
            filter_name = str(row.get("filter_name") or "")
            key = (row["line_no"], row["match"], row["args"], filter_name)
            if key in seen:
                continue
            seen.add(key)
            row["file"] = str(file_path.relative_to(role_root))
            occurrences.append(row)

        # Fallback for malformed templates where AST parsing fails.
        for idx, line in enumerate(lines, start=1):
            if idx in ast_line_numbers and ("{{" in line or "{%" in line):
                continue
            for match in ANY_FILTER_RE.finditer(line):
                filter_name = str(match.group("name") or "").strip()
                if not filter_name:
                    continue
                excerpt = line[max(0, match.start() - 80) : match.end() + 80].strip()
                key = (idx, excerpt, "", filter_name)
                if key in seen:
                    continue
                seen.add(key)
                occurrences.append(
                    {
                        "file": str(file_path.relative_to(role_root)),
                        "line_no": idx,
                        "line": line,
                        "match": excerpt,
                        "args": "",
                        "filter_name": filter_name,
                    }
                )
    except (UnicodeDecodeError, PermissionError, OSError):
        return []
    return occurrences


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
    """Return True when a heading likely describes role input variables."""
    normalized = normalize_style_heading(title)
    if not normalized:
        return False
    canonical = STYLE_SECTION_ALIASES.get(normalized)
    if canonical in {"role_variables", "variable_summary", "variable_guidance"}:
        return True
    return "variable" in normalized or "input" in normalized


def _extract_readme_input_variables(text: str) -> set[str]:
    """Extract likely variable names from README variable/input sections."""
    if not text.strip():
        return set()

    names: set[str] = set()
    in_fence = False
    fence_char = ""
    fence_len = 0
    in_variable_section = False
    lines = text.splitlines()

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        next_line = lines[idx + 1].rstrip() if idx + 1 < len(lines) else ""

        (
            in_fence,
            fence_char,
            fence_len,
            fence_handled,
        ) = _consume_fence_marker(
            line=line,
            in_fence=in_fence,
            fence_char=fence_char,
            fence_len=fence_len,
        )
        if fence_handled:
            continue

        if in_fence:
            continue

        header_state = _resolve_variable_section_heading_state(line, next_line)
        if header_state is not None:
            in_variable_section = header_state
            continue

        if not in_variable_section:
            continue

        names.update(_extract_readme_variable_names_from_line(line))

    return names


def _consume_fence_marker(
    *,
    line: str,
    in_fence: bool,
    fence_char: str,
    fence_len: int,
) -> tuple[bool, str, int, bool]:
    """Update fenced-code parsing state and indicate whether line was a marker."""
    fence_match = re.match(r"^\s*([`~]{3,})", line)
    if not fence_match:
        return in_fence, fence_char, fence_len, False
    marker = fence_match.group(1)
    marker_char = marker[0]
    marker_len = len(marker)
    if not in_fence:
        return True, marker_char, marker_len, True
    if marker_char == fence_char and marker_len >= fence_len:
        return False, "", 0, True
    return in_fence, fence_char, fence_len, True


def _resolve_variable_section_heading_state(line: str, next_line: str) -> bool | None:
    """Return variable-section state update from heading syntax, else ``None``."""
    atx_match = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
    if atx_match:
        level = len(atx_match.group(1))
        heading_text = atx_match.group(2).strip()
        if level <= 2:
            return _is_readme_variable_section_heading(heading_text)
        heading_lower = heading_text.lower()
        if "variable" not in heading_lower and "parameter" not in heading_lower:
            return False
        return None
    if line.strip() and re.match(r"^[-=]{3,}\s*$", next_line):
        return _is_readme_variable_section_heading(line.strip())
    return None


def _extract_readme_variable_names_from_line(line: str) -> set[str]:
    """Extract variable names from one markdown line using supported patterns."""
    names: set[str] = set()
    stripped = line.strip()
    if not stripped:
        return names

    patterns: tuple[re.Pattern[str], ...]
    if stripped.startswith("|"):
        patterns = (MARKDOWN_VAR_TABLE_RE,)
    elif MARKDOWN_VAR_BULLET_RE.match(stripped):
        patterns = (MARKDOWN_VAR_BULLET_RE,)
    else:
        # Prose backticks are useful but noisy; require explicit variable guidance hints.
        if not MARKDOWN_VAR_PROSE_CONTEXT_RE.search(line):
            return names
        lowered_line = line.lower()
        if (
            MARKDOWN_VAR_NESTED_KEY_HINT_RE.search(line)
            and "variable" not in lowered_line
        ):
            return names
        patterns = (MARKDOWN_VAR_BACKTICK_RE,)

    for pattern in patterns:
        for match in pattern.findall(line):
            lowered = match.lower()
            if lowered in IGNORED_IDENTIFIERS:
                continue
            names.add(match)
    return names


def _collect_readme_input_variables(
    role_path: str, style_readme_path: str | None = None
) -> set[str]:
    """Extract variable names documented in README when present, with fallback to style_readme_path.

    Prefers role README (role_path/README.md), falls back to style_readme_path if role README
    is missing, empty, or unreadable.
    """
    readme_path = Path(role_path) / "README.md"

    # Try to read role README first
    if readme_path.is_file():
        try:
            text = readme_path.read_text(encoding="utf-8")
            if text.strip():
                return _extract_readme_input_variables(text)
        except (OSError, UnicodeDecodeError):
            pass

    # Fallback to style_readme_path if provided
    if style_readme_path:
        style_path = Path(style_readme_path)
        if style_path.is_file():
            try:
                text = style_path.read_text(encoding="utf-8")
                if text.strip():
                    return _extract_readme_input_variables(text)
            except (OSError, UnicodeDecodeError):
                pass

    return set()


def load_meta(role_path: str) -> dict:
    """Load the role metadata file ``meta/main.yml`` if present.

    Returns a mapping (empty if missing or unparsable).
    """
    return _scan_discovery_load_meta(role_path)


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


def _iter_role_variable_map_candidates(role_root: Path, subdir: str) -> list[Path]:
    """Return role variable map files in deterministic merge order.

    Order is:
    1) ``<subdir>/main.yml`` then ``<subdir>/main.yaml`` fallback
    2) sorted fragments under ``<subdir>/main/*.yml`` then ``*.yaml``
    """
    return _scan_discovery_iter_role_variable_map_candidates(role_root, subdir)


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


def load_requirements(role_path: str) -> list:
    """Load ``meta/requirements.yml`` as a list, or return an empty list."""
    return _scan_discovery_load_requirements(role_path)


def _format_requirement_line(item: object) -> str:
    """Format one requirement entry into a markdown-safe display line."""
    return _requirements_format_requirement_line(item)


def normalize_requirements(requirements: list) -> list[str]:
    """Normalize requirements entries to display strings."""
    return _requirements_normalize_requirements(requirements)


def _normalize_meta_role_dependencies(meta: dict) -> list[str]:
    """Normalize role dependencies from ``meta/main.yml`` for README output."""
    return _requirements_normalize_meta_role_dependencies(meta)


def _normalize_included_role_dependencies(
    features: _scan_context_FeaturesContext,
) -> list[str]:
    """Normalize static role includes detected from task parsing features."""
    return _requirements_normalize_included_role_dependencies(features)


def _extract_declared_collections_from_meta(meta: dict) -> set[str]:
    """Extract declared non-ansible collections from ``meta/main.yml`` content."""
    return _requirements_extract_declared_collections_from_meta(meta)


def _extract_declared_collections_from_requirements(requirements: list) -> set[str]:
    """Extract declared non-ansible collections from ``meta/requirements.yml``."""
    return _requirements_extract_declared_collections_from_requirements(requirements)


def _build_collection_compliance_notes(
    *,
    features: _scan_context_FeaturesContext,
    meta: dict,
    requirements: list,
) -> list[str]:
    """Build human-readable notes about collection declaration coverage."""
    return _requirements_build_collection_compliance_notes(
        features=features,
        meta=meta,
        requirements=requirements,
    )


def collect_role_contents(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Collect lists of files from common role subdirectories.

    Returns a dict with keys like ``handlers``, ``tasks``, ``templates``,
    ``files`` and ``tests`` containing lists of relative paths.
    """
    rp = Path(role_path)
    result: dict = {}
    for name in (
        "handlers",
        "tasks",
        "templates",
        "files",
        "tests",
        "defaults",
        "vars",
    ):
        subdir = rp / name
        entries: list[str] = []
        if subdir.exists() and subdir.is_dir():
            for p in sorted(subdir.rglob("*")):
                if p.is_file():
                    if _is_path_excluded(p, rp.resolve(), exclude_paths):
                        continue
                    entries.append(str(p.relative_to(rp)))
        result[name] = entries
    # include parsed meta file for richer template rendering
    try:
        result["meta"] = load_meta(role_path)
    except Exception:
        result["meta"] = {}
    result["features"] = extract_role_features(role_path, exclude_paths=exclude_paths)
    return result


def _compute_quality_metrics(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Compute lightweight role quality metrics for comparison output."""
    contents = collect_role_contents(role_path, exclude_paths=exclude_paths)
    features = contents.get("features", {}) if isinstance(contents, dict) else {}
    variables = load_variables(role_path, exclude_paths=exclude_paths)

    present_dirs = 0
    for section in (
        "tasks",
        "defaults",
        "vars",
        "handlers",
        "templates",
        "files",
        "tests",
    ):
        if contents.get(section):
            present_dirs += 1

    defaults_hits = len(
        scan_for_default_filters(role_path, exclude_paths=exclude_paths)
    )
    tasks_scanned = int(features.get("tasks_scanned", 0) or 0)
    unique_modules_raw = str(features.get("unique_modules", "none"))
    unique_modules = (
        0
        if unique_modules_raw == "none"
        else len([item for item in unique_modules_raw.split(",") if item.strip()])
    )

    score = (
        present_dirs * 10
        + min(len(variables), 20)
        + min(tasks_scanned, 20)
        + min(unique_modules * 3, 15)
        + min(defaults_hits, 10)
    )
    score = max(0, min(100, score))

    return {
        "score": score,
        "present_dirs": present_dirs,
        "variable_count": len(variables),
        "task_count": tasks_scanned,
        "module_count": unique_modules,
        "default_filter_count": defaults_hits,
    }


def build_comparison_report(
    target_role_path: str,
    baseline_role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Build a compact comparison between a target role and local baseline role."""
    target = _compute_quality_metrics(target_role_path, exclude_paths=exclude_paths)
    baseline = _compute_quality_metrics(
        baseline_role_path,
        exclude_paths=exclude_paths,
    )

    return {
        "baseline_path": str(Path(baseline_role_path).resolve()),
        "target_score": target["score"],
        "baseline_score": baseline["score"],
        "score_delta": target["score"] - baseline["score"],
        "metrics": {
            "present_dirs": {
                "target": target["present_dirs"],
                "baseline": baseline["present_dirs"],
                "delta": target["present_dirs"] - baseline["present_dirs"],
            },
            "variable_count": {
                "target": target["variable_count"],
                "baseline": baseline["variable_count"],
                "delta": target["variable_count"] - baseline["variable_count"],
            },
            "task_count": {
                "target": target["task_count"],
                "baseline": baseline["task_count"],
                "delta": target["task_count"] - baseline["task_count"],
            },
            "module_count": {
                "target": target["module_count"],
                "baseline": baseline["module_count"],
                "delta": target["module_count"] - baseline["module_count"],
            },
            "default_filter_count": {
                "target": target["default_filter_count"],
                "baseline": baseline["default_filter_count"],
                "delta": target["default_filter_count"]
                - baseline["default_filter_count"],
            },
        },
    }


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
    dynamic_task_include_refs = _collect_dynamic_task_include_refs(
        role_path,
        exclude_paths=exclude_paths,
    )
    tokens: set[str] = set()
    for ref in dynamic_task_include_refs:
        tokens.update(
            token
            for token in JINJA_IDENTIFIER_RE.findall(ref)
            if token.lower() not in IGNORED_IDENTIFIERS
        )
    return tokens


def _collect_dynamic_include_var_tokens(
    dynamic_include_vars_refs: list[str],
) -> set[str]:
    """Collect unresolved Jinja identifier tokens from dynamic include_vars refs."""
    tokens: set[str] = set()
    for ref in dynamic_include_vars_refs:
        tokens.update(
            token
            for token in JINJA_IDENTIFIER_RE.findall(ref)
            if token.lower() not in IGNORED_IDENTIFIERS
        )
    return tokens


def _build_static_variable_rows(
    *,
    role_root: Path,
    defaults_data: dict,
    vars_data: dict,
    defaults_sources: dict[str, Path],
    vars_sources: dict[str, Path],
) -> tuple[list[dict], dict[str, dict]]:
    """Build baseline rows from defaults/main.yml and vars/main.yml."""
    rows: list[dict] = []
    rows_by_name: dict[str, dict] = {}
    for name in sorted(set(defaults_data) | set(vars_data)):
        has_default = name in defaults_data
        has_var = name in vars_data
        value = vars_data[name] if has_var else defaults_data.get(name)
        default_source_file = defaults_sources.get(name)
        vars_source_file = vars_sources.get(name)
        source = "defaults/main.yml"
        provenance_source_file = "defaults/main.yml"
        provenance_line = (
            _find_variable_line_in_yaml(default_source_file, name)
            if default_source_file is not None
            else None
        )
        provenance_confidence = 0.95
        uncertainty_reason = None
        is_ambiguous = False
        if default_source_file is not None:
            provenance_source_file = str(default_source_file.relative_to(role_root))
        if has_var and has_default:
            source = "defaults/main.yml + vars/main.yml override"
            provenance_source_file = (
                str(vars_source_file.relative_to(role_root))
                if vars_source_file is not None
                else "vars/main.yml"
            )
            provenance_line = (
                _find_variable_line_in_yaml(vars_source_file, name)
                if vars_source_file is not None
                else None
            )
            provenance_confidence = 0.80
            uncertainty_reason = (
                "Defaults value is superseded by vars/main.yml precedence "
                "(informational)."
            )
            is_ambiguous = True
        elif has_var:
            source = "vars/main.yml"
            provenance_source_file = (
                str(vars_source_file.relative_to(role_root))
                if vars_source_file is not None
                else "vars/main.yml"
            )
            provenance_line = (
                _find_variable_line_in_yaml(vars_source_file, name)
                if vars_source_file is not None
                else None
            )
            provenance_confidence = 0.90
        row = {
            "name": name,
            "type": _infer_variable_type(value),
            "default": _format_inline_yaml(value),
            "source": source,
            "documented": True,
            "required": False,
            "secret": _is_sensitive_variable(name, value),
            "provenance_source_file": provenance_source_file,
            "provenance_line": provenance_line,
            "provenance_confidence": provenance_confidence,
            "uncertainty_reason": uncertainty_reason,
            "is_unresolved": False,
            "is_ambiguous": is_ambiguous,
        }
        rows.append(row)
        rows_by_name[name] = row
    return rows, rows_by_name


def _append_include_vars_rows(
    *,
    role_path: str,
    role_root: Path,
    rows: list[dict],
    rows_by_name: dict[str, dict],
    exclude_paths: list[str] | None,
) -> set[str]:
    """Merge include_vars-derived values into variable insight rows."""
    known_names: set[str] = {row["name"] for row in rows}
    include_var_sources = _collect_include_var_sources(
        role_path=role_path,
        role_root=role_root,
        exclude_paths=exclude_paths,
    )

    for name in sorted(include_var_sources):
        entries = include_var_sources[name]
        if name in rows_by_name:
            _mark_existing_row_as_include_vars_ambiguous(
                rows_by_name[name],
                entries,
            )
            continue
        known_names.add(name)
        rows.append(_build_include_vars_row(name, entries))

    return known_names


def _collect_include_var_sources(
    *,
    role_path: str,
    role_root: Path,
    exclude_paths: list[str] | None,
) -> dict[str, list[dict]]:
    """Collect include_vars value sources keyed by variable name."""
    include_var_sources: dict[str, list[dict]] = defaultdict(list)
    for extra_path in _collect_include_vars_files(
        role_path,
        exclude_paths=exclude_paths,
    ):
        extra_data = _load_yaml_file(extra_path)
        if not isinstance(extra_data, dict):
            continue
        rel_source = str(extra_path.relative_to(role_root))
        for name in sorted(extra_data):
            include_var_sources[name].append(
                {
                    "source": rel_source,
                    "value": extra_data[name],
                    "line": _find_variable_line_in_yaml(extra_path, name),
                }
            )
    return include_var_sources


def _mark_existing_row_as_include_vars_ambiguous(
    row: dict, entries: list[dict]
) -> None:
    """Downgrade confidence for rows that can be overridden by include_vars."""
    row["is_ambiguous"] = True
    row["uncertainty_reason"] = (
        "May be overridden by include_vars sources: "
        + ", ".join(entry["source"] for entry in entries)
    )
    row["provenance_confidence"] = min(
        float(row.get("provenance_confidence", 1.0)),
        0.70,
    )


def _build_include_vars_row(name: str, entries: list[dict]) -> dict:
    """Build a variable insight row for include_vars-discovered variables."""
    selected = entries[-1]
    ambiguous = len(entries) > 1
    return {
        "name": name,
        "type": _infer_variable_type(selected["value"]),
        "default": _format_inline_yaml(selected["value"]),
        "source": selected["source"],
        "documented": True,
        "required": False,
        "secret": _is_sensitive_variable(name, selected["value"]),
        "provenance_source_file": selected["source"],
        "provenance_line": selected["line"],
        "provenance_confidence": 0.60 if ambiguous else 0.85,
        "uncertainty_reason": (
            "Defined in multiple include_vars files: "
            + ", ".join(entry["source"] for entry in entries)
            if ambiguous
            else None
        ),
        "is_unresolved": False,
        "is_ambiguous": ambiguous,
    }


def _append_set_fact_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
    exclude_paths: list[str] | None,
) -> None:
    """Append computed variable placeholders discovered from set_fact usage."""
    for name in sorted(
        _collect_set_fact_names(role_path, exclude_paths=exclude_paths) - known_names
    ):
        rows.append(
            {
                "name": name,
                "type": "computed",
                "default": "-",
                "source": "tasks (set_fact)",
                "documented": True,
                "required": False,
                "secret": False,
                "provenance_source_file": "tasks (set_fact)",
                "provenance_line": None,
                "provenance_confidence": 0.65,
                "uncertainty_reason": "Computed by set_fact at runtime.",
                "is_unresolved": False,
                "is_ambiguous": True,
            }
        )


def _append_register_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
    exclude_paths: list[str] | None,
) -> None:
    """Append runtime placeholders for task-level register variables."""
    for name in sorted(
        _collect_register_names(role_path, exclude_paths=exclude_paths) - known_names
    ):
        rows.append(
            {
                "name": name,
                "type": "computed",
                "default": "-",
                "source": "tasks (register)",
                "documented": True,
                "required": False,
                "secret": False,
                "provenance_source_file": "tasks (register)",
                "provenance_line": None,
                "provenance_confidence": 0.75,
                "uncertainty_reason": None,
                "is_unresolved": False,
                "is_ambiguous": False,
            }
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
    readme_vars = _collect_readme_input_variables(
        role_path, style_readme_path=style_readme_path
    )

    # Enrich existing variables that are documented in README
    for row in rows:
        name = row["name"]
        if name in readme_vars:
            # Mark as documented if not already
            if not row.get("documented"):
                row["documented"] = True
            # README docs indicate user-facing input, not a hard required unknown.
            row["required"] = False
            row["is_unresolved"] = False
            # Add README reference marker (optional enhancement)
            if "README.md" not in row.get("source", ""):
                row["readme_documented"] = True

    # README-only mentions no longer create variable rows
    # This eliminates the "readme_only" provenance noise


def _append_argument_spec_rows(
    *,
    role_path: str,
    rows: list[dict],
    known_names: set[str],
) -> set[str]:
    """Append argument_specs-declared inputs not yet present in row set."""
    for source_file, name, spec in _iter_role_argument_spec_entries(role_path):
        if name in known_names:
            continue
        has_default = "default" in spec
        default_value = spec.get("default")
        required = bool(spec.get("required", False) and not has_default)
        line_hint = _find_variable_line_in_yaml(Path(role_path) / source_file, name)
        rows.append(
            {
                "name": name,
                "type": _map_argument_spec_type(spec.get("type")),
                "default": (
                    _format_inline_yaml(default_value) if has_default else "<required>"
                ),
                "source": f"{source_file} (argument_specs)",
                "documented": True,
                "required": required,
                "secret": _is_sensitive_variable(name, default_value),
                "provenance_source_file": source_file,
                "provenance_line": line_hint,
                "provenance_confidence": 0.88 if has_default else 0.78,
                "uncertainty_reason": (
                    "Declared in argument_specs without a static default value."
                    if required
                    else None
                ),
                "is_unresolved": required,
                "is_ambiguous": False,
            }
        )
        known_names.add(name)
    return known_names


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
    referenced_names = _collect_referenced_variable_names(
        role_path,
        exclude_paths=exclude_paths,
    )

    for name in sorted(referenced_names - known_names):
        if _should_suppress_internal_unresolved_reference(
            name=name,
            seed_values=seed_values,
            ignore_unresolved_internal_underscore_references=(
                ignore_unresolved_internal_underscore_references
            ),
        ):
            continue
        rows.append(
            _build_referenced_variable_row(
                name=name,
                seed_values=seed_values,
                seed_secrets=seed_secrets,
                seed_sources=seed_sources,
                dynamic_include_vars_refs=dynamic_include_vars_refs,
                dynamic_include_var_tokens=dynamic_include_var_tokens,
                dynamic_task_include_tokens=dynamic_task_include_tokens,
            )
        )


def _should_suppress_internal_unresolved_reference(
    *,
    name: str,
    seed_values: dict,
    ignore_unresolved_internal_underscore_references: bool,
) -> bool:
    """Return whether an unresolved internal temp-style name should be skipped."""
    return _errorhandling_should_suppress_internal_unresolved_reference(
        name=name,
        seed_values=seed_values,
        ignore_unresolved_internal_underscore_references=ignore_unresolved_internal_underscore_references,
    )


def _build_referenced_variable_row(
    *,
    name: str,
    seed_values: dict,
    seed_secrets: set[str],
    seed_sources: dict,
    dynamic_include_vars_refs: list[str],
    dynamic_include_var_tokens: set[str],
    dynamic_task_include_tokens: set[str],
) -> dict:
    """Build one inferred variable row for referenced-but-undefined names."""
    seeded = name in seed_values
    value = seed_values.get(name, "<required>")
    source_name = seed_sources.get(name, "external vars")
    return {
        "name": name,
        "type": _infer_variable_type(value) if seeded else "required",
        "default": _format_inline_yaml(value) if seeded else "<required>",
        "source": f"seed: {source_name}" if seeded else "inferred usage",
        "documented": False,
        "required": not seeded,
        "secret": (name in seed_secrets or _is_sensitive_variable(name, value)),
        "provenance_source_file": source_name if seeded else None,
        "provenance_line": None,
        "provenance_confidence": 0.75 if seeded else 0.40,
        "uncertainty_reason": _build_referenced_variable_uncertainty_reason(
            name=name,
            seeded=seeded,
            dynamic_include_vars_refs=dynamic_include_vars_refs,
            dynamic_include_var_tokens=dynamic_include_var_tokens,
            dynamic_task_include_tokens=dynamic_task_include_tokens,
        ),
        "is_unresolved": not seeded,
        "is_ambiguous": False,
    }


def _build_referenced_variable_uncertainty_reason(
    *,
    name: str,
    seeded: bool,
    dynamic_include_vars_refs: list[str],
    dynamic_include_var_tokens: set[str],
    dynamic_task_include_tokens: set[str],
) -> str:
    """Return uncertainty reason text for inferred referenced variables."""
    return _errorhandling_build_referenced_variable_uncertainty_reason(
        name=name,
        seeded=seeded,
        dynamic_include_vars_refs=dynamic_include_vars_refs,
        dynamic_include_var_tokens=dynamic_include_var_tokens,
        dynamic_task_include_tokens=dynamic_task_include_tokens,
    )


def _append_non_authoritative_test_evidence_uncertainty_reason(
    *,
    prior_reason: str,
    match_count: int,
    matched_file_count: int,
    saturation_threshold: int,
    scan_budget_hit: bool,
) -> str:
    """Append non-authoritative test-evidence telemetry to uncertainty notes."""
    return _errorhandling_append_non_authoritative_test_evidence_uncertainty_reason(
        prior_reason=prior_reason,
        match_count=match_count,
        matched_file_count=matched_file_count,
        saturation_threshold=saturation_threshold,
        scan_budget_hit=scan_budget_hit,
    )


def _collect_non_authoritative_test_variable_evidence(
    *,
    role_path: str,
    unresolved_names: set[str],
    exclude_paths: list[str] | None,
    max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> dict[str, dict]:
    """Collect non-authoritative unresolved-name evidence from tests/molecule files."""
    return _errorhandling_collect_non_authoritative_test_variable_evidence(
        role_path=role_path,
        unresolved_names=unresolved_names,
        exclude_paths=exclude_paths,
        max_file_bytes=max_file_bytes,
        max_files_scanned=max_files_scanned,
        max_total_bytes=max_total_bytes,
    )


def _test_evidence_probability(match_count: int) -> float:
    """Return a bounded confidence score for non-authoritative test evidence."""
    return _errorhandling_test_evidence_probability(match_count)


def _attach_non_authoritative_test_evidence(
    *,
    role_path: str,
    rows: list[dict],
    exclude_paths: list[str] | None,
    max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> None:
    """Enrich unresolved rows with non-authoritative evidence from tests files."""
    return _errorhandling_attach_non_authoritative_test_evidence(
        role_path=role_path,
        rows=rows,
        exclude_paths=exclude_paths,
        max_file_bytes=max_file_bytes,
        max_files_scanned=max_files_scanned,
        max_total_bytes=max_total_bytes,
    )


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
    defaults_data, vars_data, defaults_sources, vars_sources = _load_role_variable_maps(
        role_path,
        include_vars_main,
    )
    role_root = Path(role_path)
    reference_context = _collect_variable_reference_context(
        role_path=role_path,
        seed_paths=seed_paths,
        exclude_paths=exclude_paths,
    )

    rows, rows_by_name = _build_static_variable_rows(
        role_root=role_root,
        defaults_data=defaults_data,
        vars_data=vars_data,
        defaults_sources=defaults_sources,
        vars_sources=vars_sources,
    )
    _populate_variable_rows(
        role_path=role_path,
        rows=rows,
        rows_by_name=rows_by_name,
        exclude_paths=exclude_paths,
        reference_context=reference_context,
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

    _redact_secret_defaults(rows)

    return rows


def _collect_variable_reference_context(
    *,
    role_path: str,
    seed_paths: list[str] | None,
    exclude_paths: list[str] | None,
) -> _scan_context_ReferenceContext:
    """Collect seed and dynamic-reference context for inferred variable rows."""
    seed_values, seed_secrets, seed_sources = load_seed_variables(seed_paths)
    dynamic_include_vars_refs = _collect_dynamic_include_vars_refs(
        role_path,
        exclude_paths=exclude_paths,
    )
    dynamic_include_var_tokens = _collect_dynamic_include_var_tokens(
        dynamic_include_vars_refs
    )
    dynamic_task_include_tokens = _collect_dynamic_task_include_tokens(
        role_path,
        exclude_paths=exclude_paths,
    )
    return {
        "seed_values": seed_values,
        "seed_secrets": seed_secrets,
        "seed_sources": seed_sources,
        "dynamic_include_vars_refs": dynamic_include_vars_refs,
        "dynamic_include_var_tokens": dynamic_include_var_tokens,
        "dynamic_task_include_tokens": dynamic_task_include_tokens,
    }


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
    role_root = Path(role_path).resolve()
    known_names = _append_include_vars_rows(
        role_path=role_path,
        role_root=role_root,
        rows=rows,
        rows_by_name=rows_by_name,
        exclude_paths=exclude_paths,
    )
    _append_set_fact_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        exclude_paths=exclude_paths,
    )
    known_names = _refresh_known_names(rows)
    _append_register_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        exclude_paths=exclude_paths,
    )
    known_names = _refresh_known_names(rows)
    known_names = _append_argument_spec_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
    )
    known_names = _refresh_known_names(rows)
    _append_referenced_variable_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        seed_values=reference_context["seed_values"],
        seed_secrets=reference_context["seed_secrets"],
        seed_sources=reference_context["seed_sources"],
        dynamic_include_vars_refs=reference_context["dynamic_include_vars_refs"],
        dynamic_include_var_tokens=reference_context["dynamic_include_var_tokens"],
        dynamic_task_include_tokens=reference_context["dynamic_task_include_tokens"],
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        exclude_paths=exclude_paths,
    )
    known_names = _refresh_known_names(rows)
    _append_readme_documented_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        style_readme_path=style_readme_path,
    )
    _attach_non_authoritative_test_evidence(
        role_path=role_path,
        rows=rows,
        exclude_paths=exclude_paths,
        max_file_bytes=non_authoritative_test_evidence_max_file_bytes,
        max_files_scanned=non_authoritative_test_evidence_max_files_scanned,
        max_total_bytes=non_authoritative_test_evidence_max_total_bytes,
    )


def _refresh_known_names(rows: list[dict]) -> set[str]:
    """Return a set of known variable names from row payloads."""
    return {row["name"] for row in rows}


def _redact_secret_defaults(rows: list[dict]) -> None:
    """Mask secret defaults in-place before rendering/output."""
    for row in rows:
        if row.get("secret"):
            row["default"] = "<secret>"


def _resolve_section_selector(selector: str) -> str | None:
    """Resolve a section selector to a canonical section id."""
    return _config_resolve_section_selector(
        selector=selector,
        all_section_ids=ALL_SECTION_IDS,
        style_section_aliases=STYLE_SECTION_ALIASES,
        normalize_heading_fn=normalize_style_heading,
    )


def _load_section_display_titles() -> dict[str, str]:
    """Load optional section display-title overrides from bundled data YAML."""
    return _config_load_section_display_titles(DEFAULT_SECTION_DISPLAY_TITLES_PATH)


def load_readme_marker_prefix(
    role_path: str,
    config_path: str | None = None,
) -> str:
    """Load configured documentation marker prefix from role config."""
    return _load_readme_marker_prefix(
        role_path,
        config_path=config_path,
        default_prefix=DEFAULT_DOC_MARKER_PREFIX,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_fail_on_unconstrained_dynamic_includes(
    role_path: str,
    config_path: str | None = None,
    default: bool = False,
) -> bool:
    """Load scan policy toggle for unconstrained dynamic include failures."""
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
    """Load scan policy toggle for YAML-like task annotation strict failures."""
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
    """Load suppression toggle for unresolved internal underscore references."""
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
    """Load max bytes per file for tests/molecule evidence scanning."""
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
    """Load max file-count budget for tests/molecule evidence scanning."""
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
    """Load max aggregate byte budget for tests/molecule evidence scanning."""
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
    """Load optional README section visibility rules from YAML config.

    Configuration format (either explicit ``config_path`` or auto-discovered
    ``<role_path>/.prism.yml`` / legacy ``<role_path>/.ansible_role_doc.yml``):

    .. code-block:: yaml

        readme:
          include_sections:
            - galaxy_info
            - Role purpose and capabilities
          exclude_sections:
            - comparison

    Returns:
        ``None`` when no config exists or no include/exclude keys are present,
        otherwise the enabled section-id set.
    """
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
    """Load README section visibility and section rendering options."""
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


def _render_guide_identity_sections(
    section_id: str,
    role_name: str,
    description: str,
    requirements: list,
    galaxy: dict,
    metadata: dict,
) -> str | None:
    """Compatibility wrapper for extracted guide identity rendering."""
    return _render_guide_mod_identity_sections(
        section_id,
        role_name,
        description,
        requirements,
        galaxy,
        metadata,
    )


def _render_guide_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Compatibility wrapper for extracted guide section body rendering."""
    return _render_guide_mod_section_body(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
        variable_guidance_keywords=_VARIABLE_GUIDANCE_KEYWORDS,
    )


def _generated_merge_markers(section_id: str) -> list[tuple[str, str]]:
    """Compatibility wrapper for extracted README merge markers."""
    return _render_readme_mod_generated_merge_markers(section_id)


def _strip_prior_generated_merge_block(section: dict, guide_body: str) -> str:
    """Compatibility wrapper for extracted README merge-block stripping."""
    return _render_readme_mod_strip_prior_generated_merge_block(section, guide_body)


def _resolve_section_content_mode(section: dict, modes: dict[str, str]) -> str:
    """Compatibility wrapper for extracted README section content mode resolution."""
    return _render_readme_mod_resolve_section_content_mode(section, modes)


def _compose_section_body(section: dict, generated_body: str, mode: str) -> str:
    """Compatibility wrapper for extracted README section composition."""
    return _render_readme_mod_compose_section_body(section, generated_body, mode)


def _resolve_ordered_style_sections(
    style_guide: _scan_context_StyleGuideConfig,
    metadata: dict,
) -> tuple[list[dict], set[str], dict[str, str], bool]:
    """Compatibility wrapper for extracted README section ordering."""
    return _render_readme_mod_resolve_ordered_style_sections(style_guide, metadata)


def _append_scanner_report_section_if_enabled(
    parts: list[str],
    style_guide: _scan_context_StyleGuideConfig,
    style_guide_skeleton: bool,
    scanner_report_relpath: str | None,
    include_scanner_report_link: bool,
    enabled_sections: set[str],
) -> None:
    """Compatibility wrapper for extracted README scanner-report section rendering."""
    _render_readme_mod_append_scanner_report_section_if_enabled(
        parts,
        style_guide,
        style_guide_skeleton,
        scanner_report_relpath,
        include_scanner_report_link,
        enabled_sections,
    )


def _render_readme_with_style_guide(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Compatibility wrapper for extracted style-guide README rendering."""
    return _render_readme_mod_render_readme_with_style_guide(
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    )


def _build_scanner_report_markdown(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Render a scanner-focused markdown sidecar report."""
    return _runbook_report_build_scanner_report_markdown(
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata,
        render_section_body=_render_guide_section_body,
    )


def _extract_scanner_counters(
    variable_insights: list[dict],
    default_filters: list[dict],
    features: _scan_context_FeaturesContext | None = None,
    parse_failures: list[dict[str, object]] | None = None,
) -> dict[str, int | dict[str, int]]:
    """Summarize scanner findings by certainty and variable category."""
    return _runbook_report_extract_scanner_counters(
        variable_insights,
        default_filters,
        features,
        parse_failures,
    )


def _classify_provenance_issue(row: dict) -> str | None:
    """Return a stable provenance category label for unresolved/ambiguous rows."""
    return _runbook_report_classify_provenance_issue(row)


def _is_unresolved_noise_category(category: str | None) -> bool:
    """Return True if the category participates in unresolved-noise metrics."""
    return _runbook_report_is_unresolved_noise_category(category)


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


def render_runbook(
    role_name: str,
    metadata: dict | None = None,
    template: str | None = None,
) -> str:
    """Render a standalone runbook markdown document for a role."""
    return _runbook_report_render_runbook(
        role_name=role_name, metadata=metadata, template=template
    )


def _build_runbook_rows(metadata: dict | None) -> list[tuple[str, str, str]]:
    """Build normalized runbook rows: (file, task_name, step)."""
    return _runbook_report_build_runbook_rows(metadata)


def render_runbook_csv(metadata: dict | None = None) -> str:
    """Render runbook rows to CSV with columns: file, task_name, step."""
    return _runbook_report_render_runbook_csv(metadata)


def _build_requirements_display(
    *,
    requirements: list,
    meta: dict,
    features: _scan_context_FeaturesContext,
    include_collection_checks: bool = True,
) -> tuple[list[str], list[str]]:
    """Build rendered requirements lines and collection compliance notes."""
    return _runbook_report_build_requirements_display(
        requirements=requirements,
        meta=meta,
        features=features,
        include_collection_checks=include_collection_checks,
    )


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
    return _runbook_report_write_concise_scanner_report_if_enabled(
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
        build_scanner_report_markdown_fn=_build_scanner_report_markdown,
    )


def _resolve_scan_identity(
    role_path: str,
    role_name_override: str | None,
) -> tuple[Path, dict, str, str]:
    """Resolve role path, metadata, role name, and description."""
    return _scan_discovery_resolve_scan_identity(
        role_path,
        role_name_override,
        load_meta_fn=load_meta,
    )


def _collect_scan_artifacts(
    *,
    role_path: str,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
    marker_prefix: str,
) -> tuple[dict, list, list[dict], dict]:
    """Collect scan-time variables, requirements, default filters, and metadata."""
    variables = load_variables(
        role_path,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_path_patterns,
    )
    requirements = load_requirements(role_path)
    found = scan_for_default_filters(role_path, exclude_paths=exclude_path_patterns)
    metadata = collect_role_contents(role_path, exclude_paths=exclude_path_patterns)
    metadata["molecule_scenarios"] = _collect_molecule_scenarios(
        role_path,
        exclude_paths=exclude_path_patterns,
    )
    metadata["marker_prefix"] = marker_prefix
    metadata["detailed_catalog"] = bool(detailed_catalog)
    metadata["include_task_parameters"] = True
    metadata["include_task_runbooks"] = True
    metadata["inline_task_runbooks"] = True
    metadata["unconstrained_dynamic_task_includes"] = (
        _collect_unconstrained_dynamic_task_includes(
            role_path,
            exclude_paths=exclude_path_patterns,
        )
    )
    metadata["unconstrained_dynamic_role_includes"] = (
        _collect_unconstrained_dynamic_role_includes(
            role_path,
            exclude_paths=exclude_path_patterns,
        )
    )
    if detailed_catalog:
        task_catalog, handler_catalog = _collect_task_handler_catalog(
            role_path,
            exclude_paths=exclude_path_patterns,
            marker_prefix=marker_prefix,
        )
        metadata["task_catalog"] = task_catalog
        metadata["handler_catalog"] = handler_catalog
    return variables, requirements, found, metadata


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


def _collect_variable_insights_and_default_filter_findings(
    *,
    role_path: str,
    vars_seed_paths: list[str] | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    found_default_filters: list[dict],
    variables: dict,
    metadata: dict,
    marker_prefix: str,
    style_readme_path: str | None = None,
    ignore_unresolved_internal_underscore_references: bool = True,
    non_authoritative_test_evidence_max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    non_authoritative_test_evidence_max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    non_authoritative_test_evidence_max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> tuple[list[dict], list[dict], dict]:
    """Collect variable insights, scanner counters, and secret-masked defaults."""
    variable_insights = build_variable_insights(
        role_path,
        seed_paths=vars_seed_paths,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_path_patterns,
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
    _attach_external_vars_context(metadata, vars_seed_paths)
    metadata["variable_insights"] = variable_insights
    metadata["yaml_parse_failures"] = _collect_yaml_parse_failures(
        role_path,
        exclude_paths=exclude_path_patterns,
    )
    metadata["role_notes"] = _extract_role_notes_from_comments(
        role_path,
        exclude_paths=exclude_path_patterns,
        marker_prefix=marker_prefix,
    )
    undocumented_default_filters = _build_undocumented_default_filters(
        variable_insights=variable_insights,
        found_default_filters=found_default_filters,
    )

    metadata["scanner_counters"] = _extract_scanner_counters(
        variable_insights,
        undocumented_default_filters,
        metadata.get("features") or {},
        metadata.get("yaml_parse_failures") or [],
    )
    display_variables = _build_display_variables(variables, variable_insights)
    return variable_insights, undocumented_default_filters, display_variables


def _attach_external_vars_context(
    metadata: _scan_context_ScanMetadata, vars_seed_paths: list[str] | None
) -> None:
    """Attach non-authoritative external variable context metadata when provided."""
    if not vars_seed_paths:
        return
    metadata["external_vars_context"] = {
        "paths": [str(path) for path in vars_seed_paths],
        "authoritative": False,
        "purpose": "required_variable_detection_hints",
    }


def _build_undocumented_default_filters(
    *,
    variable_insights: list[dict],
    found_default_filters: list[dict],
) -> list[dict]:
    """Return undocumented default() occurrences enriched with variable metadata."""
    inventory_names = {row["name"]: row for row in variable_insights}
    undocumented_default_filters: list[dict] = []
    for occurrence in found_default_filters:
        target_var = _extract_default_target_var(occurrence)
        if not target_var:
            continue
        row = inventory_names.get(target_var)
        if row and not row.get("documented", False):
            enriched = dict(occurrence)
            enriched["target_var"] = target_var
            if row.get("secret") or (
                _looks_secret_name(target_var)
                and _resembles_password_like(enriched.get("args", ""))
            ):
                enriched["args"] = "<secret>"
                enriched["match"] = f"{target_var} | default(<secret>)"
            undocumented_default_filters.append(enriched)
    return undocumented_default_filters


def _build_display_variables(variables: dict, variable_insights: list[dict]) -> dict:
    """Return role variables with secret values masked for rendering/output."""
    secret_names = {
        row["name"]
        for row in variable_insights
        if row.get("secret") and row["name"] in variables
    }
    return {
        key: ("<secret>" if key in secret_names else value)
        for key, value in variables.items()
    }


def _apply_style_and_comparison_metadata(
    *,
    metadata: dict,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
    role_path: str,
    exclude_path_patterns: list[str] | None,
) -> None:
    """Attach style-guide and optional baseline comparison metadata."""
    effective_style_readme_path = style_readme_path
    if not effective_style_readme_path and style_source_path:
        effective_style_readme_path = style_source_path
    if style_guide_skeleton and not effective_style_readme_path:
        effective_style_readme_path = resolve_default_style_guide_source(
            explicit_path=style_source_path
        )

    if effective_style_readme_path:
        style_path = Path(effective_style_readme_path)
        if not style_path.is_file():
            raise FileNotFoundError(
                f"style README not found: {effective_style_readme_path}"
            )
        metadata["style_guide"] = parse_style_readme(str(style_path))
    if style_guide_skeleton:
        metadata["style_guide_skeleton"] = True
    if compare_role_path:
        cp = Path(compare_role_path)
        if not cp.is_dir():
            raise FileNotFoundError(
                f"comparison role path not found: {compare_role_path}"
            )
        metadata["comparison"] = build_comparison_report(
            role_path,
            compare_role_path,
            exclude_paths=exclude_path_patterns,
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


def _prepare_scan_context(scan_options: dict) -> tuple[str, str, str, list, list, dict]:
    """Collect role metadata and scanner context required for rendering outputs."""
    base_context = _collect_scan_base_context(scan_options)
    config_default_ignore_unresolved_internal_underscore_references = (
        load_ignore_unresolved_internal_underscore_references(
            scan_options["role_path"],
            config_path=scan_options["readme_config_path"],
            default=True,
        )
    )
    effective_ignore_unresolved_internal_underscore_references = (
        config_default_ignore_unresolved_internal_underscore_references
        if scan_options["ignore_unresolved_internal_underscore_references"] is None
        else bool(scan_options["ignore_unresolved_internal_underscore_references"])
    )
    base_context["metadata"][
        "ignore_unresolved_internal_underscore_references"
    ] = effective_ignore_unresolved_internal_underscore_references
    non_authoritative_test_evidence_max_file_bytes = (
        load_non_authoritative_test_evidence_max_file_bytes(
            scan_options["role_path"],
            config_path=scan_options["readme_config_path"],
            default=NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
        )
    )
    non_authoritative_test_evidence_max_files_scanned = (
        load_non_authoritative_test_evidence_max_files_scanned(
            scan_options["role_path"],
            config_path=scan_options["readme_config_path"],
            default=NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
        )
    )
    non_authoritative_test_evidence_max_total_bytes = (
        load_non_authoritative_test_evidence_max_total_bytes(
            scan_options["role_path"],
            config_path=scan_options["readme_config_path"],
            default=NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
        )
    )
    base_context["metadata"]["non_authoritative_test_evidence_limits"] = {
        "max_file_bytes": non_authoritative_test_evidence_max_file_bytes,
        "max_files_scanned": non_authoritative_test_evidence_max_files_scanned,
        "max_total_bytes": non_authoritative_test_evidence_max_total_bytes,
    }
    undocumented_default_filters, display_variables = (
        _enrich_scan_context_with_insights(
            role_path=scan_options["role_path"],
            role_name=base_context["role_name"],
            description=base_context["description"],
            vars_seed_paths=scan_options["vars_seed_paths"],
            include_vars_main=scan_options["include_vars_main"],
            exclude_path_patterns=scan_options["exclude_path_patterns"],
            marker_prefix=base_context["marker_prefix"],
            found=base_context["found"],
            variables=base_context["variables"],
            metadata=base_context["metadata"],
            style_readme_path=scan_options["style_readme_path"],
            style_source_path=scan_options["style_source_path"],
            style_guide_skeleton=scan_options["style_guide_skeleton"],
            compare_role_path=scan_options["compare_role_path"],
            ignore_unresolved_internal_underscore_references=(
                effective_ignore_unresolved_internal_underscore_references
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
    )
    return _finalize_scan_context_payload(
        rp=base_context["rp"],
        role_name=base_context["role_name"],
        description=base_context["description"],
        requirements_display=base_context["requirements_display"],
        undocumented_default_filters=undocumented_default_filters,
        display_variables=display_variables,
        metadata=base_context["metadata"],
    )


def _collect_scan_base_context(scan_options: dict) -> _scan_context_ScanBaseContext:
    """Collect baseline scan artifacts and configured metadata state."""
    (
        rp,
        meta,
        role_name,
        description,
        marker_prefix,
        variables,
        requirements,
        found,
        metadata,
    ) = _collect_scan_identity_and_artifacts(
        role_path=scan_options["role_path"],
        role_name_override=scan_options["role_name_override"],
        readme_config_path=scan_options["readme_config_path"],
        include_vars_main=scan_options["include_vars_main"],
        exclude_path_patterns=scan_options["exclude_path_patterns"],
        detailed_catalog=scan_options["detailed_catalog"],
    )
    requirements_display = _apply_scan_metadata_configuration(
        role_path=scan_options["role_path"],
        readme_config_path=scan_options["readme_config_path"],
        adopt_heading_mode=scan_options["adopt_heading_mode"],
        include_task_parameters=scan_options["include_task_parameters"],
        include_task_runbooks=scan_options["include_task_runbooks"],
        inline_task_runbooks=scan_options["inline_task_runbooks"],
        include_collection_checks=scan_options["include_collection_checks"],
        keep_unknown_style_sections=scan_options["keep_unknown_style_sections"],
        meta=meta,
        requirements=requirements,
        metadata=metadata,
    )
    _apply_unconstrained_dynamic_include_policy(
        role_path=scan_options["role_path"],
        readme_config_path=scan_options["readme_config_path"],
        fail_on_unconstrained_dynamic_includes=scan_options[
            "fail_on_unconstrained_dynamic_includes"
        ],
        metadata=metadata,
    )
    _apply_yaml_like_task_annotation_policy(
        role_path=scan_options["role_path"],
        readme_config_path=scan_options["readme_config_path"],
        fail_on_yaml_like_task_annotations=scan_options[
            "fail_on_yaml_like_task_annotations"
        ],
        metadata=metadata,
    )
    return {
        "rp": rp,
        "role_name": role_name,
        "description": description,
        "marker_prefix": marker_prefix,
        "variables": variables,
        "found": found,
        "metadata": metadata,
        "requirements_display": requirements_display,
    }


def _apply_unconstrained_dynamic_include_policy(
    *,
    role_path: str,
    readme_config_path: str | None,
    fail_on_unconstrained_dynamic_includes: bool | None,
    metadata: dict,
) -> None:
    """Apply and enforce unconstrained dynamic include scan policy."""
    config_default = load_fail_on_unconstrained_dynamic_includes(
        role_path,
        config_path=readme_config_path,
        default=False,
    )
    effective_fail = (
        config_default
        if fail_on_unconstrained_dynamic_includes is None
        else bool(fail_on_unconstrained_dynamic_includes)
    )
    metadata["fail_on_unconstrained_dynamic_includes"] = effective_fail

    hazards = [
        *(metadata.get("unconstrained_dynamic_task_includes") or []),
        *(metadata.get("unconstrained_dynamic_role_includes") or []),
    ]
    if effective_fail and hazards:
        first = hazards[0] if isinstance(hazards[0], dict) else {}
        first_file = str(first.get("file") or "<unknown>")
        first_task = str(first.get("task") or "(unnamed task)")
        first_module = str(first.get("module") or "include")
        first_target = str(first.get("target") or "")
        raise RuntimeError(
            "Unconstrained dynamic includes detected "
            f"({len(hazards)} findings). "
            f"First finding: {first_file} / {first_task} / {first_module} -> {first_target}. "
            "Constrain with a simple when allow-list, disable via "
            "scan.fail_on_unconstrained_dynamic_includes in .prism.yml, "
            "or override at call time."
        )


def _apply_yaml_like_task_annotation_policy(
    *,
    role_path: str,
    readme_config_path: str | None,
    fail_on_yaml_like_task_annotations: bool | None,
    metadata: dict,
) -> None:
    """Apply and enforce YAML-like task annotation strict-fail policy."""
    config_default = load_fail_on_yaml_like_task_annotations(
        role_path,
        config_path=readme_config_path,
        default=False,
    )
    effective_fail = (
        config_default
        if fail_on_yaml_like_task_annotations is None
        else bool(fail_on_yaml_like_task_annotations)
    )
    metadata["fail_on_yaml_like_task_annotations"] = effective_fail

    features = metadata.get("features") or {}
    yaml_like_count = int(features.get("yaml_like_task_annotations") or 0)
    if effective_fail and yaml_like_count > 0:
        raise RuntimeError(
            "YAML-like task annotations detected "
            f"({yaml_like_count} findings). "
            "Use plain text or key=value payloads in marker comments, disable via "
            "scan.fail_on_yaml_like_task_annotations in .prism.yml, "
            "or override at call time."
        )


def _finalize_scan_context_payload(
    *,
    rp: str,
    role_name: str,
    description: str,
    requirements_display: list,
    undocumented_default_filters: list[dict],
    display_variables: dict,
    metadata: dict,
) -> tuple[str, str, str, list, list, dict]:
    """Return normalized context payload used by run_scan output emission."""
    return _scan_context_finalize_scan_context_payload(
        rp=rp,
        role_name=role_name,
        description=description,
        requirements_display=requirements_display,
        undocumented_default_filters=undocumented_default_filters,
        display_variables=display_variables,
        metadata=metadata,
    )


def _collect_scan_identity_and_artifacts(
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
) -> tuple[Path, dict, str, str, str, dict, list, list, dict]:
    """Resolve scan identity and collect core role artifacts."""
    rp, meta, role_name, description = _resolve_scan_identity(
        role_path,
        role_name_override,
    )
    marker_prefix = load_readme_marker_prefix(
        role_path,
        config_path=readme_config_path,
    )
    variables, requirements, found, metadata = _collect_scan_artifacts(
        role_path=role_path,
        include_vars_main=include_vars_main,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=detailed_catalog,
        marker_prefix=marker_prefix,
    )
    return (
        rp,
        meta,
        role_name,
        description,
        marker_prefix,
        variables,
        requirements,
        found,
        metadata,
    )


def _apply_scan_metadata_configuration(
    role_path: str,
    readme_config_path: str | None,
    adopt_heading_mode: str | None,
    include_task_parameters: bool,
    include_task_runbooks: bool,
    inline_task_runbooks: bool,
    include_collection_checks: bool,
    keep_unknown_style_sections: bool,
    meta: dict,
    requirements: list,
    metadata: _scan_context_ScanMetadata,
) -> list:
    """Apply scan options that shape metadata and requirements rendering."""
    metadata["include_task_parameters"] = bool(include_task_parameters)
    metadata["include_task_runbooks"] = bool(include_task_runbooks)
    metadata["inline_task_runbooks"] = bool(inline_task_runbooks)
    requirements_display, collection_compliance_notes = _build_requirements_display(
        requirements=requirements,
        meta=meta,
        features=metadata.get("features") or {},
        include_collection_checks=include_collection_checks,
    )
    metadata["collection_compliance_notes"] = collection_compliance_notes
    metadata["keep_unknown_style_sections"] = keep_unknown_style_sections
    readme_section_config = load_readme_section_config(
        role_path,
        config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
    )
    _apply_readme_section_config(metadata, readme_section_config)
    return requirements_display


def _enrich_scan_context_with_insights(
    role_path: str,
    role_name: str,
    description: str,
    vars_seed_paths: list[str] | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    marker_prefix: str,
    found: list,
    variables: dict,
    metadata: _scan_context_ScanMetadata,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
    ignore_unresolved_internal_underscore_references: bool,
    non_authoritative_test_evidence_max_file_bytes: int,
    non_authoritative_test_evidence_max_files_scanned: int,
    non_authoritative_test_evidence_max_total_bytes: int,
) -> tuple[list[dict], dict]:
    """Add variable/doc/style insights to scan metadata and display payloads."""
    variable_insights, undocumented_default_filters, display_variables = (
        _collect_variable_insights_and_default_filter_findings(
            role_path=role_path,
            vars_seed_paths=vars_seed_paths,
            include_vars_main=include_vars_main,
            exclude_path_patterns=exclude_path_patterns,
            found_default_filters=found,
            variables=variables,
            metadata=metadata,
            marker_prefix=marker_prefix,
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
    )
    metadata["doc_insights"] = build_doc_insights(
        role_name=role_name,
        description=description,
        metadata=metadata,
        variables=variables,
        variable_insights=variable_insights,
    )
    _apply_style_and_comparison_metadata(
        metadata=metadata,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        role_path=role_path,
        exclude_path_patterns=exclude_path_patterns,
    )
    return undocumented_default_filters, display_variables


def _build_scan_output_payload(
    *,
    role_name: str,
    description: str,
    display_variables: dict,
    requirements_display: list,
    undocumented_default_filters: list,
    metadata: dict,
) -> _scan_context_RunScanOutputPayload:
    """Build the shared payload used for scanner report and primary output rendering."""
    return _scan_context_build_scan_output_payload(
        role_name=role_name,
        description=description,
        display_variables=display_variables,
        requirements_display=requirements_display,
        undocumented_default_filters=undocumented_default_filters,
        metadata=metadata,
    )


def _build_emit_scan_outputs_args(
    *,
    output: str,
    output_format: str,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    payload: _scan_context_RunScanOutputPayload,
    template: str | None,
    dry_run: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> _scan_context_EmitScanOutputsArgs:
    """Build the typed argument bundle for _emit_scan_outputs."""
    return _scan_context_build_emit_scan_outputs_args(
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


def _build_scan_report_sidecar_args(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    payload: _scan_context_RunScanOutputPayload,
    dry_run: bool,
) -> _scan_context_ScanReportSidecarArgs:
    """Build the typed argument bundle for _write_concise_scanner_report_if_enabled."""
    return _runbook_report_build_scan_report_sidecar_args(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        payload=payload,
        dry_run=dry_run,
    )


def _build_runbook_sidecar_args(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    payload: _scan_context_RunScanOutputPayload,
) -> _scan_context_RunbookSidecarArgs:
    """Build the typed argument bundle for _write_optional_runbook_outputs."""
    return _runbook_report_build_runbook_sidecar_args(
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        payload=payload,
    )


def _render_primary_scan_output(
    *,
    out_path: Path,
    output_format: str,
    template: str | None,
    dry_run: bool,
    output_payload: _scan_context_RunScanOutputPayload,
) -> str:
    """Render and optionally write the primary scan output."""
    return _scan_output_primary_render_primary_scan_output(
        out_path=out_path,
        output_format=output_format,
        template=template,
        dry_run=dry_run,
        output_payload=output_payload,
        render_and_write_scan_output=_render_and_write_scan_output,
    )


def _emit_scan_outputs(
    args: _scan_context_EmitScanOutputsArgs,
) -> str:
    """Render primary outputs and optional sidecars for a scanner run."""
    return _scan_output_emit_scan_outputs(
        args,
        build_scanner_report_markdown=_build_scanner_report_markdown,
        render_and_write_output=_render_and_write_scan_output,
        render_runbook_fn=render_runbook,
        render_runbook_csv_fn=render_runbook_csv,
    )


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
    prepared = _prepare_run_scan_payload(scan_options)
    emit_args = _build_emit_scan_outputs_args(
        output=output,
        output_format=output_format,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_scanner_report_link=include_scanner_report_link,
        payload=prepared,
        template=template,
        dry_run=dry_run,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )
    return _emit_scan_outputs(emit_args)


def _resolve_detailed_catalog_flag(
    *,
    detailed_catalog: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> bool:
    """Ensure task catalog collection is enabled when standalone runbooks are requested."""
    return _scan_request_resolve_detailed_catalog_flag(
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
    return _scan_request_build_run_scan_options(
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
    return _scan_context_prepare_run_scan_payload(
        prepared_scan_context=prepared_scan_context,
    )
