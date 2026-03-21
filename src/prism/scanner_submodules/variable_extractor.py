"""Variable extraction and sensitivity helpers.

These functions are extracted from scanner.py to improve cohesion.
They depend only on _jinja_analyzer, _task_parser, pattern_config,
and stdlib.

Policy-derived module-level constants (_SECRET_NAME_TOKENS, etc.) mirror
scanner.py's globals and are refreshed by scanner._refresh_policy() when
the policy is reloaded.

Exported names consumed by scanner.py:
  Constants: DEFAULT_TARGET_RE, JINJA_VAR_RE, JINJA_IDENTIFIER_RE,
             VAULT_KEY_RE, IGNORED_IDENTIFIERS,
             _SECRET_NAME_TOKENS, _VAULT_MARKERS,
             _CREDENTIAL_PREFIXES, _URL_PREFIXES
  Functions: _extract_default_target_var, _collect_include_vars_files,
             _collect_set_fact_names, _find_variable_line_in_yaml,
             _collect_dynamic_include_vars_refs,
             _collect_dynamic_task_include_refs,
             _collect_referenced_variable_names,
             _looks_secret_name, _resembles_password_like,
             _is_sensitive_variable, _looks_secret_value,
             _infer_variable_type,
             _read_seed_yaml, _resolve_seed_var_files, load_seed_variables
"""

from __future__ import annotations

import re
import yaml
from pathlib import Path

from .._jinja_analyzer import (
    _collect_jinja_local_bindings_from_text,
    _collect_undeclared_jinja_variables,
)
from .task_parser import (
    INCLUDE_VARS_KEYS,
    SET_FACT_KEYS,
    _collect_task_files,
    _is_path_excluded,
    _iter_task_mappings,
    _load_yaml_file,
)
from ..pattern_config import load_pattern_config

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

DEFAULT_TARGET_RE = re.compile(r"\b(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\|\s*default\b")
JINJA_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
VAULT_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*!vault\b", re.MULTILINE)
# Strip quoted string literals before identifier scanning of when: expressions
_QUOTED_STRING_RE = re.compile(r"\"[^\"]*\"|'[^']*'")

# ---------------------------------------------------------------------------
# Policy-derived constants (refreshed by scanner._refresh_policy)
# ---------------------------------------------------------------------------

_POLICY = load_pattern_config()
_SENSITIVITY = _POLICY["sensitivity"]
_SECRET_NAME_TOKENS: tuple[str, ...] = tuple(_SENSITIVITY["name_tokens"])
_VAULT_MARKERS: tuple[str, ...] = tuple(_SENSITIVITY["vault_markers"])
_CREDENTIAL_PREFIXES: tuple[str, ...] = tuple(_SENSITIVITY["credential_prefixes"])
_URL_PREFIXES: tuple[str, ...] = tuple(_SENSITIVITY["url_prefixes"])
IGNORED_IDENTIFIERS: set[str] = _POLICY["ignored_identifiers"]

# ---------------------------------------------------------------------------
# Default filter target detection
# ---------------------------------------------------------------------------


def _extract_default_target_var(occurrence: dict) -> str | None:
    """Extract the variable name used with ``| default(...)`` when available."""
    line = str(occurrence.get("line") or occurrence.get("match") or "")
    match = DEFAULT_TARGET_RE.search(line)
    if not match:
        return None
    return match.group("var")


# ---------------------------------------------------------------------------
# Variable collection from task files
# ---------------------------------------------------------------------------


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


def _collect_dynamic_task_include_refs(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[str]:
    """Return templated include/import task references from task files."""
    from .task_parser import _iter_task_include_targets

    role_root = Path(role_path).resolve()
    refs: list[str] = []
    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        for ref in _iter_task_include_targets(data):
            if "{{" in ref or "{%" in ref:
                refs.append(ref)
    return refs


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
            except (UnicodeDecodeError, OSError):
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
                    expression = _QUOTED_STRING_RE.sub("", line.split("when:", 1)[1])
                    for token in JINJA_IDENTIFIER_RE.findall(expression):
                        lowered = token.lower()
                        if lowered in IGNORED_IDENTIFIERS:
                            continue
                        if lowered.startswith("ansible_"):
                            continue
                        candidates.add(token)
    return candidates


# ---------------------------------------------------------------------------
# Sensitivity / secret detection helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Type inference
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Seed variable loading
# ---------------------------------------------------------------------------


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
