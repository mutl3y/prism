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
import yaml
import jinja2

from .scanner_submodules.doc_insights import build_doc_insights, parse_comma_values
from .scanner_submodules.output import (
    render_final_output,
    resolve_output_path,
    write_output,
)
from .pattern_config import load_pattern_config
from .scanner_submodules.readme_config import (
    DEFAULT_DOC_MARKER_PREFIX as READMECFG_DEFAULT_DOC_MARKER_PREFIX,
    load_fail_on_unconstrained_dynamic_includes as _load_fail_on_unconstrained_dynamic_includes,
    load_fail_on_yaml_like_task_annotations as _load_fail_on_yaml_like_task_annotations,
    load_readme_marker_prefix as _load_readme_marker_prefix,
    load_readme_section_config as _load_readme_section_config,
    load_readme_section_visibility as _load_readme_section_visibility,
)
from .scanner_submodules.requirements import (
    build_collection_compliance_notes as _requirements_build_collection_compliance_notes,
    build_requirements_display as _requirements_build_display,
    extract_declared_collections_from_meta as _requirements_extract_declared_meta,
    extract_declared_collections_from_requirements as _requirements_extract_declared_requirements,
    format_requirement_line as _requirements_format_line,
    normalize_included_role_dependencies as _requirements_normalize_included_roles,
    normalize_meta_role_dependencies as _requirements_normalize_meta_deps,
    normalize_requirements as _requirements_normalize,
)
from .scanner_submodules.scanner_report import (
    build_scanner_report_markdown as _report_build_markdown,
    classify_provenance_issue as _report_classify_provenance_issue,
    extract_scanner_counters as _report_extract_counters,
)
from .scanner_submodules.runbook import (
    _build_runbook_rows as _runbook_build_rows,
    render_runbook as _runbook_render,
    render_runbook_csv as _runbook_render_csv,
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
    xdg_data_home = os.environ.get(XDG_DATA_HOME_ENV)
    if xdg_data_home:
        data_home = Path(xdg_data_home).expanduser()
    else:
        data_home = (Path.home() / ".local" / "share").expanduser()
    return [
        data_home / STYLE_GUIDE_DATA_DIRNAME / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME,
        data_home
        / LEGACY_STYLE_GUIDE_DATA_DIRNAME
        / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME,
    ]


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
    if explicit_path:
        explicit_candidate = Path(explicit_path).expanduser()
        if explicit_candidate.is_file():
            return str(explicit_candidate.resolve())
        raise FileNotFoundError(f"style source path not found: {explicit_path}")

    candidates: list[Path] = []

    env_style_source = os.environ.get(ENV_STYLE_GUIDE_SOURCE_PATH)
    if env_style_source:
        candidates.append(Path(env_style_source).expanduser())

    legacy_env_style_source = os.environ.get(LEGACY_ENV_STYLE_GUIDE_SOURCE_PATH)
    if legacy_env_style_source:
        candidates.append(Path(legacy_env_style_source).expanduser())

    candidates.append(Path.cwd() / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME)
    candidates.extend(_default_style_guide_user_paths())
    candidates.append(SYSTEM_STYLE_GUIDE_SOURCE_PATH)
    candidates.append(LEGACY_SYSTEM_STYLE_GUIDE_SOURCE_PATH)
    candidates.append(DEFAULT_STYLE_GUIDE_SOURCE_PATH)

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    return str(DEFAULT_STYLE_GUIDE_SOURCE_PATH.resolve())


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
            row["file"] = os.path.relpath(file_path, role_root)
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
                        "file": os.path.relpath(file_path, role_root),
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
            row["file"] = os.path.relpath(file_path, role_root)
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
                        "file": os.path.relpath(file_path, role_root),
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
    role_root = Path(role_path).resolve()
    failures: list[dict[str, object]] = []

    for candidate in _iter_role_yaml_candidates(
        role_root,
        exclude_paths=exclude_paths,
    ):
        failure = _parse_yaml_candidate(candidate, role_root)
        if failure is not None:
            failures.append(failure)

    return failures


def _iter_role_yaml_candidates(
    role_root: Path,
    *,
    exclude_paths: list[str] | None,
):
    """Yield role-local YAML files while honoring ignored and excluded paths."""
    for root, dirs, files in os.walk(str(role_root)):
        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRS
            and not _is_relpath_excluded(
                str((Path(root) / d).resolve().relative_to(role_root)),
                exclude_paths,
            )
        ]
        for fname in sorted(files):
            candidate = Path(root) / fname
            if candidate.suffix.lower() not in {".yml", ".yaml"}:
                continue
            if _is_path_excluded(candidate, role_root, exclude_paths):
                continue
            yield candidate


def _parse_yaml_candidate(candidate: Path, role_root: Path) -> dict[str, object] | None:
    """Parse one YAML candidate and return a failure payload when parsing fails."""
    try:
        text = candidate.read_text(encoding="utf-8")
        yaml.safe_load(text)
        return None
    except (OSError, UnicodeDecodeError) as exc:
        return {
            "file": str(candidate.resolve().relative_to(role_root)),
            "line": None,
            "column": None,
            "error": f"read_error: {exc}",
        }
    except (yaml.YAMLError, ValueError) as exc:
        mark = getattr(exc, "problem_mark", None)
        line = int(mark.line) + 1 if mark is not None else None
        column = int(mark.column) + 1 if mark is not None else None
        problem = str(getattr(exc, "problem", "") or "").strip()
        if not problem:
            problem = str(exc).splitlines()[0].strip()
        return {
            "file": str(candidate.resolve().relative_to(role_root)),
            "line": line,
            "column": column,
            "error": problem,
        }


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
    meta_file = Path(role_path) / "meta" / "main.yml"
    if meta_file.exists():
        try:
            return yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
            return {}
    return {}


