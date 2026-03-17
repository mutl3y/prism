"""Core scanner implementation.

This module provides utilities to scan an Ansible role for common
patterns (for example uses of the `default()` filter), load role
metadata and variables, and render a README using a Jinja2 template.
"""

from __future__ import annotations

from collections import defaultdict
from fnmatch import fnmatch
import os
from pathlib import Path
import re
from typing import TypedDict
import yaml
import jinja2
from jinja2 import meta

from .doc_insights import build_doc_insights, parse_comma_values
from .output import render_final_output, resolve_output_path, write_output
from .pattern_config import load_pattern_config
from .style_guide import (
    detect_style_section_level,
    format_heading,
    normalize_style_heading,
    parse_style_readme,
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
_SECRET_NAME_TOKENS: tuple[str, ...] = tuple(_SENSITIVITY["name_tokens"])
_VAULT_MARKERS: tuple[str, ...] = tuple(_SENSITIVITY["vault_markers"])
_CREDENTIAL_PREFIXES: tuple[str, ...] = tuple(_SENSITIVITY["credential_prefixes"])
_URL_PREFIXES: tuple[str, ...] = tuple(_SENSITIVITY["url_prefixes"])

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

SECTION_CONFIG_FILENAME = ".ansible_role_doc.yml"
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
TASK_INCLUDE_KEYS = {
    "include_tasks",
    "import_tasks",
    "ansible.builtin.include_tasks",
    "ansible.builtin.import_tasks",
}
INCLUDE_VARS_KEYS = {
    "include_vars",
    "ansible.builtin.include_vars",
}
SET_FACT_KEYS = {
    "set_fact",
    "ansible.builtin.set_fact",
}
TASK_BLOCK_KEYS = ("block", "rescue", "always")
TASK_META_KEYS = {
    "name",
    "when",
    "tags",
    "register",
    "notify",
    "vars",
    "become",
    "become_user",
    "become_method",
    "check_mode",
    "changed_when",
    "failed_when",
    "ignore_errors",
    "ignore_unreachable",
    "delegate_to",
    "run_once",
    "loop",
    "loop_control",
    "with_items",
    "with_dict",
    "with_fileglob",
    "with_first_found",
    "with_nested",
    "with_sequence",
    "environment",
    "args",
    "retries",
    "delay",
    "until",
    "throttle",
    "no_log",
}

DEFAULT_RE = re.compile(
    r"""(?P<context>.{0,40}?)(\|\s*default\b|\bdefault\s*\()\s*(?P<args>[^)\n]{0,200})""",
    flags=re.IGNORECASE,
)

DEFAULT_STYLE_GUIDE_SOURCE_PATH = (
    Path(__file__).parent / "templates" / "STYLE_GUIDE_SOURCE.md"
)
DEFAULT_STYLE_GUIDE_SOURCE_FILENAME = "STYLE_GUIDE_SOURCE.md"
ENV_STYLE_GUIDE_SOURCE_PATH = "ANSIBLE_ROLE_DOC_STYLE_SOURCE"
XDG_DATA_HOME_ENV = "XDG_DATA_HOME"
STYLE_GUIDE_DATA_DIRNAME = "ansible-role-doc"
SYSTEM_STYLE_GUIDE_SOURCE_PATH = (
    Path("/var/lib") / STYLE_GUIDE_DATA_DIRNAME / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME
)
DEFAULT_SECTION_DISPLAY_TITLES_PATH = (
    Path(__file__).parent / "data" / "section_display_titles.yml"
)

DEFAULT_TARGET_RE = re.compile(r"\b(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\|\s*default\b")
JINJA_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
VAULT_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*!vault\b", re.MULTILINE)
MARKDOWN_VAR_BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
MARKDOWN_VAR_TABLE_RE = re.compile(r"^\|\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\|")
MARKDOWN_VAR_BULLET_RE = re.compile(
    r"^\s*[-*+]\s+`?([A-Za-z_][A-Za-z0-9_]*)`?(?:\s*[:|-]|\s*$)"
)
ROLE_NOTES_RE = re.compile(
    r"^\s*#\s*<notes>\s*(warning|deprecated|note|additional|additionals)?\s*:?\s*(.*)$",
    flags=re.IGNORECASE,
)
_JINJA_AST_ENV = jinja2.Environment()

IGNORED_IDENTIFIERS: set[str] = _POLICY["ignored_identifiers"]


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


def _normalize_style_heading(heading: str) -> str:
    """Backward-compatible alias for style heading normalization."""
    return normalize_style_heading(heading)


def _detect_style_section_level(lines: list[str]) -> int:
    """Backward-compatible alias for style section-level detection."""
    return detect_style_section_level(lines)


def _format_heading(text: str, level: int, style: str) -> str:
    """Backward-compatible alias for heading formatting."""
    return format_heading(text, level, style)


def _default_style_guide_user_path() -> Path:
    """Return user-level style guide path honoring XDG conventions."""
    xdg_data_home = os.environ.get(XDG_DATA_HOME_ENV)
    if xdg_data_home:
        data_home = Path(xdg_data_home).expanduser()
    else:
        data_home = (Path.home() / ".local" / "share").expanduser()
    return data_home / STYLE_GUIDE_DATA_DIRNAME / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME


def resolve_default_style_guide_source(explicit_path: str | None = None) -> str:
    """Resolve default style guide source path using Linux-aware precedence.

    Precedence (first existing path wins):

    1. ``$ANSIBLE_ROLE_DOC_STYLE_SOURCE``
    2. ``./STYLE_GUIDE_SOURCE.md``
    3. ``$XDG_DATA_HOME/ansible-role-doc/STYLE_GUIDE_SOURCE.md``
       (or ``~/.local/share/...`` fallback)
    4. ``/var/lib/ansible-role-doc/STYLE_GUIDE_SOURCE.md``
    5. bundled package template path
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

    candidates.append(Path.cwd() / DEFAULT_STYLE_GUIDE_SOURCE_FILENAME)
    candidates.append(_default_style_guide_user_path())
    candidates.append(SYSTEM_STYLE_GUIDE_SOURCE_PATH)
    candidates.append(DEFAULT_STYLE_GUIDE_SOURCE_PATH)

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    return str(DEFAULT_STYLE_GUIDE_SOURCE_PATH.resolve())


def _normalize_exclude_patterns(exclude_paths: list[str] | None) -> list[str]:
    """Return normalized glob patterns used to exclude role-relative paths."""
    if not exclude_paths:
        return []
    return [
        item.strip() for item in exclude_paths if isinstance(item, str) and item.strip()
    ]


def _is_relpath_excluded(relpath: str, exclude_paths: list[str] | None) -> bool:
    """Return True when a role-relative path should be excluded."""
    normalized = relpath.replace("\\", "/").lstrip("./")
    for pattern in _normalize_exclude_patterns(exclude_paths):
        if fnmatch(normalized, pattern) or fnmatch(f"{normalized}/", pattern):
            return True
        if "/" not in pattern and normalized.split("/", 1)[0] == pattern:
            return True
    return False


def _is_path_excluded(
    path: Path, role_root: Path, exclude_paths: list[str] | None
) -> bool:
    """Return True when an absolute path resolves to an excluded role-relative path."""
    try:
        relpath = str(path.resolve().relative_to(role_root.resolve()))
    except ValueError:
        return False
    return _is_relpath_excluded(relpath, exclude_paths)


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


def _scan_text_for_default_filters_with_ast(text: str, lines: list[str]) -> list[dict]:
    """Return occurrences discovered via Jinja AST parsing."""
    if "{{" not in text and "{%" not in text:
        return []
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except Exception:
        return []

    occurrences: list[dict] = []
    for node in parsed.find_all(jinja2.nodes.Filter):
        if node.name != "default":
            continue
        line_no = int(getattr(node, "lineno", 1) or 1)
        line_no = max(1, min(line_no, len(lines) if lines else 1))
        line = lines[line_no - 1] if lines else ""

        target = _stringify_jinja_node(getattr(node, "node", None)).strip()
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )

        if target:
            match = f"{target} | default({args})" if args else f"{target} | default()"
        else:
            match = line.strip()

        occurrences.append(
            {
                "line_no": line_no,
                "line": line,
                "match": match,
                "args": args,
            }
        )
    return occurrences


def _stringify_jinja_node(node: object) -> str:
    """Best-effort compact string rendering for Jinja AST nodes."""
    if node is None:
        return ""
    if isinstance(node, jinja2.nodes.Const):
        return str(node.value)
    if isinstance(node, jinja2.nodes.Name):
        return node.name
    if isinstance(node, jinja2.nodes.Getattr):
        base = _stringify_jinja_node(node.node)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, jinja2.nodes.Getitem):
        base = _stringify_jinja_node(node.node)
        arg = _stringify_jinja_node(node.arg)
        return f"{base}[{arg}]" if base else f"[{arg}]"
    if isinstance(node, jinja2.nodes.Filter):
        base = _stringify_jinja_node(node.node)
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )
        if args:
            return f"{base} | {node.name}({args})"
        return f"{base} | {node.name}".strip()
    if isinstance(node, jinja2.nodes.Call):
        callee = _stringify_jinja_node(node.node)
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )
        return f"{callee}({args})" if callee else f"({args})"
    if isinstance(node, jinja2.nodes.Test):
        left = _stringify_jinja_node(node.node)
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )
        if args:
            return f"{left} is {node.name}({args})"
        return f"{left} is {node.name}".strip()
    if isinstance(node, jinja2.nodes.TemplateData):
        return node.data.strip()
    return ""


def _collect_undeclared_jinja_variables(text: str) -> set[str]:
    """Collect undeclared variable names from Jinja template text."""
    if "{{" not in text and "{%" not in text:
        return set()
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except Exception:
        return set()
    try:
        return set(meta.find_undeclared_variables(parsed))
    except Exception:
        # Some Ansible-specific filters are unknown to plain Jinja and can
        # break introspection. Fall back to AST name scanning.
        return _collect_undeclared_jinja_variables_from_ast(parsed)


def _collect_undeclared_jinja_variables_from_ast(
    parsed: jinja2.nodes.Template,
) -> set[str]:
    """Collect variable names from Jinja AST without meta introspection.

    Excludes names locally bound by Jinja control flow constructs so loop
    variables, macro parameters, and ``set`` targets are not treated as
    external inputs.
    """
    local_bound = _collect_jinja_local_bindings(parsed)
    names: set[str] = set()
    for node in parsed.find_all(jinja2.nodes.Name):
        if getattr(node, "ctx", None) != "load":
            continue
        if isinstance(node.name, str) and node.name:
            if node.name in local_bound:
                continue
            names.add(node.name)
    return names


def _collect_jinja_local_bindings_from_text(text: str) -> set[str]:
    """Collect locally bound Jinja variable names from raw template text."""
    if "{{" not in text and "{%" not in text:
        return set()
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except Exception:
        return set()
    return _collect_jinja_local_bindings(parsed)


def _collect_jinja_local_bindings(parsed: jinja2.nodes.Template) -> set[str]:
    """Collect names introduced by local Jinja scopes in a template."""
    local_names: set[str] = set()

    for for_node in parsed.find_all(jinja2.nodes.For):
        local_names.update(
            _extract_jinja_name_targets(getattr(for_node, "target", None))
        )

    for macro_node in parsed.find_all(jinja2.nodes.Macro):
        for arg in getattr(macro_node, "args", []) or []:
            if isinstance(arg, jinja2.nodes.Name) and isinstance(arg.name, str):
                local_names.add(arg.name)

    for assign_node in parsed.find_all(jinja2.nodes.Assign):
        local_names.update(
            _extract_jinja_name_targets(getattr(assign_node, "target", None))
        )

    for assign_block in parsed.find_all(jinja2.nodes.AssignBlock):
        local_names.update(
            _extract_jinja_name_targets(getattr(assign_block, "target", None))
        )

    return local_names


def _extract_jinja_name_targets(node: object) -> set[str]:
    """Extract identifier names from Jinja assignment/loop target nodes."""
    if node is None:
        return set()
    if isinstance(node, jinja2.nodes.Name) and isinstance(node.name, str):
        return {node.name}

    names: set[str] = set()
    for child in getattr(node, "items", []) or []:
        names.update(_extract_jinja_name_targets(child))
    return names


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

        fence_match = re.match(r"^\s*([`~]{3,})", line)
        if fence_match:
            marker = fence_match.group(1)
            marker_char = marker[0]
            marker_len = len(marker)
            if not in_fence:
                in_fence = True
                fence_char = marker_char
                fence_len = marker_len
            elif marker_char == fence_char and marker_len >= fence_len:
                in_fence = False
                fence_char = ""
                fence_len = 0
            continue

        if in_fence:
            continue

        atx_match = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if atx_match:
            level = len(atx_match.group(1))
            if level <= 2:
                in_variable_section = _is_readme_variable_section_heading(
                    atx_match.group(2).strip()
                )
            continue

        if line.strip() and re.match(r"^[-=]{3,}\s*$", next_line):
            in_variable_section = _is_readme_variable_section_heading(line.strip())
            continue

        if not in_variable_section:
            continue

        for pattern in (
            MARKDOWN_VAR_BACKTICK_RE,
            MARKDOWN_VAR_TABLE_RE,
            MARKDOWN_VAR_BULLET_RE,
        ):
            for match in pattern.findall(line):
                lowered = match.lower()
                if lowered in IGNORED_IDENTIFIERS or lowered.startswith("ansible_"):
                    continue
                names.add(match)

    return names


def _collect_readme_input_variables(role_path: str) -> set[str]:
    """Extract variable names documented in ``README.md`` when present."""
    readme_path = Path(role_path) / "README.md"
    if not readme_path.is_file():
        return set()
    try:
        text = readme_path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return _extract_readme_input_variables(text)


def _extract_default_target_var(occurrence: dict) -> str | None:
    """Extract the variable name used with ``| default(...)`` when available."""
    line = str(occurrence.get("line") or occurrence.get("match") or "")
    match = DEFAULT_TARGET_RE.search(line)
    if not match:
        return None
    return match.group("var")


def _collect_task_files(
    role_root: Path,
    exclude_paths: list[str] | None = None,
) -> list[Path]:
    """Collect task files reachable from ``tasks/main.yml`` recursively."""
    tasks_dir = role_root / "tasks"
    if not tasks_dir.is_dir():
        return []

    entrypoints = [tasks_dir / "main.yml"] if (tasks_dir / "main.yml").exists() else []
    if not entrypoints:
        entrypoints = sorted(
            path
            for path in tasks_dir.rglob("*")
            if path.is_file()
            and path.suffix in {".yml", ".yaml"}
            and not _is_path_excluded(path, role_root, exclude_paths)
        )

    discovered: list[Path] = []
    pending = list(entrypoints)
    seen: set[Path] = set()
    while pending:
        current = pending.pop(0).resolve()
        if current in seen or not current.is_file():
            continue
        if _is_path_excluded(current, role_root, exclude_paths):
            continue
        seen.add(current)
        discovered.append(current)

        data = _load_yaml_file(current)
        for include_target in _iter_task_include_targets(data):
            resolved = _resolve_task_include(role_root, current, include_target)
            if (
                resolved is not None
                and resolved not in seen
                and not _is_path_excluded(resolved, role_root, exclude_paths)
            ):
                pending.append(resolved)

    return sorted(discovered, key=lambda path: str(path.relative_to(role_root)))


def _load_yaml_file(file_path: Path) -> object | None:
    """Load a YAML file and return its contents, or ``None`` on failure."""
    try:
        return yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_task_include_targets(data: object) -> list[str]:
    """Return include/import task targets found in a task YAML structure."""
    targets: list[str] = []
    for task in _iter_task_mappings(data):
        for key in TASK_INCLUDE_KEYS:
            if key not in task:
                continue
            value = task[key]
            if isinstance(value, str):
                targets.append(value)
            elif isinstance(value, dict):
                file_value = value.get("file") or value.get("_raw_params")
                if isinstance(file_value, str):
                    targets.append(file_value)
    return targets


def _iter_task_mappings(data: object):
    """Yield task dictionaries from a YAML task document recursively."""
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            yield item
            for key in TASK_BLOCK_KEYS:
                nested = item.get(key)
                if nested is not None:
                    yield from _iter_task_mappings(nested)


def _resolve_task_include(
    role_root: Path, current_file: Path, include_target: str
) -> Path | None:
    """Resolve an included task file relative to the current task file or tasks dir."""
    candidate = include_target.strip()
    if not candidate or "{{" in candidate or "{%" in candidate:
        return None

    path = Path(candidate)
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.append((current_file.parent / path).resolve())
        candidates.append((role_root / "tasks" / path).resolve())

    if not path.suffix:
        candidates.extend(resolved.with_suffix(".yml") for resolved in list(candidates))

    for resolved in candidates:
        if not resolved.is_file():
            continue
        try:
            resolved.relative_to(role_root)
        except ValueError:
            continue
        return resolved

    return None


def _collect_include_vars_files(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[Path]:
    """Return var files referenced by static ``include_vars`` tasks within the role.

    Only files whose paths can be resolved to a concrete file inside the role
    directory are returned.  Dynamic paths containing Jinja2 expressions are
    silently ignored.
    """
    role_root = Path(role_path).resolve()
    task_files = _collect_task_files(role_root, exclude_paths=exclude_paths)
    result: list[Path] = []
    seen: set[Path] = set()
    for task_file in task_files:
        data = _load_yaml_file(task_file)
        for task in _iter_task_mappings(data):
            for key in INCLUDE_VARS_KEYS:
                if key not in task:
                    continue
                value = task[key]
                ref: str | None = None
                if isinstance(value, str):
                    ref = value
                elif isinstance(value, dict):
                    ref = value.get("file") or value.get("name")
                if not ref or "{{" in ref or "{%" in ref:
                    continue
                for candidate in (
                    (task_file.parent / ref).resolve(),
                    (role_root / "vars" / ref).resolve(),
                    (role_root / ref).resolve(),
                ):
                    if candidate.is_file() and candidate not in seen:
                        try:
                            candidate.relative_to(role_root)
                        except ValueError:
                            continue
                        seen.add(candidate)
                        result.append(candidate)
                        break
    return result


def _collect_set_fact_names(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> set[str]:
    """Return variable names assigned by ``set_fact`` tasks within the role.

    Only names with static (non-templated) keys are returned.
    """
    role_root = Path(role_path).resolve()
    task_files = _collect_task_files(role_root, exclude_paths=exclude_paths)
    names: set[str] = set()
    for task_file in task_files:
        data = _load_yaml_file(task_file)
        for task in _iter_task_mappings(data):
            for key in SET_FACT_KEYS:
                if key not in task:
                    continue
                value = task[key]
                if isinstance(value, dict):
                    for vname in value:
                        if isinstance(vname, str) and "{{" not in vname:
                            names.add(vname)
    return names


def _find_variable_line_in_yaml(file_path: Path, var_name: str) -> int | None:
    """Return 1-indexed line where ``var_name`` is defined in a YAML file."""
    pattern = re.compile(rf"^\s*{re.escape(var_name)}\s*:")
    try:
        for idx, line in enumerate(file_path.read_text(encoding="utf-8").splitlines()):
            if pattern.match(line):
                return idx + 1
    except OSError:
        return None
    return None


def _collect_dynamic_include_vars_refs(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[str]:
    """Return dynamic include_vars references that cannot be statically resolved."""
    role_root = Path(role_path).resolve()
    refs: list[str] = []
    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        for task in _iter_task_mappings(data):
            for key in INCLUDE_VARS_KEYS:
                if key not in task:
                    continue
                value = task[key]
                ref: str | None = None
                if isinstance(value, str):
                    ref = value
                elif isinstance(value, dict):
                    ref = value.get("file") or value.get("name")
                if ref and ("{{" in ref or "{%" in ref):
                    refs.append(ref)
    return refs


def _extract_role_notes_from_comments(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict[str, list[str]]:
    """Extract comment-driven role notes from YAML files.

    Supported syntax:
        # <notes> Warning: text
        # <notes> Deprecated: text
        # <notes> Note: text
    """
    role_root = Path(role_path).resolve()
    categories: dict[str, list[str]] = {
        "warnings": [],
        "deprecations": [],
        "notes": [],
        "additionals": [],
    }
    files: list[Path] = []
    files.extend(_collect_task_files(role_root, exclude_paths=exclude_paths))
    for rel in ("defaults/main.yml", "vars/main.yml", "handlers/main.yml"):
        candidate = role_root / rel
        if candidate.is_file() and not _is_path_excluded(
            candidate, role_root, exclude_paths
        ):
            files.append(candidate)

    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        i = 0
        while i < len(lines):
            line = lines[i]
            match = ROLE_NOTES_RE.match(line)
            if not match:
                i += 1
                continue
            note_type = (match.group(1) or "note").lower()
            text = (match.group(2) or "").strip()
            continuation: list[str] = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if ROLE_NOTES_RE.match(next_line):
                    break
                cont_match = re.match(r"^\s*#\s+(.+)$", next_line)
                if not cont_match:
                    break
                continuation.append(cont_match.group(1).strip())
                j += 1
            if continuation:
                text = " ".join(part for part in [text, *continuation] if part)
            if text:
                if note_type == "warning":
                    categories["warnings"].append(text)
                elif note_type == "deprecated":
                    categories["deprecations"].append(text)
                elif note_type in {"additional", "additionals"}:
                    categories["additionals"].append(text)
                else:
                    categories["notes"].append(text)
            i = j if j > i + 1 else i + 1

    return categories


def load_meta(role_path: str) -> dict:
    """Load the role metadata file ``meta/main.yml`` if present.

    Returns a mapping (empty if missing or unparsable).
    """
    meta_file = Path(role_path) / "meta" / "main.yml"
    if meta_file.exists():
        try:
            return yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


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
    subdirs = ["defaults"]
    if include_vars_main:
        subdirs.append("vars")

    for sub in subdirs:
        p = Path(role_path) / sub / "main.yml"
        if p.exists():
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    vars_out.update(data)
            except Exception:
                continue
    for extra_path in _collect_include_vars_files(
        role_path, exclude_paths=exclude_paths
    ):
        try:
            data = yaml.safe_load(extra_path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                vars_out.update(data)
        except Exception:
            continue
    return vars_out


def load_requirements(role_path: str) -> list:
    """Load ``meta/requirements.yml`` as a list, or return an empty list."""
    p = Path(role_path) / "meta" / "requirements.yml"
    if p.exists():
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or []
        except Exception:
            return []
    return []


def _format_requirement_line(item: object) -> str:
    """Format one requirement entry into a markdown-safe display line."""
    if isinstance(item, dict):
        source_value = item.get("src") or item.get("name") or ""
        line = str(source_value)
        version = item.get("version")
        if version:
            line += f" (version: {version})"
        return line
    return str(item)


def normalize_requirements(requirements: list) -> list[str]:
    """Normalize requirements entries to display strings."""
    lines = [_format_requirement_line(item).strip() for item in requirements]
    return [line for line in lines if line]


def _normalize_meta_role_dependencies(meta: dict) -> list[str]:
    """Normalize role dependencies from ``meta/main.yml`` for README output."""
    dependencies = meta.get("dependencies") if isinstance(meta, dict) else None
    if not isinstance(dependencies, list):
        return []
    lines = [_format_requirement_line(item).strip() for item in dependencies]
    return [line for line in lines if line]


def _extract_collection_from_module_name(module_name: str) -> str | None:
    """Return collection prefix from a fully-qualified module name."""
    parts = module_name.split(".")
    if len(parts) < 3:
        return None
    collection = ".".join(parts[:2]).strip()
    if not collection or collection.startswith("ansible."):
        return None
    return collection


def _extract_declared_collections_from_meta(meta: dict) -> set[str]:
    """Extract declared non-ansible collections from ``meta/main.yml`` content."""
    declared: set[str] = set()
    galaxy = meta.get("galaxy_info") if isinstance(meta, dict) else None
    if not isinstance(galaxy, dict):
        return declared
    collections_raw = galaxy.get("collections")
    if not isinstance(collections_raw, list):
        return declared
    for item in collections_raw:
        if not isinstance(item, str):
            continue
        candidate = item.strip()
        if not candidate or candidate.startswith("ansible."):
            continue
        if re.match(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$", candidate):
            declared.add(candidate)
    return declared


def _extract_declared_collections_from_requirements(requirements: list) -> set[str]:
    """Extract declared non-ansible collections from ``meta/requirements.yml``."""
    declared: set[str] = set()
    for item in requirements:
        raw: object = item
        if isinstance(item, dict):
            raw = item.get("src") or item.get("name") or ""
        if not isinstance(raw, str):
            continue
        candidate = raw.strip().split()[0]
        if not candidate or candidate.startswith("ansible."):
            continue
        if re.match(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$", candidate):
            declared.add(candidate)
    return declared


def _build_collection_compliance_notes(
    *,
    features: dict,
    meta: dict,
    requirements: list,
) -> list[str]:
    """Build human-readable notes about collection declaration coverage."""
    raw_collections = str(features.get("external_collections", "none")).strip()
    if not raw_collections or raw_collections == "none":
        return []

    detected = {item.strip() for item in raw_collections.split(",") if item.strip()}
    if not detected:
        return []

    declared_meta = _extract_declared_collections_from_meta(meta)
    declared_requirements = _extract_declared_collections_from_requirements(
        requirements
    )
    missing_meta = sorted(detected - declared_meta)
    missing_requirements = sorted(detected - declared_requirements)

    notes = [
        "Detected non-ansible collections from task usage: "
        + ", ".join(sorted(detected))
        + "."
    ]
    if missing_meta:
        notes.append(
            "Missing from meta/main.yml galaxy_info.collections: "
            + ", ".join(missing_meta)
            + "."
        )
    if missing_requirements:
        notes.append(
            "Missing from meta/requirements.yml: "
            + ", ".join(missing_requirements)
            + "."
        )
    return notes


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


def extract_role_features(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Extract adaptive role features from tasks and role structure.

    These heuristics are intentionally lightweight and update automatically
    as task files change, providing richer documentation without manual edits.
    """
    role_root = Path(role_path).resolve()
    task_files = _collect_task_files(role_root, exclude_paths=exclude_paths)

    include_count = 0
    tasks_scanned = 0
    privileged_tasks = 0
    conditional_tasks = 0
    tagged_tasks = 0
    modules: set[str] = set()
    external_collections: set[str] = set()
    handlers_notified: set[str] = set()

    for task_file in task_files:
        data = _load_yaml_file(task_file)
        include_count += len(_iter_task_include_targets(data))
        for task in _iter_task_mappings(data):
            tasks_scanned += 1
            module_name = _detect_task_module(task)
            if module_name:
                modules.add(module_name)
                collection = _extract_collection_from_module_name(module_name)
                if collection:
                    external_collections.add(collection)

            if bool(task.get("become")):
                privileged_tasks += 1
            if "when" in task:
                conditional_tasks += 1
            if task.get("tags"):
                tagged_tasks += 1

            notify = task.get("notify")
            if isinstance(notify, str):
                handlers_notified.add(notify)
            elif isinstance(notify, list):
                handlers_notified.update(
                    item for item in notify if isinstance(item, str)
                )

    return {
        "task_files_scanned": len(task_files),
        "tasks_scanned": tasks_scanned,
        "recursive_task_includes": include_count,
        "unique_modules": ", ".join(sorted(modules)) if modules else "none",
        "external_collections": (
            ", ".join(sorted(external_collections)) if external_collections else "none"
        ),
        "handlers_notified": (
            ", ".join(sorted(handlers_notified)) if handlers_notified else "none"
        ),
        "privileged_tasks": privileged_tasks,
        "conditional_tasks": conditional_tasks,
        "tagged_tasks": tagged_tasks,
    }


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


def _infer_variable_type(value: object) -> str:
    """Infer a lightweight type label for rendered variable summaries."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if value is None:
        return "null"
    return "str"


def _format_inline_yaml(value: object) -> str:
    """Render a value as compact inline YAML for README tables."""
    text = yaml.safe_dump(value, default_flow_style=True, sort_keys=False).strip()
    return text.replace("\n", " ").replace("...", "").strip()


def _looks_secret_name(name: str) -> bool:
    """Return True when a variable name suggests secret/sensitive content."""
    lowered = name.lower()
    return any(token in lowered for token in _SECRET_NAME_TOKENS)


def _resembles_password_like(value: object) -> bool:
    """Return True when a string value looks like a credential/token."""
    if not isinstance(value, str):
        return False

    raw = value.strip().strip("'\"")
    if not raw:
        return False
    lowered = raw.lower()

    if any(marker in lowered for marker in _VAULT_MARKERS):
        return True
    if raw.startswith(_CREDENTIAL_PREFIXES):
        return True
    if raw.startswith(_URL_PREFIXES):
        return False
    if " " in raw or "{{" in raw or "}}" in raw:
        return False

    has_lower = any(char.islower() for char in raw)
    has_upper = any(char.isupper() for char in raw)
    has_digit = any(char.isdigit() for char in raw)
    has_symbol = any(not char.isalnum() for char in raw)
    class_count = sum((has_lower, has_upper, has_digit, has_symbol))

    if len(raw) >= 24 and class_count >= 2:
        return True
    if len(raw) >= 12 and class_count >= 3:
        return True
    return False


def _is_sensitive_variable(name: str, value: object) -> bool:
    """Return True when variable should be treated as sensitive for output."""
    if _looks_secret_value(value):
        return True
    if _looks_secret_name(name) and _resembles_password_like(value):
        return True
    return False


def _looks_secret_value(value: object) -> bool:
    """Return True when a value appears to be vaulted or sensitive."""
    if isinstance(value, str):
        lowered = value.lower()
        return any(
            marker in lowered for marker in _VAULT_MARKERS
        ) or lowered.startswith("vault_")
    return False


def _read_seed_yaml(path: Path) -> tuple[dict, set[str]]:
    """Read a seed vars YAML file and return mapping plus detected secret keys."""
    text = path.read_text(encoding="utf-8")
    secret_keys = set(VAULT_KEY_RE.findall(text))
    try:
        data = yaml.safe_load(text)
    except Exception:
        sanitized = re.sub(
            r":\s*!vault\b[^\n]*\n(?:[ \t]+.*\n?)*",
            ': "<vault>"\n',
            text,
            flags=re.MULTILINE,
        )
        try:
            data = yaml.safe_load(sanitized)
        except Exception:
            data = None
    if not isinstance(data, dict):
        return {}, secret_keys
    parsed = {key: value for key, value in data.items() if isinstance(key, str)}
    for key, value in parsed.items():
        if _is_sensitive_variable(key, value):
            secret_keys.add(key)
    return parsed, secret_keys


def _resolve_seed_var_files(seed_paths: list[str] | None) -> list[Path]:
    """Resolve seed var file/dir inputs into concrete YAML files."""
    files: list[Path] = []
    if not seed_paths:
        return files
    for raw_path in seed_paths:
        seed_path = Path(raw_path).expanduser().resolve()
        if seed_path.is_file() and seed_path.suffix in {".yml", ".yaml"}:
            files.append(seed_path)
            continue
        if seed_path.is_dir():
            files.extend(
                sorted(
                    candidate
                    for candidate in seed_path.rglob("*")
                    if candidate.is_file() and candidate.suffix in {".yml", ".yaml"}
                )
            )
    return files


def load_seed_variables(seed_paths: list[str] | None) -> tuple[dict, set[str], dict]:
    """Load external seed variables from files/directories.

    Returns ``(values, secret_names, source_map)``.
    """
    values: dict = {}
    secret_names: set[str] = set()
    source_map: dict[str, str] = {}
    for path in _resolve_seed_var_files(seed_paths):
        file_values, file_secrets = _read_seed_yaml(path)
        values.update(file_values)
        secret_names.update(file_secrets)
        for key in file_values:
            source_map[key] = str(path)
    return values, secret_names, source_map


def _collect_referenced_variable_names(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> set[str]:
    """Collect likely variable references from role tasks/templates/handlers files."""
    role_root = Path(role_path).resolve()
    candidates: set[str] = set()
    scan_dirs = ["tasks", "templates", "handlers"]
    for dirname in scan_dirs:
        root = role_root / dirname
        if not root.is_dir():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if _is_path_excluded(file_path, role_root, exclude_paths):
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError, OSError:
                continue
            local_bindings = _collect_jinja_local_bindings_from_text(text)
            for name in _collect_undeclared_jinja_variables(text):
                lowered = name.lower()
                if lowered in IGNORED_IDENTIFIERS or lowered.startswith("ansible_"):
                    continue
                candidates.add(name)
            for match in JINJA_VAR_RE.findall(text):
                lowered = match.lower()
                if (
                    lowered not in IGNORED_IDENTIFIERS
                    and not lowered.startswith("ansible_")
                    and match not in local_bindings
                ):
                    candidates.add(match)
            if file_path.suffix in {".yml", ".yaml"}:
                for line in text.splitlines():
                    if "when:" not in line:
                        continue
                    expression = line.split("when:", 1)[1]
                    for token in JINJA_IDENTIFIER_RE.findall(expression):
                        lowered = token.lower()
                        if lowered in IGNORED_IDENTIFIERS:
                            continue
                        if lowered.startswith("ansible_"):
                            continue
                        candidates.add(token)
    return candidates


def _collect_dynamic_task_include_refs(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[str]:
    """Return templated include/import task references from task files."""
    role_root = Path(role_path).resolve()
    refs: list[str] = []
    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        for ref in _iter_task_include_targets(data):
            if "{{" in ref or "{%" in ref:
                refs.append(ref)
    return refs


def build_variable_insights(
    role_path: str,
    seed_paths: list[str] | None = None,
    include_vars_main: bool = True,
    exclude_paths: list[str] | None = None,
) -> list[dict]:
    """Build variable rows with inferred type/default/source details."""
    defaults_file = Path(role_path) / "defaults" / "main.yml"
    vars_file = Path(role_path) / "vars" / "main.yml"

    defaults_data: dict = {}
    vars_data: dict = {}
    if defaults_file.exists():
        loaded = _load_yaml_file(defaults_file)
        if isinstance(loaded, dict):
            defaults_data = loaded
    if include_vars_main and vars_file.exists():
        loaded = _load_yaml_file(vars_file)
        if isinstance(loaded, dict):
            vars_data = loaded

    seed_values, seed_secrets, seed_sources = load_seed_variables(seed_paths)
    dynamic_include_vars_refs = _collect_dynamic_include_vars_refs(
        role_path,
        exclude_paths=exclude_paths,
    )
    dynamic_task_include_refs = _collect_dynamic_task_include_refs(
        role_path,
        exclude_paths=exclude_paths,
    )
    dynamic_task_include_tokens: set[str] = set()
    for ref in dynamic_task_include_refs:
        dynamic_task_include_tokens.update(
            token
            for token in JINJA_IDENTIFIER_RE.findall(ref)
            if token.lower() not in IGNORED_IDENTIFIERS
            and not token.lower().startswith("ansible_")
        )

    rows: list[dict] = []
    rows_by_name: dict[str, dict] = {}
    for name in sorted(set(defaults_data) | set(vars_data)):
        has_default = name in defaults_data
        has_var = name in vars_data
        value = vars_data[name] if has_var else defaults_data.get(name)
        source = "defaults/main.yml"
        provenance_source_file = "defaults/main.yml"
        provenance_line = _find_variable_line_in_yaml(defaults_file, name)
        provenance_confidence = 0.95
        uncertainty_reason = None
        is_ambiguous = False
        if has_var and has_default:
            source = "defaults/main.yml + vars/main.yml override"
            provenance_source_file = "vars/main.yml"
            provenance_line = _find_variable_line_in_yaml(vars_file, name)
            provenance_confidence = 0.80
            uncertainty_reason = "Overridden by vars/main.yml precedence."
            is_ambiguous = True
        elif has_var:
            source = "vars/main.yml"
            provenance_source_file = "vars/main.yml"
            provenance_line = _find_variable_line_in_yaml(vars_file, name)
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

    # Discover variables from include_vars task references
    known_names: set[str] = {row["name"] for row in rows}
    role_root = Path(role_path).resolve()
    include_var_sources: dict[str, list[dict]] = defaultdict(list)
    for extra_path in _collect_include_vars_files(
        role_path, exclude_paths=exclude_paths
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

    for name in sorted(include_var_sources):
        entries = include_var_sources[name]
        selected = entries[-1]
        if name in rows_by_name:
            row = rows_by_name[name]
            row["is_ambiguous"] = True
            row["uncertainty_reason"] = (
                "May be overridden by include_vars sources: "
                + ", ".join(entry["source"] for entry in entries)
            )
            row["provenance_confidence"] = min(
                float(row.get("provenance_confidence", 1.0)),
                0.70,
            )
            continue
        known_names.add(name)
        ambiguous = len(entries) > 1
        rows.append(
            {
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
        )

    # Discover computed variable names from set_fact tasks
    for name in sorted(
        _collect_set_fact_names(role_path, exclude_paths=exclude_paths) - known_names
    ):
        rows.append(
            {
                "name": name,
                "type": "computed",
                "default": "—",
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

    # Discover documented inputs from README variable/input sections.
    for name in sorted(_collect_readme_input_variables(role_path) - known_names):
        rows.append(
            {
                "name": name,
                "type": "documented",
                "default": "<documented in README>",
                "source": "README.md (documented input)",
                "documented": True,
                "required": False,
                "secret": _looks_secret_name(name),
                "provenance_source_file": "README.md",
                "provenance_line": None,
                "provenance_confidence": 0.50,
                "uncertainty_reason": "Documented in README; static role definition not found.",
                "is_unresolved": True,
                "is_ambiguous": False,
            }
        )

    known_names: set[str] = {row["name"] for row in rows}
    referenced_names = _collect_referenced_variable_names(
        role_path,
        exclude_paths=exclude_paths,
    )

    for name in sorted(referenced_names - known_names):
        seeded = name in seed_values
        value = seed_values.get(name, "<required>")
        rows.append(
            {
                "name": name,
                "type": _infer_variable_type(value) if seeded else "required",
                "default": _format_inline_yaml(value) if seeded else "<required>",
                "source": (
                    f"seed: {seed_sources.get(name, 'external vars')}"
                    if seeded
                    else "inferred usage"
                ),
                "documented": False,
                "required": not seeded,
                "secret": (name in seed_secrets or _is_sensitive_variable(name, value)),
                "provenance_source_file": (
                    seed_sources.get(name, "external vars") if seeded else None
                ),
                "provenance_line": None,
                "provenance_confidence": 0.75 if seeded else 0.40,
                "uncertainty_reason": (
                    "Provided by external seed vars."
                    if seeded
                    else (
                        "Referenced in role but no static definition found. Dynamic include_vars paths detected."
                        if dynamic_include_vars_refs
                        else "Referenced in role but no static definition found."
                    )
                    + (
                        " Dynamic include_tasks/import_tasks paths detected."
                        if (not seeded and name in dynamic_task_include_tokens)
                        else ""
                    )
                ),
                "is_unresolved": not seeded,
                "is_ambiguous": False,
            }
        )

    # redact secret defaults before returning rows
    for row in rows:
        if row.get("secret"):
            row["default"] = "<secret>"

    return rows


def _resolve_section_selector(selector: str) -> str | None:
    """Resolve a section selector to a canonical section id.

    Selectors can be:
    - canonical ids (e.g. ``galaxy_info``)
    - heading text aliases (e.g. ``Role purpose and capabilities``)
    """
    value = selector.strip()
    if not value:
        return None
    if value in ALL_SECTION_IDS:
        return value
    normalized = normalize_style_heading(value)
    if normalized in ALL_SECTION_IDS:
        return normalized
    return STYLE_SECTION_ALIASES.get(normalized)


def load_readme_section_visibility(
    role_path: str,
    config_path: str | None = None,
) -> set[str] | None:
    """Load optional README section visibility rules from YAML config.

    Configuration format (either explicit ``config_path`` or
    ``<role_path>/.ansible_role_doc.yml``):

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
    config = load_readme_section_config(role_path, config_path=config_path)
    if config is None:
        return None

    return config["enabled_sections"]


def load_readme_section_config(
    role_path: str,
    config_path: str | None = None,
    adopt_heading_mode: str | None = None,
) -> dict | None:
    """Load README section visibility and section rendering options."""
    cfg_file = (
        Path(config_path) if config_path else Path(role_path) / SECTION_CONFIG_FILENAME
    )
    if not cfg_file.is_file():
        return None

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None

    readme_cfg = raw.get("readme", raw)
    if not isinstance(readme_cfg, dict):
        return None

    include_raw = readme_cfg.get("include_sections")
    exclude_raw = readme_cfg.get("exclude_sections")
    content_modes_raw = readme_cfg.get("section_content_modes")
    config_adopt_heading_mode = readme_cfg.get("adopt_heading_mode")
    if include_raw is None and exclude_raw is None and content_modes_raw is None:
        return None

    if adopt_heading_mode is None and isinstance(config_adopt_heading_mode, str):
        adopt_heading_mode = config_adopt_heading_mode.strip().lower()
    if adopt_heading_mode is None:
        adopt_heading_mode = "canonical"
    if adopt_heading_mode not in {"canonical", "style", "popular"}:
        adopt_heading_mode = "canonical"

    include_items = include_raw if isinstance(include_raw, list) else None
    exclude_items = exclude_raw if isinstance(exclude_raw, list) else []
    content_modes_items = (
        content_modes_raw if isinstance(content_modes_raw, dict) else {}
    )
    title_overrides: dict[str, str] = {}
    display_titles = _load_section_display_titles()
    section_content_modes: dict[str, str] = {}
    include_selector_map: dict[str, str] = {}

    if include_items is None:
        enabled: set[str] = set(ALL_SECTION_IDS)
    else:
        enabled = set()
        for item in include_items:
            if isinstance(item, str):
                resolved = _resolve_section_selector(item)
                if resolved:
                    enabled.add(resolved)
                    normalized_item = normalize_style_heading(item)
                    if normalized_item:
                        include_selector_map[normalized_item] = resolved
                    if adopt_heading_mode == "style":
                        title_overrides[resolved] = item.strip()

    for item in exclude_items:
        if isinstance(item, str):
            resolved = _resolve_section_selector(item)
            if resolved:
                enabled.discard(resolved)

    if adopt_heading_mode == "popular":
        for section_id in enabled:
            display_title = display_titles.get(section_id)
            if display_title:
                title_overrides[section_id] = display_title

    for selector, mode in content_modes_items.items():
        if not isinstance(selector, str) or not isinstance(mode, str):
            continue
        normalized_selector = normalize_style_heading(selector)
        resolved = include_selector_map.get(normalized_selector)
        if not resolved:
            resolved = _resolve_section_selector(selector)
        if not resolved:
            continue
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"generate", "replace", "merge"}:
            continue
        section_content_modes[resolved] = normalized_mode

    return {
        "enabled_sections": enabled,
        "section_title_overrides": title_overrides,
        "adopt_heading_mode": adopt_heading_mode,
        "section_content_modes": section_content_modes,
    }


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


