"""Scanner extraction package - consolidates variable, task, and data extraction logic."""

from __future__ import annotations

from prism.scanner_plugins.defaults import resolve_comment_driven_documentation_plugin
from prism.scanner_extract.task_line_parsing import (
    TASK_INCLUDE_KEYS,
    ROLE_INCLUDE_KEYS,
    INCLUDE_VARS_KEYS,
    SET_FACT_KEYS,
    TASK_BLOCK_KEYS,
    TASK_META_KEYS,
    ROLE_NOTES_RE,
    ROLE_NOTES_SHORT_RE,
    TASK_NOTES_LONG_RE,
    TASK_NOTES_SHORT_RE,
    COMMENT_CONTINUATION_RE,
)
from prism.scanner_extract.task_file_traversal import (
    _is_path_excluded,
    _load_yaml_file,
    _collect_task_files,
    _is_relpath_excluded,
    _collect_unconstrained_dynamic_role_includes,
    _collect_unconstrained_dynamic_task_includes,
)
from prism.scanner_extract.task_catalog_assembly import (
    _collect_task_handler_catalog,
    _collect_molecule_scenarios,
    extract_role_features,
)
from prism.scanner_extract.variable_extractor import (
    DEFAULT_TARGET_RE,
    JINJA_VAR_RE,
    JINJA_IDENTIFIER_RE,
    VAULT_KEY_RE,
    IGNORED_IDENTIFIERS,
    collect_include_vars_files,
    looks_secret_name,
    resembles_password_like,
    extract_default_target_var,
    load_seed_variables,
    refresh_policy_derived_state,
)
from prism.scanner_extract.discovery import (
    iter_role_variable_map_candidates,
    load_meta,
    load_requirements,
    load_variables,
    resolve_scan_identity,
)
from prism.scanner_extract.dataload import (
    iter_role_yaml_candidates,
    parse_yaml_candidate,
    collect_yaml_parse_failures,
    load_role_variable_maps,
    iter_role_argument_spec_entries,
    map_argument_spec_type,
)
from prism.scanner_extract.requirements import (
    format_requirement_line,
    normalize_requirements,
    normalize_meta_role_dependencies,
    normalize_included_role_dependencies,
    extract_declared_collections_from_meta,
    extract_declared_collections_from_requirements,
    build_collection_compliance_notes,
    build_requirements_display,
)


is_path_excluded = _is_path_excluded
load_yaml_file = _load_yaml_file
collect_task_files = _collect_task_files
is_relpath_excluded = _is_relpath_excluded


def _make_standalone_di(role_path: str, exclude_paths=None):
    from prism.scanner_core.scan_request import ensure_prepared_policy_bundle

    options: dict = {"role_path": role_path, "exclude_path_patterns": exclude_paths}
    ensure_prepared_policy_bundle(scan_options=options, di=None)

    class _StandaloneDI:
        def __init__(self, opts: dict) -> None:
            self._scan_options = opts

    return _StandaloneDI(options)


def collect_unconstrained_dynamic_role_includes(role_path, exclude_paths=None):
    di = _make_standalone_di(role_path, exclude_paths)
    return _collect_unconstrained_dynamic_role_includes(role_path, exclude_paths, di=di)


def collect_unconstrained_dynamic_task_includes(role_path, exclude_paths=None):
    di = _make_standalone_di(role_path, exclude_paths)
    return _collect_unconstrained_dynamic_task_includes(role_path, exclude_paths, di=di)


collect_task_handler_catalog = _collect_task_handler_catalog


def extract_role_notes_from_comments(
    role_path,
    exclude_paths=None,
    marker_prefix="prism",
    *,
    di=None,
):
    plugin = resolve_comment_driven_documentation_plugin(di)
    return plugin.extract_role_notes_from_comments(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=marker_prefix,
    )


def collect_molecule_scenarios(role_path, exclude_paths=None):
    di = _make_standalone_di(role_path, exclude_paths)
    return _collect_molecule_scenarios(role_path, exclude_paths, di=di)


__all__ = [
    "TASK_INCLUDE_KEYS",
    "ROLE_INCLUDE_KEYS",
    "INCLUDE_VARS_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
    "ROLE_NOTES_RE",
    "ROLE_NOTES_SHORT_RE",
    "TASK_NOTES_LONG_RE",
    "TASK_NOTES_SHORT_RE",
    "COMMENT_CONTINUATION_RE",
    "is_path_excluded",
    "load_yaml_file",
    "collect_task_files",
    "is_relpath_excluded",
    "extract_role_notes_from_comments",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "collect_task_handler_catalog",
    "collect_molecule_scenarios",
    "extract_role_features",
    "DEFAULT_TARGET_RE",
    "JINJA_VAR_RE",
    "JINJA_IDENTIFIER_RE",
    "VAULT_KEY_RE",
    "IGNORED_IDENTIFIERS",
    "looks_secret_name",
    "resembles_password_like",
    "extract_default_target_var",
    "load_seed_variables",
    "collect_include_vars_files",
    "refresh_policy_derived_state",
    "iter_role_variable_map_candidates",
    "load_meta",
    "load_requirements",
    "load_variables",
    "resolve_scan_identity",
    "iter_role_yaml_candidates",
    "parse_yaml_candidate",
    "collect_yaml_parse_failures",
    "load_role_variable_maps",
    "iter_role_argument_spec_entries",
    "map_argument_spec_type",
    "format_requirement_line",
    "normalize_requirements",
    "normalize_meta_role_dependencies",
    "normalize_included_role_dependencies",
    "extract_declared_collections_from_meta",
    "extract_declared_collections_from_requirements",
    "build_collection_compliance_notes",
    "build_requirements_display",
]


def __getattr__(name: str) -> object:
    """Enforce module public API at runtime."""
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only public API in dir() and introspection."""
    return sorted(__all__)