def _iter_role_argument_spec_entries(role_path: str):
    """Yield argument spec variable entries discovered in role metadata files.

    Supported layouts:
    - ``meta/argument_specs.yml`` with top-level ``argument_specs`` mapping
    - ``meta/main.yml`` with embedded ``argument_specs`` mapping
    """
    role_root = Path(role_path)
    arg_specs_file = role_root / "meta" / "argument_specs.yml"
    sources: list[tuple[str, dict]] = []

    if arg_specs_file.is_file():
        loaded = _load_yaml_file(arg_specs_file)
        if isinstance(loaded, dict):
            sources.append(("meta/argument_specs.yml", loaded))

    meta_main = load_meta(role_path)
    if isinstance(meta_main, dict):
        sources.append(("meta/main.yml", meta_main))

    for source_file, payload in sources:
        argument_specs = payload.get("argument_specs")
        if not isinstance(argument_specs, dict):
            continue
        for task_spec in argument_specs.values():
            if not isinstance(task_spec, dict):
                continue
            options = task_spec.get("options")
            if not isinstance(options, dict):
                continue
            for var_name, spec in options.items():
                if not isinstance(var_name, str) or not isinstance(spec, dict):
                    continue
                if "{{" in var_name or "{%" in var_name:
                    continue
                yield source_file, var_name, spec


def _map_argument_spec_type(spec_type: object) -> str:
    """Map argument-spec type labels into scanner variable type labels."""
    if not isinstance(spec_type, str):
        return "documented"
    normalized = spec_type.strip().lower()
    if normalized in {"str", "raw", "path", "bytes", "bits"}:
        return "string"
    if normalized in {"int"}:
        return "int"
    if normalized in {"bool"}:
        return "bool"
    if normalized in {"dict"}:
        return "dict"
    if normalized in {"list"}:
        return "list"
    if normalized in {"float"}:
        return "string"
    return "documented"


def _iter_role_variable_map_candidates(role_root: Path, subdir: str) -> list[Path]:
    """Return role variable map files in deterministic merge order.

    Order is:
    1) ``<subdir>/main.yml`` then ``<subdir>/main.yaml`` fallback
    2) sorted fragments under ``<subdir>/main/*.yml`` then ``*.yaml``
    """
    candidates: list[Path] = []

    main_yml = role_root / subdir / "main.yml"
    main_yaml = role_root / subdir / "main.yaml"
    if main_yml.exists():
        candidates.append(main_yml)
    elif main_yaml.exists():
        candidates.append(main_yaml)

    fragment_dir = role_root / subdir / "main"
    if fragment_dir.is_dir():
        candidates.extend(sorted(fragment_dir.glob("*.yml")))
        candidates.extend(sorted(fragment_dir.glob("*.yaml")))

    return candidates


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
    vars_out: dict = {}
    role_root = Path(role_path)
    subdirs = ["defaults"]
    if include_vars_main:
        subdirs.append("vars")

    for sub in subdirs:
        for p in _iter_role_variable_map_candidates(role_root, sub):
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    vars_out.update(data)
            except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
                continue
    for extra_path in _collect_include_vars_files(
        role_path, exclude_paths=exclude_paths
    ):
        try:
            data = yaml.safe_load(extra_path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                vars_out.update(data)
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
            continue
    return vars_out


def load_requirements(role_path: str) -> list:
    """Load ``meta/requirements.yml`` as a list, or return an empty list."""
    p = Path(role_path) / "meta" / "requirements.yml"
    if p.exists():
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or []
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
            return []
    return []


def _format_requirement_line(item: object) -> str:
    """Format one requirement entry into a markdown-safe display line."""
    return _requirements_format_line(item)


def normalize_requirements(requirements: list) -> list[str]:
    """Normalize requirements entries to display strings."""
    return _requirements_normalize(requirements)


def _normalize_meta_role_dependencies(meta: dict) -> list[str]:
    """Normalize role dependencies from ``meta/main.yml`` for README output."""
    return _requirements_normalize_meta_deps(meta)


def _normalize_included_role_dependencies(features: dict) -> list[str]:
    """Normalize static role includes detected from task parsing features."""
    return _requirements_normalize_included_roles(features)


def _extract_declared_collections_from_meta(meta: dict) -> set[str]:
    """Extract declared non-ansible collections from ``meta/main.yml`` content."""
    return _requirements_extract_declared_meta(meta)


def _extract_declared_collections_from_requirements(requirements: list) -> set[str]:
    """Extract declared non-ansible collections from ``meta/requirements.yml``."""
    return _requirements_extract_declared_requirements(requirements)


def _build_collection_compliance_notes(
    *,
    features: dict,
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
    defaults_data: dict = {}
    vars_data: dict = {}
    defaults_sources: dict[str, Path] = {}
    vars_sources: dict[str, Path] = {}
    role_root = Path(role_path)
    for candidate in _iter_role_variable_map_candidates(role_root, "defaults"):
        loaded = _load_yaml_file(candidate)
        if isinstance(loaded, dict):
            for name in loaded:
                defaults_sources[name] = candidate
            defaults_data.update(loaded)
    if include_vars_main:
        for candidate in _iter_role_variable_map_candidates(role_root, "vars"):
            loaded = _load_yaml_file(candidate)
            if isinstance(loaded, dict):
                for name in loaded:
                    vars_sources[name] = candidate
                vars_data.update(loaded)
    return defaults_data, vars_data, defaults_sources, vars_sources


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
            uncertainty_reason = "Overridden by vars/main.yml precedence."
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
    exclude_paths: list[str] | None,
) -> None:
    """Append rows for referenced-but-undefined variable names."""
    referenced_names = _collect_referenced_variable_names(
        role_path,
        exclude_paths=exclude_paths,
    )

    for name in sorted(referenced_names - known_names):
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
    if seeded:
        return "Provided by external seed vars."
    message = "Referenced in role but no static definition found."
    if dynamic_include_vars_refs and name in dynamic_include_var_tokens:
        message = (
            "Referenced in role but no static definition found. "
            "Dynamic include_vars paths detected."
        )
    if name in dynamic_task_include_tokens:
        message += " Dynamic include_tasks/import_tasks paths detected."
    if name.isupper():
        message += (
            " Uppercase name suggests an environment variable or external constant."
        )
    return message


def build_variable_insights(
    role_path: str,
    seed_paths: list[str] | None = None,
    include_vars_main: bool = True,
    exclude_paths: list[str] | None = None,
    style_readme_path: str | None = None,
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
    )

    _redact_secret_defaults(rows)

    return rows


def _collect_variable_reference_context(
    *,
    role_path: str,
    seed_paths: list[str] | None,
    exclude_paths: list[str] | None,
) -> dict:
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
    reference_context: dict,
    style_readme_path: str | None = None,
) -> None:  # <- ADD THIS LINE (was missing)
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
        exclude_paths=exclude_paths,
    )
    known_names = _refresh_known_names(rows)
    _append_readme_documented_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        style_readme_path=style_readme_path,
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
    value = selector.strip()
    if not value:
        return None
    if value in ALL_SECTION_IDS:
        return value
    normalized = normalize_style_heading(value)
    if normalized in ALL_SECTION_IDS:
        return normalized
    return STYLE_SECTION_ALIASES.get(normalized)


