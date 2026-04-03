"""Core scanner implementation.

This module provides utilities to scan an Ansible role for common
patterns (for example uses of the `default()` filter), load role
metadata and variables, and render a README using a Jinja2 template.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
import re

from prism._jinja_analyzer import (
    _scan_text_for_all_filters_with_ast,
    _scan_text_for_default_filters_with_ast,
)
from prism.errors import FailurePolicy
from prism.scanner_analysis import (
    build_scanner_report_markdown as _runbook_report_build_scanner_report_markdown,
    extract_scanner_counters as _analysis_extract_scanner_counters,
    render_runbook as _runbook_report_render_runbook,
    render_runbook_csv as _runbook_report_render_runbook_csv,
)
from prism.scanner_analysis.metrics import (
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES as _ANALYSIS_MAX_FILE_BYTES,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED as _ANALYSIS_MAX_FILES_SCANNED,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES as _ANALYSIS_MAX_TOTAL_BYTES,
)
from prism.scanner_config import (
    DEFAULT_DOC_MARKER_PREFIX as READMECFG_DEFAULT_DOC_MARKER_PREFIX,
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
    load_fail_on_unconstrained_dynamic_includes as _load_fail_on_unconstrained_dynamic_includes,
    load_fail_on_yaml_like_task_annotations as _load_fail_on_yaml_like_task_annotations,
    load_ignore_unresolved_internal_underscore_references as _load_ignore_unresolved_internal_underscore_references,
    load_non_authoritative_test_evidence_max_file_bytes as _load_non_authoritative_test_evidence_max_file_bytes,
    load_non_authoritative_test_evidence_max_files_scanned as _load_non_authoritative_test_evidence_max_files_scanned,
    load_non_authoritative_test_evidence_max_total_bytes as _load_non_authoritative_test_evidence_max_total_bytes,
    load_pattern_policy_with_context,
    load_readme_marker_prefix as _load_readme_marker_prefix,
    load_readme_section_config as _load_readme_section_config,
    load_readme_section_visibility as _load_readme_section_visibility,
    resolve_default_style_guide_source as _config_resolve_default_style_guide_source,
)
from prism.scanner_core import DIContainer, ScanContextBuilder, ScannerContext
from prism.scanner_core import scan_facade_helpers as _scan_facade_helpers
from prism.scanner_core import scan_request
from prism.scanner_core import scan_runtime as _scan_runtime
from prism.scanner_core import variable_insights as _variable_insights
from prism.scanner_core import variable_pipeline as _variable_pipeline
from prism.scanner_data.contracts import (
    ScanMetadata as _scan_context_ScanMetadata,
)
from prism.scanner_data.contracts_output import (
    RunScanOutputPayload as _RunScanOutputPayload,
)
from prism.scanner_data.contracts_request import PolicyContext as _PolicyContext
from prism.scanner_data.contracts_request import ScanOptionsDict as _ScanOptionsDict
from prism.scanner_data.contracts_variables import (
    ReferenceContext as _scan_context_ReferenceContext,
)
from prism.scanner_data.contracts_variables import VariableRow as _VariableRow
from prism.scanner_extract import (
    build_requirements_display as _runbook_report_build_requirements_display,
    collect_include_vars_files as _collect_include_vars_files,
    collect_molecule_scenarios as _collect_molecule_scenarios,
    collect_task_files as _collect_task_files,
    collect_task_handler_catalog as _collect_task_handler_catalog,
    collect_unconstrained_dynamic_role_includes as _collect_unconstrained_dynamic_role_includes,
    collect_unconstrained_dynamic_task_includes as _collect_unconstrained_dynamic_task_includes,
    extract_default_target_var as _extract_default_target_var,
    extract_role_features,
    extract_role_notes_from_comments as _extract_role_notes_from_comments,
    filter_scanner as _filter_scanner,
    is_path_excluded as _is_path_excluded,
    is_relpath_excluded as _is_relpath_excluded,
    iter_role_argument_spec_entries as _dataload_iter_role_argument_spec_entries,
    iter_role_variable_map_candidates as _scan_discovery_iter_role_variable_map_candidates,
    load_meta as _scan_discovery_load_meta,
    load_requirements as _scan_discovery_load_requirements,
    load_role_variable_maps as _dataload_load_role_variable_maps,
    load_seed_variables,
    load_variables as _scan_discovery_load_variables,
    load_yaml_file as _load_yaml_file,
    looks_secret_name as _looks_secret_name,
    normalize_requirements as _requirements_normalize_requirements,
    resembles_password_like as _resembles_password_like,
    resolve_scan_identity as _scan_discovery_resolve_scan_identity,
)
from prism.scanner_extract import variable_extractor as _variable_extractor
from prism.scanner_io import (
    render_final_output,
    write_output,
)
from prism.scanner_io import (
    collect_yaml_parse_failures as _dataload_collect_yaml_parse_failures,
    iter_role_yaml_candidates as _dataload_iter_role_yaml_candidates,
    map_argument_spec_type as _dataload_map_argument_spec_type,
)
from prism.scanner_io.scan_output_emission import (
    emit_scan_outputs as _scan_output_emit_scan_outputs,
)
from prism.scanner_io.scan_output_primary import (
    render_and_write_scan_output as _scan_output_primary_render_and_write_scan_output,
)
from prism.scanner_readme import (
    append_scanner_report_section_if_enabled as _readme_append_scanner_report_section_if_enabled,
    build_doc_insights,
    normalize_style_heading,
    parse_style_readme,
    render_guide_section_body as _readme_render_guide_section_body,
)
from prism.scanner_readme import guide as _readme_guide
from prism.scanner_readme import render_readme as _readme_render_readme
from prism.scanner_readme import style as _readme_style

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


normalize_requirements = _requirements_normalize_requirements


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
        load_variables=lambda role_path, exclude_paths=None: load_variables(
            role_path,
            exclude_paths=exclude_paths,
        ),
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
        iter_variable_map_candidates_fn=_scan_discovery_iter_role_variable_map_candidates,
        load_yaml_file_fn=_load_yaml_file,
    )


def _build_static_variable_rows(
    *,
    role_root: Path,
    defaults_data: dict,
    vars_data: dict,
    defaults_sources: dict[str, Path],
    vars_sources: dict[str, Path],
) -> tuple[list[_VariableRow], dict[str, _VariableRow]]:
    """Build baseline rows from defaults/main.yml and vars/main.yml."""
    return _variable_pipeline.build_static_variable_rows(
        role_root=role_root,
        defaults_data=defaults_data,
        vars_data=vars_data,
        defaults_sources=defaults_sources,
        vars_sources=vars_sources,
    )


def _collect_variable_reference_context(
    *,
    role_path: str,
    seed_paths: list[str] | None,
    exclude_paths: list[str] | None,
    policy_context: _PolicyContext | None = None,
) -> _scan_context_ReferenceContext:
    """Collect seed and dynamic-reference context for inferred variable rows."""
    return _variable_pipeline.collect_variable_reference_context(
        role_path=role_path,
        seed_paths=seed_paths,
        exclude_paths=exclude_paths,
        load_seed_variables=load_seed_variables,
        policy_context=policy_context,
    )


def _populate_variable_rows(
    *,
    role_path: str,
    rows: list[_VariableRow],
    rows_by_name: dict[str, _VariableRow],
    exclude_paths: list[str] | None,
    reference_context: _scan_context_ReferenceContext,
    style_readme_path: str | None = None,
    policy_context: _PolicyContext | None = None,
    ignore_unresolved_internal_underscore_references: bool = True,
    non_authoritative_test_evidence_max_file_bytes: int = _ANALYSIS_MAX_FILE_BYTES,
    non_authoritative_test_evidence_max_files_scanned: int = _ANALYSIS_MAX_FILES_SCANNED,
    non_authoritative_test_evidence_max_total_bytes: int = _ANALYSIS_MAX_TOTAL_BYTES,
) -> None:
    """Populate dynamic, documented, and inferred variable rows in-place."""
    _variable_pipeline.populate_variable_rows(
        role_path=role_path,
        rows=rows,
        rows_by_name=rows_by_name,
        exclude_paths=exclude_paths,
        reference_context=reference_context,
        map_argument_spec_type=_dataload_map_argument_spec_type,
        style_readme_path=style_readme_path,
        policy_context=policy_context,
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


def _redact_secret_defaults(rows: list[_VariableRow]) -> None:
    """Mask secret defaults in-place before rendering/output."""
    _variable_pipeline.redact_secret_defaults(rows)


def build_variable_insights(
    role_path: str,
    seed_paths: list[str] | None = None,
    include_vars_main: bool = True,
    exclude_paths: list[str] | None = None,
    style_readme_path: str | None = None,
    policy_context: _PolicyContext | None = None,
    ignore_unresolved_internal_underscore_references: bool = True,
    non_authoritative_test_evidence_max_file_bytes: int = _ANALYSIS_MAX_FILE_BYTES,
    non_authoritative_test_evidence_max_files_scanned: int = _ANALYSIS_MAX_FILES_SCANNED,
    non_authoritative_test_evidence_max_total_bytes: int = _ANALYSIS_MAX_TOTAL_BYTES,
) -> list[dict]:
    """Build variable rows with inferred type/default/source details."""
    return _variable_insights.build_variable_insights(
        role_path,
        seed_paths=seed_paths,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_paths,
        style_readme_path=style_readme_path,
        policy_context=policy_context,
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


def get_style_section_aliases_snapshot() -> dict[str, str]:
    """Return an isolated copy of the currently active section alias mapping."""
    return _readme_style.get_style_section_aliases_snapshot()


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
    """Compatibility wrapper that intentionally preserves loader exceptions."""
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
    """Compatibility wrapper that intentionally preserves loader exceptions."""
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
    """Compatibility wrapper that intentionally preserves loader exceptions."""
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
    default: int = _ANALYSIS_MAX_FILE_BYTES,
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
    default: int = _ANALYSIS_MAX_FILES_SCANNED,
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
    default: int = _ANALYSIS_MAX_TOTAL_BYTES,
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
        section_aliases=get_style_section_aliases_snapshot(),
        normalize_heading=normalize_style_heading,
        display_titles_path=DEFAULT_SECTION_DISPLAY_TITLES_PATH,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def load_readme_section_config(
    role_path: str,
    config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    strict: bool = False,
    warning_collector: list[str] | None = None,
) -> dict | None:
    return _load_readme_section_config(
        role_path=role_path,
        config_path=config_path,
        adopt_heading_mode=adopt_heading_mode,
        all_section_ids=ALL_SECTION_IDS,
        section_aliases=get_style_section_aliases_snapshot(),
        normalize_heading=normalize_style_heading,
        display_titles_path=DEFAULT_SECTION_DISPLAY_TITLES_PATH,
        strict=strict,
        warning_collector=warning_collector,
        config_filenames=SECTION_CONFIG_FILENAMES,
        default_filename=SECTION_CONFIG_FILENAME,
    )


def _render_guide_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
    *,
    variable_guidance_keywords: tuple[str, ...] | None = None,
) -> str:
    """Render README guide sections using the currently active policy keywords."""
    return _readme_render_guide_section_body(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
        variable_guidance_keywords=variable_guidance_keywords,
    )


_append_scanner_report_section_if_enabled = (
    _readme_append_scanner_report_section_if_enabled
)


_build_scanner_report_markdown = partial(
    _runbook_report_build_scanner_report_markdown,
    render_section_body=_render_guide_section_body,
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


_build_undocumented_default_filters = partial(
    _variable_insights.build_undocumented_default_filters,
    extract_default_target_var=_extract_default_target_var,
    looks_secret_name=_looks_secret_name,
    resembles_password_like=_resembles_password_like,
)

_collect_variable_insights_and_default_filter_findings = partial(
    _variable_insights.collect_variable_insights_and_default_filter_findings,
    build_variable_insights=build_variable_insights,
    attach_external_vars_context=_variable_insights.attach_external_vars_context,
    collect_yaml_parse_failures=_collect_yaml_parse_failures,
    extract_role_notes_from_comments=_extract_role_notes_from_comments,
    build_undocumented_default_filters=_build_undocumented_default_filters,
    extract_scanner_counters=_analysis_extract_scanner_counters,
    build_display_variables=_variable_insights.build_display_variables,
)


_apply_style_and_comparison_metadata = partial(
    _scan_facade_helpers.apply_style_and_comparison_metadata,
    resolve_default_style_guide_source=resolve_default_style_guide_source,
    parse_style_readme=parse_style_readme,
    build_comparison_report=build_comparison_report,
)


_render_and_write_scan_output = partial(
    _scan_output_primary_render_and_write_scan_output,
    render_readme=_readme_render_readme,
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
    build_requirements_display=_runbook_report_build_requirements_display,
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
    non_authoritative_test_evidence_max_file_bytes=(_ANALYSIS_MAX_FILE_BYTES),
    non_authoritative_test_evidence_max_files_scanned=(_ANALYSIS_MAX_FILES_SCANNED),
    non_authoritative_test_evidence_max_total_bytes=(_ANALYSIS_MAX_TOTAL_BYTES),
)


_build_scan_output_payload = _scan_runtime.build_scan_output_payload


_build_emit_scan_outputs_args = _scan_runtime.build_emit_scan_outputs_args

_emit_scan_outputs = partial(
    _scan_runtime.emit_scan_outputs,
    emit_scan_outputs_fn=_scan_output_emit_scan_outputs,
    build_scanner_report_markdown=_build_scanner_report_markdown,
    render_and_write_scan_output=_render_and_write_scan_output,
    render_runbook=_runbook_report_render_runbook,
    render_runbook_csv=_runbook_report_render_runbook_csv,
)


def _execute_scan_with_context(
    *,
    role_path: str,
    scan_options: _ScanOptionsDict,
    output: str,
    output_format: str,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    template: str | None,
    dry_run: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> str | bytes:
    """Execute scan using ScannerContext orchestration and emit final outputs."""
    return _scan_facade_helpers.execute_scan_with_context(
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
        di_container_cls=DIContainer,
        scanner_context_cls=ScannerContext,
        build_run_scan_options_fn=scan_request.build_run_scan_options_canonical,
        prepare_scan_context_fn=_prepare_scan_context,
        build_emit_scan_outputs_args_fn=_build_emit_scan_outputs_args,
        emit_scan_outputs_fn=_emit_scan_outputs,
    )


def _orchestrate_scan_payload(
    *,
    role_path: str,
    scan_options: _ScanOptionsDict,
) -> _RunScanOutputPayload:
    """Execute scan orchestration and return the structured payload."""
    return _scan_facade_helpers.orchestrate_scan_payload(
        role_path=role_path,
        scan_options=scan_options,
        di_container_cls=DIContainer,
        scanner_context_cls=ScannerContext,
        build_run_scan_options_fn=scan_request.build_run_scan_options_canonical,
        prepare_scan_context_fn=_prepare_scan_context,
    )


_build_runtime_scan_state = partial(
    _scan_runtime.build_runtime_scan_state,
    load_pattern_policy_with_context=load_pattern_policy_with_context,
    build_run_scan_options_fn=scan_request.build_run_scan_options_canonical,
    resolve_scan_request_for_runtime_fn=scan_request.resolve_scan_request_for_runtime,
)


_scan_policy_scope = partial(
    _scan_runtime.scan_policy_scope,
    variable_policy_scope=_variable_extractor.policy_override_scope,
    style_section_aliases_scope=_readme_style.style_section_aliases_scope,
    variable_guidance_keywords_scope=_readme_guide.variable_guidance_keywords_scope,
)


def _run_scan_payload(
    role_path: str,
    *,
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
    include_collection_checks: bool = True,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    strict_phase_failures: bool = True,
    failure_policy: FailurePolicy | None = None,
    runbook_output: str | None = None,
    runbook_csv_output: str | None = None,
) -> _RunScanOutputPayload:
    """Scan a role and return the structured payload without rendering output."""
    loaded_policy, policy_context, scan_options = _build_runtime_scan_state(
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
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        strict_phase_failures=strict_phase_failures,
        failure_policy=failure_policy,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )
    with _scan_policy_scope(
        loaded_policy=loaded_policy,
        policy_context=policy_context,
    ):
        return _orchestrate_scan_payload(
            role_path=role_path,
            scan_options=scan_options,
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
    strict_phase_failures: bool = True,
    failure_policy: FailurePolicy | None = None,
    runbook_output: str | None = None,
    runbook_csv_output: str | None = None,
) -> str | bytes:
    """Scan an Ansible role and render documentation.

    Delegates scan orchestration to ScannerContext and then emits outputs.
    """
    loaded_policy, policy_context, scan_options = _build_runtime_scan_state(
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
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        strict_phase_failures=strict_phase_failures,
        failure_policy=failure_policy,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )
    with _scan_policy_scope(
        loaded_policy=loaded_policy,
        policy_context=policy_context,
    ):
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