def _describe_variable(name: str, source: str) -> str:
    """Generate a lightweight variable description when no source prose exists."""
    lowered = name.lower()
    if lowered.endswith("_enabled"):
        return "Enable or disable related behavior."
    if "port" in lowered:
        return "Set the port value used by the role."
    if "package" in lowered:
        return "Configure the package name or package list used by the role."
    if "service" in lowered:
        return "Control the related service name or service state."
    if "path" in lowered or "file" in lowered:
        return "Override the file or path location used by the role."
    if "user" in lowered or "group" in lowered:
        return "Set the user or group-related value used by the role."
    return f"Configured from `{source}` and can be overridden for environment-specific behavior."


def _render_role_variables_for_style(variables: dict, metadata: dict) -> str:
    """Render role variables following the style guide's preferred format."""
    if not variables:
        return "No variables found."

    style_guide = metadata.get("style_guide") or {}
    variable_style = style_guide.get("variable_style", "simple_list")
    variable_intro = style_guide.get("variable_intro")
    variable_insights = metadata.get("variable_insights") or []

    if variable_style == "table":
        lines: list[str] = []
        if variable_intro:
            lines.extend([variable_intro, ""])
        lines.extend(["| Name | Default | Description |", "| --- | --- | --- |"])
        source_by_name = {
            row.get("name"): row for row in variable_insights if row.get("name")
        }
        for name, value in variables.items():
            row = source_by_name.get(name) or {}
            default = str(row.get("default") or _format_inline_yaml(value)).replace(
                "`", "'"
            )
            description = _describe_variable(
                name,
                str(row.get("source") or "defaults/main.yml"),
            )
            lines.append(f"| `{name}` | `{default}` | {description} |")
        return "\n".join(lines)

    if variable_style == "nested_bullets":
        lines: list[str] = []
        if variable_intro:
            lines.extend([variable_intro, ""])
        for row in variable_insights:
            default = _format_inline_yaml(row["default"]).replace("`", "'")
            lines.append(f"* `{row['name']}`")
            lines.append(f"  * Default: `{default}`")
            lines.append(
                f"  * Description: {_describe_variable(row['name'], row['source'])}"
            )
        return "\n".join(lines)

    if variable_style == "yaml_block":
        intro = (
            variable_intro
            or "Available variables are listed below, along with default values (see `defaults/main.yml`):"
        )
        yaml_block = yaml.safe_dump(
            variables, sort_keys=False, default_flow_style=False
        ).strip()
        return f"{intro}\n\n```yaml\n{yaml_block}\n```"

    lines = [variable_intro or "The following variables are available:"]
    for name, value in variables.items():
        rendered = _format_inline_yaml(value).replace("`", "'")
        lines.append(f"- `{name}`: `{rendered}`")
    return "\n".join(lines)