def _load_section_display_titles() -> dict[str, str]:
    """Load optional section display-title overrides from bundled data YAML."""
    path = DEFAULT_SECTION_DISPLAY_TITLES_PATH
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    payload = raw.get("display_titles")
    if not isinstance(payload, dict):
        return {}

    parsed: dict[str, str] = {}
    for section_id, display_title in payload.items():
        if not isinstance(section_id, str) or not isinstance(display_title, str):
            continue
        sid = section_id.strip()
        label = display_title.strip()
        if sid and label:
            parsed[sid] = label
    return parsed


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
    """Render style-guide sections focused on role identity and metadata."""
    if section_id == "galaxy_info":
        return _render_identity_galaxy_info_section(role_name, description, galaxy)
    if section_id == "requirements":
        return _render_identity_requirements_section(requirements)
    if section_id == "installation":
        return _render_identity_installation_section(role_name, galaxy)
    if section_id == "license":
        return _render_identity_license_section(galaxy)
    if section_id == "author_information":
        return _render_identity_author_section(galaxy)
    if section_id == "license_author":
        return _render_identity_license_author_section(galaxy)
    if section_id == "sponsors":
        return "No sponsorship metadata detected for this role."
    if section_id == "purpose":
        return _render_identity_purpose_section(metadata)
    if section_id == "role_notes":
        return _render_role_notes_section(metadata.get("role_notes"))
    return None


def _render_identity_galaxy_info_section(
    role_name: str,
    description: str,
    galaxy: dict,
) -> str:
    """Render Galaxy metadata section details."""
    if not galaxy:
        return "No Galaxy metadata found."
    lines = [
        f"- **Role name**: {galaxy.get('role_name', role_name)}",
        f"- **Description**: {galaxy.get('description', description)}",
        f"- **License**: {galaxy.get('license', 'N/A')}",
        f"- **Min Ansible Version**: {galaxy.get('min_ansible_version', 'N/A')}",
    ]
    tags = galaxy.get("galaxy_tags")
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags)}")
    return "\n".join(lines)


def _render_identity_requirements_section(requirements: list) -> str:
    """Render normalized requirements bullet list."""
    requirement_lines = normalize_requirements(requirements)
    if not requirement_lines:
        return "No additional requirements."
    return "\n".join(f"- {line}" for line in requirement_lines)


def _render_identity_installation_section(role_name: str, galaxy: dict) -> str:
    """Render installation guidance using Ansible Galaxy and requirements.yml."""
    install_name = str(galaxy.get("role_name") or role_name)
    return (
        "Install the role with Ansible Galaxy:\n\n"
        "```bash\n"
        f"ansible-galaxy install {install_name}\n"
        "```\n\n"
        "Or pin it in `requirements.yml`:\n\n"
        "```yaml\n"
        f"- src: {install_name}\n"
        "```"
    )


def _render_identity_license_section(galaxy: dict) -> str:
    """Render license value from Galaxy metadata when present."""
    if galaxy and galaxy.get("license"):
        return str(galaxy.get("license"))
    return "N/A"


def _render_identity_author_section(galaxy: dict) -> str:
    """Render author value from Galaxy metadata when present."""
    if galaxy and galaxy.get("author"):
        return str(galaxy.get("author"))
    return "N/A"


def _render_identity_license_author_section(galaxy: dict) -> str:
    """Render combined license/author identity section."""
    license_value = str(galaxy.get("license", "N/A")) if galaxy else "N/A"
    author_value = str(galaxy.get("author", "N/A")) if galaxy else "N/A"
    return f"License: {license_value}\n\nAuthor: {author_value}"


def _render_identity_purpose_section(metadata: dict) -> str:
    """Render inferred purpose and capabilities from doc insights."""
    insights = metadata.get("doc_insights") or {}
    lines = [insights.get("purpose_summary", "No inferred role summary available.")]
    capabilities = insights.get("capabilities", [])
    if capabilities:
        lines.extend(["", "Capabilities:"])
        lines.extend(f"- {capability}" for capability in capabilities)
    return "\n".join(lines)


def _render_guide_variable_sections(
    section_id: str,
    variables: dict,
    metadata: dict,
) -> str | None:
    """Render style-guide sections focused on variable inventory and guidance."""
    if section_id == "variable_summary":
        return _render_variable_summary_section(metadata)
    if section_id == "variable_guidance":
        return _render_variable_guidance_section(metadata)
    if section_id == "template_overrides":
        return _render_template_overrides_section(metadata)
    if section_id == "role_variables":
        return _render_role_variables_for_style(variables, metadata)
    return None


def _render_variable_guidance_section(metadata: dict) -> str:
    """Render recommended variable override candidates."""
    rows = metadata.get("variable_insights") or []
    if not rows:
        return "No variable guidance available because no variable defaults were discovered."

    priority = [
        row
        for row in rows
        if any(keyword in row["name"] for keyword in _VARIABLE_GUIDANCE_KEYWORDS)
    ]
    if not priority:
        priority = rows[:5]
    lines = ["Recommended variables to tune:"]
    for row in priority[:8]:
        lines.append(
            f"- `{row['name']}` (default: `{str(row['default']).replace('`', "'")}`)"
        )
    lines.append("")
    lines.append("Use these as initial overrides for environment-specific behavior.")
    return "\n".join(lines)


def _render_guide_task_sections(
    section_id: str,
    default_filters: list,
    metadata: dict,
) -> str | None:
    """Render style-guide sections focused on task, handler, and test activity."""
    if section_id == "task_summary":
        return _render_task_summary_section(metadata)
    if section_id == "example_usage":
        return _render_example_usage_section(metadata)
    if section_id == "local_testing":
        return _render_local_testing_section(metadata)
    if section_id == "handlers":
        return _render_handlers_section(metadata)
    if section_id == "faq_pitfalls":
        return _render_faq_pitfalls_section(default_filters, metadata)
    return None


def _render_task_summary_section(metadata: dict) -> str:
    """Render task-summary section details including optional parse failures/catalog."""
    summary = (metadata.get("doc_insights") or {}).get("task_summary", {})
    if not summary:
        return "No task summary available."

    yaml_parse_failures = metadata.get("yaml_parse_failures") or []
    unconstrained_dynamic_task_includes = (
        metadata.get("unconstrained_dynamic_task_includes") or []
    )
    unconstrained_dynamic_role_includes = (
        metadata.get("unconstrained_dynamic_role_includes") or []
    )
    unconstrained_dynamic_includes = [
        *unconstrained_dynamic_task_includes,
        *unconstrained_dynamic_role_includes,
    ]
    lines = [
        f"- **Task files scanned**: {summary.get('task_files_scanned', 0)}",
        f"- **Tasks scanned**: {summary.get('tasks_scanned', 0)}",
        f"- **Recursive includes**: {summary.get('recursive_task_includes', 0)}",
        f"- **Unique modules**: {summary.get('module_count', 0)}",
        f"- **Handlers referenced**: {summary.get('handler_count', 0)}",
        f"- **YAML parse failures**: {len(yaml_parse_failures)}",
        f"- **Unconstrained dynamic task includes**: {len(unconstrained_dynamic_task_includes)}",
        f"- **Unconstrained dynamic role includes**: {len(unconstrained_dynamic_role_includes)}",
    ]
    if yaml_parse_failures:
        lines.extend(["", "Parse failures detected:"])
        for item in yaml_parse_failures[:5]:
            file_name = str(item.get("file") or "<unknown>")
            line = item.get("line")
            column = item.get("column")
            location = (
                f"{file_name}:{line}:{column}"
                if line is not None and column is not None
                else file_name
            )
            error_text = str(item.get("error") or "parse error")
            lines.append(f"- `{location}`: {error_text}")
        if len(yaml_parse_failures) > 5:
            lines.append(
                f"- ... and {len(yaml_parse_failures) - 5} additional parse failures"
            )

    if unconstrained_dynamic_includes:
        lines.extend(["", "Unconstrained dynamic include hazards detected:"])
        for item in unconstrained_dynamic_includes[:5]:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file") or "<unknown>")
            task_name = str(item.get("task") or "(unnamed task)")
            target = str(item.get("target") or "")
            lines.append(f"- `{file_name}` / {task_name}: `{target}`")
        if len(unconstrained_dynamic_includes) > 5:
            lines.append(
                "- ... and "
                f"{len(unconstrained_dynamic_includes) - 5} additional unconstrained dynamic includes"
            )

    task_catalog = metadata.get("task_catalog") or []
    if metadata.get("detailed_catalog") and task_catalog:
        lines.extend(
            [
                "",
                "Detailed task catalog:",
                "",
                "| File | Task | Module | Parameters |",
                "| --- | --- | --- | --- |",
            ]
        )
        for entry in task_catalog:
            if not isinstance(entry, dict):
                continue
            lines.append(
                f"| `{entry.get('file', '')}` | {entry.get('name', '')} | `{entry.get('module', '')}` | {entry.get('parameters', '')} |"
            )

    return "\n".join(lines)


def _render_example_usage_section(metadata: dict) -> str:
    """Render inferred example playbook block for style guide output."""
    example = (metadata.get("doc_insights") or {}).get("example_playbook")
    if not example:
        return "No inferred example available."
    return f"```yaml\n{example}\n```"


def _build_molecule_scenario_lines(metadata: dict) -> list[str]:
    """Render optional molecule scenario bullet list for testing guidance."""
    molecule_scenarios = metadata.get("molecule_scenarios") or []
    scenario_lines: list[str] = []
    if molecule_scenarios:
        scenario_lines.extend(["", "Molecule scenarios detected:"])
        for scenario in molecule_scenarios:
            if not isinstance(scenario, dict):
                continue
            name = str(scenario.get("name") or "default")
            driver = str(scenario.get("driver") or "unknown")
            verifier = str(scenario.get("verifier") or "unknown")
            platforms = scenario.get("platforms") or []
            platform_summary = ", ".join(
                str(item) for item in platforms if isinstance(item, str)
            )
            if not platform_summary:
                platform_summary = "unspecified"
            scenario_lines.append(
                f"- `{name}` (driver: `{driver}`, verifier: `{verifier}`, platforms: {platform_summary})"
            )
    return scenario_lines


def _render_local_testing_section(metadata: dict) -> str:
    """Render local testing guidance including role-test and molecule hints."""
    role_tests = metadata.get("tests") or []
    scenario_lines = _build_molecule_scenario_lines(metadata)

    if role_tests:
        inventory = next(
            (item for item in role_tests if "inventory" in item), role_tests[0]
        )
        playbook = next(
            (
                item
                for item in role_tests
                if item.endswith(".yml") or item.endswith(".yaml")
            ),
            role_tests[0],
        )
        guidance = (
            "Run a quick local validation using bundled role tests:\n\n"
            "```bash\n"
            f"ansible-playbook -i {inventory} {playbook}\n"
            "```"
        )
        if scenario_lines:
            guidance += "\n" + "\n".join(scenario_lines)
        return guidance

    fallback = "Run `tox` or `pytest -q` locally to validate scanner behavior and generated output."
    if scenario_lines:
        fallback += "\n" + "\n".join(scenario_lines)
    return fallback


def _render_handlers_section(metadata: dict) -> str:
    """Render handler summary and optional handler catalog for style output."""
    features = metadata.get("features") or {}
    handler_names = parse_comma_values(str(features.get("handlers_notified", "none")))
    handler_files = metadata.get("handlers") or []
    summary = (metadata.get("doc_insights") or {}).get("task_summary", {})
    if not handler_names and not handler_files and not summary:
        return "No handler activity was detected."

    lines = [
        f"- **Handler files detected**: {len(handler_files)}",
        f"- **Handlers referenced by tasks**: {summary.get('handler_count', len(handler_names))}",
    ]
    if handler_names:
        lines.append("- **Named handlers**: " + ", ".join(handler_names))
    if handler_files:
        lines.append("")
        lines.append("Handler definition files:")
        lines.extend(f"- `{path}`" for path in handler_files)

    handler_catalog = metadata.get("handler_catalog") or []
    if metadata.get("detailed_catalog") and handler_catalog:
        lines.extend(
            [
                "",
                "Detailed handler catalog:",
                "",
                "| File | Handler | Module | Parameters |",
                "| --- | --- | --- | --- |",
            ]
        )
        for entry in handler_catalog:
            if not isinstance(entry, dict):
                continue
            lines.append(
                f"| `{entry.get('file', '')}` | {entry.get('name', '')} | `{entry.get('module', '')}` | {entry.get('parameters', '')} |"
            )

    return "\n".join(lines)