def _render_role_notes_section(role_notes: dict | None) -> str:
    """Render comment-driven role notes in a readable markdown block."""
    notes = role_notes or {}
    warnings = notes.get("warnings") or []
    deprecations = notes.get("deprecations") or []
    general = notes.get("notes") or []
    additionals = notes.get("additionals") or []
    if not warnings and not deprecations and not general and not additionals:
        return "No role notes were found in comment annotations."

    lines: list[str] = []
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings)
    if deprecations:
        if lines:
            lines.append("")
        lines.append("Deprecations:")
        lines.extend(f"- {item}" for item in deprecations)
    if general:
        if lines:
            lines.append("")
        lines.append("Notes:")
        lines.extend(f"- {item}" for item in general)
    if additionals:
        if lines:
            lines.append("")
        lines.append("Additionals:")
        lines.extend(f"- {item}" for item in additionals)
    return "\n".join(lines)


def _render_variable_uncertainty_notes(rows: list[dict]) -> str:
    """Render unresolved/ambiguous variable provenance notes."""
    unresolved = [row for row in rows if row.get("is_unresolved")]
    ambiguous = [row for row in rows if row.get("is_ambiguous")]
    if not unresolved and not ambiguous:
        return ""

    lines = ["Variable provenance and confidence notes:", ""]
    if unresolved:
        lines.append("Unresolved variables:")
        for row in unresolved:
            reason = row.get("uncertainty_reason") or "Unknown source."
            lines.append(f"- `{row['name']}`: {reason}")
    if ambiguous:
        if unresolved:
            lines.append("")
        lines.append("Ambiguous variables:")
        for row in ambiguous:
            reason = row.get("uncertainty_reason") or "Multiple possible sources."
            lines.append(f"- `{row['name']}`: {reason}")
    return "\n".join(lines)


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

    if section_id == "galaxy_info":
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

    if section_id == "requirements":
        requirement_lines = normalize_requirements(requirements)
        if not requirement_lines:
            return "No additional requirements."
        return "\n".join(f"- {line}" for line in requirement_lines)

    if section_id == "installation":
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

    if section_id == "license":
        if galaxy and galaxy.get("license"):
            return str(galaxy.get("license"))
        return "N/A"

    if section_id == "author_information":
        if galaxy and galaxy.get("author"):
            return str(galaxy.get("author"))
        return "N/A"

    if section_id == "license_author":
        license_value = str(galaxy.get("license", "N/A")) if galaxy else "N/A"
        author_value = str(galaxy.get("author", "N/A")) if galaxy else "N/A"
        return f"License: {license_value}\n\nAuthor: {author_value}"

    if section_id == "sponsors":
        return "No sponsorship metadata detected for this role."

    if section_id == "purpose":
        insights = metadata.get("doc_insights") or {}
        lines = [insights.get("purpose_summary", "No inferred role summary available.")]
        capabilities = insights.get("capabilities", [])
        if capabilities:
            lines.extend(["", "Capabilities:"])
            lines.extend(f"- {capability}" for capability in capabilities)
        return "\n".join(lines)

    if section_id == "role_notes":
        return _render_role_notes_section(metadata.get("role_notes"))

    if section_id == "variable_summary":
        rows = metadata.get("variable_insights") or []
        if not rows:
            return "No variable insights available."
        lines = ["| Name | Type | Default | Source |", "| --- | --- | --- | --- |"]
        for row in rows:
            default = str(row["default"]).replace("`", "'")
            source = row["source"]
            if row.get("secret"):
                source = f"{source} (secret)"
            lines.append(
                f"| `{row['name']}` | {row['type']} | `{default}` | {source} |"
            )
        uncertainty_notes = _render_variable_uncertainty_notes(rows)
        if uncertainty_notes:
            lines.extend(["", uncertainty_notes])
        return "\n".join(lines)

    if section_id == "variable_guidance":
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
        lines.append(
            "Use these as initial overrides for environment-specific behavior."
        )
        return "\n".join(lines)

    if section_id == "task_summary":
        summary = (metadata.get("doc_insights") or {}).get("task_summary", {})
        if not summary:
            return "No task summary available."
        return "\n".join(
            [
                f"- **Task files scanned**: {summary.get('task_files_scanned', 0)}",
                f"- **Tasks scanned**: {summary.get('tasks_scanned', 0)}",
                f"- **Recursive includes**: {summary.get('recursive_task_includes', 0)}",
                f"- **Unique modules**: {summary.get('module_count', 0)}",
                f"- **Handlers referenced**: {summary.get('handler_count', 0)}",
            ]
        )

    if section_id == "example_usage":
        example = (metadata.get("doc_insights") or {}).get("example_playbook")
        if not example:
            return "No inferred example available."
        return f"```yaml\n{example}\n```"

    if section_id == "local_testing":
        role_tests = metadata.get("tests") or []
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
            return (
                "Run a quick local validation using bundled role tests:\n\n"
                "```bash\n"
                f"ansible-playbook -i {inventory} {playbook}\n"
                "```"
            )
        return "Run `tox` or `pytest -q` locally to validate scanner behavior and generated output."

    if section_id == "handlers":
        features = metadata.get("features") or {}
        handler_names = parse_comma_values(
            str(features.get("handlers_notified", "none"))
        )
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
        return "\n".join(lines)

    if section_id == "template_overrides":
        template_files = metadata.get("templates") or []
        variable_rows = metadata.get("variable_insights") or []
        template_vars = [
            row["name"]
            for row in variable_rows
            if isinstance(row.get("name"), str) and "template" in row["name"].lower()
        ]
        lines = [
            "Override template-related variables or point them at playbook-local templates when the built-in layout is not sufficient."
        ]
        if template_vars:
            lines.append("")
            lines.append("Likely template override variables:")
            lines.extend(f"- `{name}`" for name in template_vars[:8])
        if template_files:
            lines.append("")
            lines.append("Templates detected in this role:")
            lines.extend(f"- `{path}`" for path in template_files)
        return "\n".join(lines)

    if section_id == "basic_authorization":
        return (
            "Use custom vhost or directory directives to add HTTP Basic Authentication where needed.\n\n"
            "- Provide credential files such as `.htpasswd` from your playbook or a companion role.\n"
            "- Prefer explicit configuration blocks or custom templates over editing generated files in place.\n"
            "- Keep authentication settings alongside the related virtual host configuration so the access policy remains reviewable."
        )

    if section_id == "faq_pitfalls":
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

    if section_id == "contributing":
        return (
            "Contributions are welcome.\n\n"
            "- Run `pytest -q` before submitting changes.\n"
            "- Run `tox` for full local validation and review artifact generation.\n"
            "- Update docs/templates when scanner behavior changes."
        )

    if section_id == "role_variables":
        return _render_role_variables_for_style(variables, metadata)

    if section_id == "role_contents":
        lines = ["The scanner collected these role subdirectories (counts):", ""]
        for key, items in metadata.items():
            if key in (
                "meta",
                "features",
                "comparison",
                "variable_insights",
                "doc_insights",
                "style_guide",
                "role_notes",
                "scanner_counters",
            ):
                continue
            if isinstance(items, list):
                lines.append(f"- **{key}**: {len(items)} files")
        return "\n".join(lines)

    if section_id == "features":
        features = metadata.get("features") or {}
        if not features:
            return "No role features detected."
        return "\n".join(f"- **{key}**: {value}" for key, value in features.items())

    if section_id == "comparison":
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

    if section_id == "default_filters":
        if not default_filters:
            return "No undocumented variables using `default()` were detected."
        lines = [
            "The scanner found undocumented variables using `default()` in role files:",
            "",
        ]
        for occ in default_filters:
            match = occ["match"].replace("`", "'")
            args = occ["args"].replace("`", "'")
            lines.append(f"- {occ['file']}:{occ['line_no']} — `{match}`")
            lines.append(f"  args: `{args}`")
        return "\n".join(lines)

    return ""