def _render_faq_pitfalls_section(default_filters: list, metadata: dict) -> str:
    """Render common scanner-detected pitfalls for role docs."""
    features = metadata.get("features") or {}
    lines = [
        "- Ensure default values are defined in `defaults/main.yml` so they are discoverable.",
        "- Keep task includes file-based when possible for better recursive scanning.",
    ]
    if int(features.get("recursive_task_includes", 0) or 0) > 0:
        lines.append(
            "- Nested include chains are detected; avoid heavily dynamic include paths when possible."
        )
    if default_filters:
        lines.append(
            "- `default()` usages are captured from source files; keep expressions readable for better docs."
        )
    return "\n".join(lines)


def _render_guide_operations_sections(section_id: str, metadata: dict) -> str | None:
    """Render style-guide sections for operational guidance."""
    if section_id == "basic_authorization":
        return (
            "Use custom vhost or directory directives to add HTTP Basic Authentication where needed.\n\n"
            "- Provide credential files such as `.htpasswd` from your playbook or a companion role.\n"
            "- Prefer explicit configuration blocks or custom templates over editing generated files in place.\n"
            "- Keep authentication settings alongside the related virtual host configuration so the access policy remains reviewable."
        )

    if section_id == "contributing":
        return (
            "Contributions are welcome.\n\n"
            "- Run `pytest -q` before submitting changes.\n"
            "- Run `tox` for full local validation and review artifact generation.\n"
            "- Update docs/templates when scanner behavior changes."
        )

    return None


def _render_guide_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Render one canonical section body for guided README output."""
    galaxy = (
        metadata.get("meta", {}).get("galaxy_info", {}) if metadata.get("meta") else {}
    )

    rendered = _render_guide_identity_sections(
        section_id,
        role_name,
        description,
        requirements,
        galaxy,
        metadata,
    )
    if rendered is not None:
        return rendered

    rendered = _render_guide_variable_sections(section_id, variables, metadata)
    if rendered is not None:
        return rendered

    rendered = _render_guide_task_sections(section_id, default_filters, metadata)
    if rendered is not None:
        return rendered

    rendered = _render_guide_operations_sections(section_id, metadata)
    if rendered is not None:
        return rendered

    rendered = _render_guide_misc_sections(section_id, default_filters, metadata)
    if rendered is not None:
        return rendered

    return ""


def _render_guide_misc_sections(
    section_id: str,
    default_filters: list,
    metadata: dict,
) -> str | None:
    """Render remaining style-guide sections not covered by other groups."""
    renderers = {
        "role_contents": lambda: _render_role_contents_section(metadata),
        "features": lambda: _render_features_section(metadata),
        "comparison": lambda: _render_comparison_section(metadata),
        "default_filters": lambda: _render_default_filters_section(default_filters),
    }
    renderer = renderers.get(section_id)
    return renderer() if renderer else None


def _render_role_contents_section(metadata: dict) -> str:
    """Render a compact count summary of discovered role subdirectories."""
    lines = ["The scanner collected these role subdirectories (counts):", ""]
    for key, items in metadata.items():
        if key in {
            "meta",
            "features",
            "comparison",
            "variable_insights",
            "doc_insights",
            "style_guide",
            "role_notes",
            "scanner_counters",
        }:
            continue
        if isinstance(items, list):
            lines.append(f"- **{key}**: {len(items)} files")
    return "\n".join(lines)


def _render_features_section(metadata: dict) -> str:
    """Render extracted role feature heuristics."""
    features = metadata.get("features") or {}
    if not features:
        return "No role features detected."
    return "\n".join(f"- **{key}**: {value}" for key, value in features.items())


def _render_comparison_section(metadata: dict) -> str:
    """Render baseline comparison metrics when available."""
    comparison = metadata.get("comparison")
    if not comparison:
        return "No comparison baseline provided."
    lines = [
        f"- **Baseline path**: {comparison['baseline_path']}",
        f"- **Target score**: {comparison['target_score']}/100",
        f"- **Baseline score**: {comparison['baseline_score']}/100",
        f"- **Score delta**: {comparison['score_delta']}",
        "",
    ]
    for metric, values in comparison["metrics"].items():
        lines.append(
            f"- **{metric}**: target={values['target']}, baseline={values['baseline']}, delta={values['delta']}"
        )
    return "\n".join(lines)


def _render_default_filters_section(default_filters: list) -> str:
    """Render undocumented default() findings in bullet-list form."""
    if not default_filters:
        return "No undocumented variables using `default()` were detected."
    lines = [
        "The scanner found undocumented variables using `default()` in role files:",
        "",
    ]
    for occ in default_filters:
        match = occ["match"].replace("`", "'")
        args = occ["args"].replace("`", "'")
        lines.append(f"- {occ['file']}:{occ['line_no']} - `{match}`")
        lines.append(f"  args: `{args}`")
    return "\n".join(lines)


def _generated_merge_markers(section_id: str) -> list[tuple[str, str]]:
    """Return supported hidden marker pairs for generated merge payloads."""
    return [
        (
            f"<!-- prism:generated:start:{section_id} -->",
            f"<!-- prism:generated:end:{section_id} -->",
        ),
        (
            f"<!-- ansible-role-doc:generated:start:{section_id} -->",
            f"<!-- ansible-role-doc:generated:end:{section_id} -->",
        ),
    ]


def _strip_prior_generated_merge_block(section: dict, guide_body: str) -> str:
    """Remove previously generated merge payload for a section, if present."""
    section_id = str(section.get("id") or "")
    cleaned = guide_body
    for start_marker, end_marker in _generated_merge_markers(section_id):
        start_idx = cleaned.find(start_marker)
        end_idx = cleaned.find(end_marker)
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            prefix = cleaned[:start_idx].rstrip()
            suffix = cleaned[end_idx + len(end_marker) :].lstrip()
            if prefix and suffix:
                cleaned = f"{prefix}\n\n{suffix}"
            else:
                cleaned = prefix or suffix

    # Backward compatibility for earlier merge output without markers.
    legacy_labels = ["\n\nGenerated content:\n"]
    if section_id == "requirements":
        legacy_labels.append("\n\nDetected requirements from scanner:\n")
    for label in legacy_labels:
        if label in cleaned:
            cleaned = cleaned.split(label, 1)[0].rstrip()

    return cleaned


def _resolve_section_content_mode(section: dict, modes: dict[str, str]) -> str:
    """Resolve content handling mode for a style section."""
    section_id = str(section.get("id") or "")
    guide_body = str(section.get("body") or "").strip()
    configured = str(modes.get(section_id) or "").strip().lower()
    if configured in {"generate", "replace", "merge"}:
        return configured
    if section_id == "requirements":
        return "merge"
    # Preserve source prose patterns for narrative sections while still
    # appending scanner-derived structured content.
    if guide_body and section_id in {
        "purpose",
        "task_summary",
        "local_testing",
        "handlers",
        "template_overrides",
        "faq_pitfalls",
        "contributing",
    }:
        return "merge"
    return "generate"


def _merge_section_body(
    section: dict,
    generated_body: str,
    guide_body: str,
) -> str:
    """Merge scanner-generated and style-guide content for a section."""
    cleaned_guide_body = _strip_prior_generated_merge_block(section, guide_body)
    if not cleaned_guide_body:
        return generated_body
    if not generated_body:
        return cleaned_guide_body
    if generated_body in cleaned_guide_body:
        return cleaned_guide_body
    section_id = str(section.get("id") or "")
    start_marker, end_marker = _generated_merge_markers(section_id)[0]
    if section_id == "requirements":
        return (
            f"{cleaned_guide_body}\n\n"
            "Detected requirements from scanner:\n"
            f"{start_marker}\n"
            f"{generated_body}\n"
            f"{end_marker}"
        )
    return (
        f"{cleaned_guide_body}\n\n"
        "Generated content:\n"
        f"{start_marker}\n"
        f"{generated_body}\n"
        f"{end_marker}"
    )


def _compose_section_body(section: dict, generated_body: str, mode: str) -> str:
    """Compose final section body according to configured mode."""
    guide_body = str(section.get("body") or "").strip()
    if mode == "replace":
        return guide_body or generated_body
    if mode == "merge":
        return _merge_section_body(section, generated_body, guide_body)
    return generated_body


def _default_ordered_style_sections() -> list[dict]:
    """Return default style sections when no style guide sections are supplied."""
    return [
        {"id": section_id, "title": title}
        for section_id, title in DEFAULT_SECTION_SPECS
    ]


def _apply_section_title_overrides(
    ordered_sections: list[dict],
    section_title_overrides: dict[str, str],
) -> list[dict]:
    """Apply metadata-driven section title overrides to a copied section list."""
    overridden_sections = [dict(section) for section in ordered_sections]
    for section in overridden_sections:
        override_title = section_title_overrides.get(section.get("id"))
        if override_title:
            section["title"] = override_title
    return overridden_sections


def _filter_ordered_sections_by_metadata(
    ordered_sections: list[dict],
    enabled_sections: set[str],
    keep_unknown_style_sections: bool,
) -> list[dict]:
    """Filter sections by unknown/enabled metadata controls."""
    filtered_sections = ordered_sections
    if not keep_unknown_style_sections:
        filtered_sections = [
            section for section in filtered_sections if section.get("id") != "unknown"
        ]
    if enabled_sections:
        filtered_sections = [
            section
            for section in filtered_sections
            if section.get("id") in enabled_sections
        ]
    return filtered_sections


def _filter_concise_readme_sections(ordered_sections: list[dict]) -> list[dict]:
    """Drop verbose sections and duplicate variable detail rows for concise output."""
    concise_sections = [
        section
        for section in ordered_sections
        if section.get("id") not in SCANNER_STATS_SECTION_IDS
    ]
    section_ids = [section.get("id") for section in concise_sections]
    if "variable_summary" in section_ids and "role_variables" in section_ids:
        concise_sections = [
            section
            for section in concise_sections
            if section.get("id") != "role_variables"
        ]
    return concise_sections


def _resolve_ordered_style_sections(
    style_guide: dict,
    metadata: dict,
) -> tuple[list[dict], set[str], dict[str, str], bool]:
    """Resolve ordered style-guide sections after scanner/readme config filters."""
    ordered_sections = list(style_guide.get("sections") or [])
    enabled_sections = set(metadata.get("enabled_sections") or [])
    section_title_overrides = metadata.get("section_title_overrides") or {}
    keep_unknown_style_sections = bool(metadata.get("keep_unknown_style_sections"))

    if not ordered_sections:
        ordered_sections = _default_ordered_style_sections()

    ordered_sections = _apply_section_title_overrides(
        ordered_sections,
        section_title_overrides,
    )
    ordered_sections = _filter_ordered_sections_by_metadata(
        ordered_sections,
        enabled_sections,
        keep_unknown_style_sections,
    )

    if metadata.get("concise_readme"):
        ordered_sections = _filter_concise_readme_sections(ordered_sections)

    return (
        ordered_sections,
        enabled_sections,
        metadata.get("section_content_modes") or {},
        bool(metadata.get("style_guide_skeleton")),
    )


def _render_style_guide_sections_into_parts(
    parts: list[str],
    ordered_sections: list[dict],
    style_guide: dict,
    style_guide_skeleton: bool,
    section_content_modes: dict[str, str],
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> None:
    """Append rendered style-guide sections into the markdown parts list."""
    for section in ordered_sections:
        _append_style_guide_section_heading(parts, section, style_guide)

        if style_guide_skeleton:
            continue

        body = _resolve_rendered_style_guide_section_body(
            section,
            section_content_modes,
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        )
        if not body:
            continue
        parts.append(body)
        parts.append("")


def _append_style_guide_section_heading(
    parts: list[str],
    section: dict,
    style_guide: dict,
) -> None:
    """Append a formatted heading for a style-guide section."""
    heading_level = int(section.get("level") or style_guide.get("section_level") or 2)
    parts.append(
        format_heading(
            section["title"],
            heading_level,
            style_guide.get("section_style", "setext"),
        )
    )
    parts.append("")


def _resolve_rendered_style_guide_section_body(
    section: dict,
    section_content_modes: dict[str, str],
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Return rendered section body after merge/unknown handling."""
    body = _render_guide_section_body(
        section["id"],
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    ).strip()
    mode = _resolve_section_content_mode(section, section_content_modes)
    body = _compose_section_body(section, body, mode)
    if section["id"] != "unknown":
        return body
    unknown_guide_body = str(section.get("body") or "").strip()
    if unknown_guide_body:
        return unknown_guide_body
    return "Style section retained from guide; scanner does not map this section yet."