def _render_readme_with_style_guide(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Render markdown following the structure of a guide README."""

    def _generated_merge_markers(section_id: str) -> tuple[str, str]:
        start = f"<!-- ansible-role-doc:generated:start:{section_id} -->"
        end = f"<!-- ansible-role-doc:generated:end:{section_id} -->"
        return start, end

    def _strip_prior_generated_merge_block(section: dict, guide_body: str) -> str:
        """Remove previously generated merge payload for a section, if present."""
        section_id = str(section.get("id") or "")
        cleaned = guide_body
        start_marker, end_marker = _generated_merge_markers(section_id)
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
        configured = str(modes.get(section_id) or "").strip().lower()
        if configured in {"generate", "replace", "merge"}:
            return configured
        if section_id == "requirements":
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
        start_marker, end_marker = _generated_merge_markers(section_id)
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

    style_guide = metadata.get("style_guide") or {}
    ordered_sections = list(style_guide.get("sections") or [])
    enabled_sections = set(metadata.get("enabled_sections") or [])
    section_title_overrides = metadata.get("section_title_overrides") or {}
    section_content_modes = metadata.get("section_content_modes") or {}
    keep_unknown_style_sections = bool(metadata.get("keep_unknown_style_sections"))

    if not ordered_sections:
        ordered_sections = [
            {"id": section_id, "title": title}
            for section_id, title in DEFAULT_SECTION_SPECS
        ]

    ordered_sections = [dict(section) for section in ordered_sections]
    for section in ordered_sections:
        override_title = section_title_overrides.get(section.get("id"))
        if override_title:
            section["title"] = override_title

    if not keep_unknown_style_sections:
        ordered_sections = [
            section for section in ordered_sections if section.get("id") != "unknown"
        ]

    if enabled_sections:
        ordered_sections = [
            section
            for section in ordered_sections
            if section.get("id") in enabled_sections
        ]

    if metadata.get("concise_readme"):
        ordered_sections = [
            section
            for section in ordered_sections
            if section.get("id") not in SCANNER_STATS_SECTION_IDS
        ]
        section_ids = [section.get("id") for section in ordered_sections]
        if "variable_summary" in section_ids and "role_variables" in section_ids:
            ordered_sections = [
                section
                for section in ordered_sections
                if section.get("id") != "role_variables"
            ]

    style_guide_skeleton = bool(metadata.get("style_guide_skeleton"))

    rendered_title = role_name
    if style_guide.get("title_text"):
        rendered_title = role_name

    parts = [
        format_heading(rendered_title, 1, style_guide.get("title_style", "setext")),
        "",
        description,
        "",
    ]
    for section in ordered_sections:
        heading_level = int(
            section.get("level") or style_guide.get("section_level") or 2
        )
        parts.append(
            format_heading(
                section["title"],
                heading_level,
                style_guide.get("section_style", "setext"),
            )
        )
        parts.append("")

        if style_guide_skeleton:
            continue

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
        if section["id"] == "unknown":
            unknown_guide_body = str(section.get("body") or "").strip()
            if unknown_guide_body:
                body = unknown_guide_body
            else:
                body = "Style section retained from guide; scanner does not map this section yet."
        if not body:
            continue
        parts.append(body)
        parts.append("")

    scanner_report_relpath = metadata.get("scanner_report_relpath")
    if (
        not style_guide_skeleton
        and scanner_report_relpath
        and metadata.get("include_scanner_report_link", True)
        and (not enabled_sections or "scanner_report" in enabled_sections)
    ):
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
    counters = metadata.get("scanner_counters") or _extract_scanner_counters(
        metadata.get("variable_insights") or [],
        default_filters,
    )
    lines = [
        f"{role_name} scanner report",
        "=" * (len(role_name) + len(" scanner report")),
        "",
        description,
        "",
        "Summary",
        "-------",
        "",
        f"- **Total variables**: {counters['total_variables']} ({counters['documented_variables']} documented, {counters['undocumented_variables']} undocumented)",
        f"- **Unresolved**: {counters['unresolved_variables']} | **Ambiguous**: {counters['ambiguous_variables']} | **Required**: {counters['required_variables']} | **Secrets**: {counters['secret_variables']}",
        f"- **Confidence buckets**: high={counters['high_confidence_variables']}, medium={counters['medium_confidence_variables']}, low={counters['low_confidence_variables']}",
        f"- **Default filter findings**: {counters['undocumented_default_filters']} undocumented out of {counters['total_default_filters']} discovered",
    ]

    issue_categories = counters.get("provenance_issue_categories") or {}
    non_zero_categories = [
        (name, value) for name, value in issue_categories.items() if value
    ]
    if non_zero_categories:
        lines.append("- **Provenance issue categories**:")
        for name, value in non_zero_categories:
            lines.append(f"  - `{name}`: {value}")
    lines.append("")

    unresolved_rows = [
        row
        for row in (metadata.get("variable_insights") or [])
        if row.get("is_unresolved")
    ]
    ambiguous_rows = [
        row
        for row in (metadata.get("variable_insights") or [])
        if row.get("is_ambiguous")
    ]
    if unresolved_rows or ambiguous_rows:
        lines.extend(["Variable provenance issues", "-------------------------", ""])
        if unresolved_rows:
            lines.append("Unresolved variables:")
            for row in unresolved_rows:
                reason = row.get("uncertainty_reason") or "Unknown source."
                lines.append(f"- `{row['name']}`: {reason}")
            lines.append("")
        if ambiguous_rows:
            lines.append("Ambiguous variables:")
            for row in ambiguous_rows:
                reason = row.get("uncertainty_reason") or "Multiple possible sources."
                lines.append(f"- `{row['name']}`: {reason}")
            lines.append("")

    sections = [
        ("task_summary", "Task/module usage summary"),
        ("role_contents", "Role contents summary"),
        ("features", "Auto-detected role features"),
        ("comparison", "Comparison against local baseline role"),
        ("default_filters", "Detected usages of the default() filter"),
    ]
    for section_id, title in sections:
        body = _render_guide_section_body(
            section_id,
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        ).strip()
        if not body:
            continue
        lines.extend([title, "-" * len(title), "", body, ""])
    return "\n".join(lines).strip() + "\n"


def _extract_scanner_counters(
    variable_insights: list[dict],
    default_filters: list[dict],
) -> dict[str, int | dict[str, int]]:
    """Summarize scanner findings by certainty and variable category."""
    counters = {
        "total_variables": len(variable_insights),
        "documented_variables": 0,
        "undocumented_variables": 0,
        "unresolved_variables": 0,
        "ambiguous_variables": 0,
        "secret_variables": 0,
        "required_variables": 0,
        "high_confidence_variables": 0,
        "medium_confidence_variables": 0,
        "low_confidence_variables": 0,
        "total_default_filters": len(default_filters),
        "undocumented_default_filters": len(default_filters),
        "provenance_issue_categories": {
            "unresolved_readme_documented_only": 0,
            "unresolved_dynamic_include_vars": 0,
            "unresolved_no_static_definition": 0,
            "unresolved_other": 0,
            "ambiguous_defaults_vars_override": 0,
            "ambiguous_include_vars_sources": 0,
            "ambiguous_set_fact_runtime": 0,
            "ambiguous_other": 0,
        },
    }

    for row in variable_insights:
        if row.get("documented"):
            counters["documented_variables"] += 1
        else:
            counters["undocumented_variables"] += 1
        if row.get("is_unresolved"):
            counters["unresolved_variables"] += 1
        if row.get("is_ambiguous"):
            counters["ambiguous_variables"] += 1
        if row.get("secret"):
            counters["secret_variables"] += 1
        if row.get("required"):
            counters["required_variables"] += 1

        issue_category = _classify_provenance_issue(row)
        if issue_category:
            counters["provenance_issue_categories"][issue_category] += 1

        confidence = float(row.get("provenance_confidence") or 0.0)
        if confidence >= 0.90:
            counters["high_confidence_variables"] += 1
        elif confidence >= 0.70:
            counters["medium_confidence_variables"] += 1
        else:
            counters["low_confidence_variables"] += 1

    return counters


def _classify_provenance_issue(row: dict) -> str | None:
    """Return a stable issue category label for unresolved/ambiguous rows."""
    reason = str(row.get("uncertainty_reason") or "").lower()
    source = str(row.get("source") or "").lower()

    if row.get("is_unresolved"):
        if "documented in readme" in reason or "readme" in source:
            return "unresolved_readme_documented_only"
        if "dynamic include_vars" in reason:
            return "unresolved_dynamic_include_vars"
        if "no static definition" in reason:
            return "unresolved_no_static_definition"
        return "unresolved_other"

    if row.get("is_ambiguous"):
        if "overridden by vars/main.yml precedence" in reason:
            return "ambiguous_defaults_vars_override"
        if "include_vars" in reason:
            return "ambiguous_include_vars_sources"
        if "set_fact" in reason or "runtime" in reason:
            return "ambiguous_set_fact_runtime"
        return "ambiguous_other"

    return None


def _detect_task_module(task: dict) -> str | None:
    """Detect the task module key from an Ansible task mapping."""
    for key in task:
        if key in TASK_META_KEYS or key in TASK_INCLUDE_KEYS or key in TASK_BLOCK_KEYS:
            continue
        if key.startswith("with_"):
            continue
        return key
    return None


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
    dry_run: bool = False,
) -> str:
    _refresh_policy(policy_config_path)

    rp = Path(role_path)
    if not rp.is_dir():
        raise FileNotFoundError(f"role path not found: {role_path}")
    meta = load_meta(role_path)
    galaxy = meta.get("galaxy_info", {}) if isinstance(meta, dict) else {}
    role_name = galaxy.get("role_name", rp.name)
    if role_name_override and (not galaxy.get("role_name") or role_name == "repo"):
        role_name = role_name_override
    description = galaxy.get("description", "")
    variables = load_variables(
        role_path,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_path_patterns,
    )
    requirements = load_requirements(role_path)
    found = scan_for_default_filters(role_path, exclude_paths=exclude_path_patterns)
    metadata = collect_role_contents(role_path, exclude_paths=exclude_path_patterns)
    collection_compliance_notes = _build_collection_compliance_notes(
        features=metadata.get("features") or {},
        meta=meta,
        requirements=requirements,
    )
    metadata["collection_compliance_notes"] = collection_compliance_notes
    requirements_display = normalize_requirements(requirements)
    meta_dependencies_display = _normalize_meta_role_dependencies(meta)
    for dep in meta_dependencies_display:
        if dep not in requirements_display:
            requirements_display.append(dep)
    requirements_display.extend(
        f"[Collection check] {note}" for note in collection_compliance_notes
    )
    metadata["keep_unknown_style_sections"] = keep_unknown_style_sections
    readme_section_config = load_readme_section_config(
        role_path,
        config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
    )
    if readme_section_config is not None:
        metadata["enabled_sections"] = sorted(readme_section_config["enabled_sections"])
        if readme_section_config["section_title_overrides"]:
            metadata["section_title_overrides"] = dict(
                readme_section_config["section_title_overrides"]
            )
        if readme_section_config["section_content_modes"]:
            metadata["section_content_modes"] = dict(
                readme_section_config["section_content_modes"]
            )
    variable_insights = build_variable_insights(
        role_path,
        seed_paths=vars_seed_paths,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_path_patterns,
    )
    metadata["variable_insights"] = variable_insights
    metadata["role_notes"] = _extract_role_notes_from_comments(
        role_path,
        exclude_paths=exclude_path_patterns,
    )
    inventory_names = {row["name"]: row for row in variable_insights}
    undocumented_default_filters: list[dict] = []
    for occurrence in found:
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

    metadata["scanner_counters"] = _extract_scanner_counters(
        variable_insights,
        undocumented_default_filters,
    )

    # Replace secret values in simple role-variable rendering.
    secret_names = {
        row["name"]
        for row in variable_insights
        if row.get("secret") and row["name"] in variables
    }
    display_variables = {
        key: ("<secret>" if key in secret_names else value)
        for key, value in variables.items()
    }
    metadata["doc_insights"] = build_doc_insights(
        role_name=role_name,
        description=description,
        metadata=metadata,
        variables=variables,
        variable_insights=variable_insights,
    )
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

    out_path = resolve_output_path(output, output_format)

    scanner_report_path: Path | None = None
    if concise_readme:
        if scanner_report_output:
            scanner_report_path = Path(scanner_report_output)
        else:
            scanner_report_path = out_path.with_suffix(".scan-report.md")
        metadata["concise_readme"] = True
        metadata["include_scanner_report_link"] = include_scanner_report_link
        if not dry_run:
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