def _append_scanner_report_section_if_enabled(
    parts: list[str],
    style_guide: dict,
    style_guide_skeleton: bool,
    scanner_report_relpath: str | None,
    include_scanner_report_link: bool,
    enabled_sections: set[str],
) -> None:
    """Append scanner report section when concise/section settings allow it."""
    if (
        style_guide_skeleton
        or not scanner_report_relpath
        or not include_scanner_report_link
        or (enabled_sections and "scanner_report" not in enabled_sections)
    ):
        return
    parts.append(
        format_heading(
            "Scanner report",
            int(style_guide.get("section_level") or 2),
            style_guide.get("section_style", "setext"),
        )
    )
    parts.append("")
    parts.append(
        f"Detailed scanner output is available in `{scanner_report_relpath}`. It includes task/module statistics, role-content inventory, baseline comparison details, and undocumented `default()` findings."
    )
    parts.append("")


def _render_readme_with_style_guide(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Render markdown following the structure of a guide README."""
    style_guide = metadata.get("style_guide") or {}
    (
        ordered_sections,
        enabled_sections,
        section_content_modes,
        style_guide_skeleton,
    ) = _resolve_ordered_style_sections(style_guide, metadata)

    rendered_title = role_name
    if style_guide.get("title_text"):
        rendered_title = role_name

    parts = [
        format_heading(rendered_title, 1, style_guide.get("title_style", "setext")),
        "",
        description,
        "",
    ]
    _render_style_guide_sections_into_parts(
        parts=parts,
        ordered_sections=ordered_sections,
        style_guide=style_guide,
        style_guide_skeleton=style_guide_skeleton,
        section_content_modes=section_content_modes,
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata,
    )

    scanner_report_relpath = metadata.get("scanner_report_relpath")
    _append_scanner_report_section_if_enabled(
        parts=parts,
        style_guide=style_guide,
        style_guide_skeleton=style_guide_skeleton,
        scanner_report_relpath=scanner_report_relpath,
        include_scanner_report_link=bool(
            metadata.get("include_scanner_report_link", True)
        ),
        enabled_sections=enabled_sections,
    )
    return "\n".join(parts).strip() + "\n"


def _build_scanner_report_markdown(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Render a scanner-focused markdown sidecar report."""
    return _report_build_markdown(
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
    features: dict | None = None,
    parse_failures: list[dict[str, object]] | None = None,
) -> dict[str, int | dict[str, int]]:
    """Summarize scanner findings by certainty and variable category."""
    return _report_extract_counters(
        variable_insights,
        default_filters,
        features,
        parse_failures,
    )


def _classify_provenance_issue(row: dict) -> str | None:
    """Return a stable issue category label for unresolved/ambiguous rows."""
    return _report_classify_provenance_issue(row)


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
    metadata = metadata or {}
    if metadata.get("style_guide"):
        rendered = _render_readme_with_style_guide(
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        )
        if write:
            Path(output).write_text(rendered, encoding="utf-8")
            return str(Path(output).resolve())
        return rendered

    if template:
        tpl_file = Path(template)
    else:
        tpl_file = Path(__file__).parent / "templates" / "README.md.j2"

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(tpl_file.parent)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template_obj = env.get_template(tpl_file.name)
    rendered = template_obj.render(
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata,
    )
    if write:
        Path(output).write_text(rendered, encoding="utf-8")
        return str(Path(output).resolve())
    return rendered


def render_runbook(
    role_name: str,
    metadata: dict | None = None,
    template: str | None = None,
) -> str:
    """Render a standalone runbook markdown document for a role."""
    return _runbook_render(role_name=role_name, metadata=metadata, template=template)


def _build_runbook_rows(metadata: dict | None) -> list[tuple[str, str, str]]:
    """Build normalized runbook rows: (file, task_name, step)."""
    return _runbook_build_rows(metadata)


def render_runbook_csv(metadata: dict | None = None) -> str:
    """Render runbook rows to CSV with columns: file, task_name, step."""
    return _runbook_render_csv(metadata)


def _build_requirements_display(
    *,
    requirements: list,
    meta: dict,
    features: dict,
    include_collection_checks: bool = True,
) -> tuple[list[str], list[str]]:
    """Build rendered requirements lines and collection compliance notes."""
    return _requirements_build_display(
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
    if not concise_readme:
        return None

    scanner_report_path = (
        Path(scanner_report_output)
        if scanner_report_output
        else out_path.with_suffix(".scan-report.md")
    )
    metadata["concise_readme"] = True
    metadata["include_scanner_report_link"] = include_scanner_report_link

    if dry_run:
        return scanner_report_path

    scanner_report_path.parent.mkdir(parents=True, exist_ok=True)
    scanner_report = _build_scanner_report_markdown(
        role_name=role_name,
        description=description,
        variables=display_variables,
        requirements=requirements_display,
        default_filters=undocumented_default_filters,
        metadata=metadata,
    )
    scanner_report_path.write_text(scanner_report, encoding="utf-8")
    metadata["scanner_report_relpath"] = os.path.relpath(
        scanner_report_path, out_path.parent
    )
    return scanner_report_path


def _resolve_scan_identity(
    role_path: str,
    role_name_override: str | None,
) -> tuple[Path, dict, str, str]:
    """Resolve role path, metadata, role name, and description."""
    rp = Path(role_path)
    if not rp.is_dir():
        raise FileNotFoundError(f"role path not found: {role_path}")
    meta = load_meta(role_path)
    galaxy = meta.get("galaxy_info", {}) if isinstance(meta, dict) else {}
    role_name = galaxy.get("role_name", rp.name)
    if role_name_override and (not galaxy.get("role_name") or role_name == "repo"):
        role_name = role_name_override
    description = galaxy.get("description", "")
    return rp, meta, role_name, description


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
    if runbook_output:
        rb_path = Path(runbook_output)
        rb_path.parent.mkdir(parents=True, exist_ok=True)
        rb_content = render_runbook(role_name, metadata)
        rb_path.write_text(rb_content, encoding="utf-8")
    if runbook_csv_output:
        rb_csv_path = Path(runbook_csv_output)
        rb_csv_path.parent.mkdir(parents=True, exist_ok=True)
        rb_csv_content = render_runbook_csv(metadata)
        rb_csv_path.write_text(rb_csv_content, encoding="utf-8")


def _apply_readme_section_config(
    metadata: dict, readme_section_config: dict | None
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
) -> tuple[list[dict], list[dict], dict]:
    """Collect variable insights, scanner counters, and secret-masked defaults."""
    variable_insights = build_variable_insights(
        role_path,
        seed_paths=vars_seed_paths,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_path_patterns,
        style_readme_path=style_readme_path,
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
    metadata: dict, vars_seed_paths: list[str] | None
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
    rendered = ""
    if output_format != "json":
        rendered = render_readme(
            str(out_path),
            role_name,
            description,
            display_variables,
            requirements_display,
            undocumented_default_filters,
            template,
            metadata,
            write=False,
        )

    final_content = render_final_output(
        rendered,
        output_format,
        role_name,
        payload={
            "role_name": role_name,
            "description": description,
            "variables": display_variables,
            "requirements": requirements_display,
            "default_filters": undocumented_default_filters,
            "metadata": metadata,
        },
    )
    if dry_run:
        return final_content
    return write_output(out_path, final_content)


def _prepare_scan_context(scan_options: dict) -> tuple[str, str, str, list, list, dict]:
    """Collect role metadata and scanner context required for rendering outputs."""
    base_context = _collect_scan_base_context(scan_options)
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


def _collect_scan_base_context(scan_options: dict) -> dict:
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


def _collect_scan_identity_and_artifacts(
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
) -> tuple[str, dict, str, str, str, dict, list, list, dict]:
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
    metadata: dict,
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
    metadata: dict,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
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
) -> dict:
    """Build the shared payload used for scanner report and primary output rendering."""
    return {
        "role_name": role_name,
        "description": description,
        "display_variables": display_variables,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "metadata": metadata,
    }


def _render_primary_scan_output(
    *,
    out_path: Path,
    output_format: str,
    template: str | None,
    dry_run: bool,
    output_payload: dict,
) -> str:
    """Render and optionally write the primary scan output."""
    return _render_and_write_scan_output(
        out_path=out_path,
        output_format=output_format,
        role_name=output_payload["role_name"],
        description=output_payload["description"],
        display_variables=output_payload["display_variables"],
        requirements_display=output_payload["requirements_display"],
        undocumented_default_filters=output_payload["undocumented_default_filters"],
        metadata=output_payload["metadata"],
        template=template,
        dry_run=dry_run,
    )


def _emit_scan_outputs(
    output: str,
    output_format: str,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    role_name: str,
    description: str,
    display_variables: dict,
    requirements_display: list,
    undocumented_default_filters: list,
    metadata: dict,
    template: str | None,
    dry_run: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> str:
    """Render primary outputs and optional sidecars for a scanner run."""
    out_path = resolve_output_path(output, output_format)
    output_payload = _build_scan_output_payload(
        role_name=role_name,
        description=description,
        display_variables=display_variables,
        requirements_display=requirements_display,
        undocumented_default_filters=undocumented_default_filters,
        metadata=metadata,
    )
    _write_concise_scanner_report_if_enabled(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        role_name=output_payload["role_name"],
        description=output_payload["description"],
        display_variables=output_payload["display_variables"],
        requirements_display=output_payload["requirements_display"],
        undocumented_default_filters=output_payload["undocumented_default_filters"],
        metadata=output_payload["metadata"],
        dry_run=dry_run,
    )
    result = _render_primary_scan_output(
        out_path=out_path,
        output_format=output_format,
        template=template,
        dry_run=dry_run,
        output_payload=output_payload,
    )
    if dry_run:
        return result
    _write_optional_runbook_outputs(
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        role_name=output_payload["role_name"],
        metadata=output_payload["metadata"],
    )
    return result


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
    )
    prepared = _prepare_run_scan_payload(scan_options)
    return _emit_scan_outputs(
        output=output,
        output_format=output_format,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_scanner_report_link=include_scanner_report_link,
        role_name=prepared["role_name"],
        description=prepared["description"],
        display_variables=prepared["display_variables"],
        requirements_display=prepared["requirements_display"],
        undocumented_default_filters=prepared["undocumented_default_filters"],
        metadata=prepared["metadata"],
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
    if runbook_output or runbook_csv_output:
        return True
    return detailed_catalog


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
) -> dict:
    """Build normalized scan options consumed by scan orchestration helpers."""
    return {
        "role_path": role_path,
        "role_name_override": role_name_override,
        "readme_config_path": readme_config_path,
        "include_vars_main": include_vars_main,
        "exclude_path_patterns": exclude_path_patterns,
        "detailed_catalog": detailed_catalog,
        "include_task_parameters": include_task_parameters,
        "include_task_runbooks": include_task_runbooks,
        "inline_task_runbooks": inline_task_runbooks,
        "include_collection_checks": include_collection_checks,
        "keep_unknown_style_sections": keep_unknown_style_sections,
        "adopt_heading_mode": adopt_heading_mode,
        "vars_seed_paths": vars_seed_paths,
        "style_readme_path": style_readme_path,
        "style_source_path": style_source_path,
        "style_guide_skeleton": style_guide_skeleton,
        "compare_role_path": compare_role_path,
        "fail_on_unconstrained_dynamic_includes": (
            fail_on_unconstrained_dynamic_includes
        ),
        "fail_on_yaml_like_task_annotations": (fail_on_yaml_like_task_annotations),
    }


def _prepare_run_scan_payload(scan_options: dict) -> dict:
    """Prepare role metadata and display payloads used by scan output emission."""
    (
        _rp,
        role_name,
        description,
        requirements_display,
        undocumented_default_filters,
        scan_context,
    ) = _prepare_scan_context(scan_options)
    return {
        "role_name": role_name,
        "description": description,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "display_variables": scan_context["display_variables"],
        "metadata": scan_context["metadata"],
    }
