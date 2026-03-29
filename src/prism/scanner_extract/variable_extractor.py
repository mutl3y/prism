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
                         _collect_set_fact_names, _collect_register_names,
                         _find_variable_line_in_yaml,
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
from typing import Any, Iterable

from .._jinja_analyzer import (
    _collect_jinja_local_bindings_from_text,
    _collect_undeclared_jinja_variables,
)
from . import (
    TASK_BLOCK_KEYS,
    TASK_INCLUDE_KEYS,
    TASK_META_KEYS,
    ROLE_INCLUDE_KEYS,
    INCLUDE_VARS_KEYS,
    SET_FACT_KEYS,
    _collect_task_files,
    _is_path_excluded,
    _iter_task_mappings,
    _load_yaml_file,
)
from ..scanner_config.patterns import load_pattern_config

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

DEFAULT_TARGET_RE = re.compile(r"\b(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\|\s*default\b")
JINJA_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
VAULT_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*!vault\b", re.MULTILINE)
# Strip quoted string literals before identifier scanning of when: expressions
_QUOTED_STRING_RE = re.compile(r"\"[^\"]*\"|'[^']*'")
_WHEN_FILTER_OR_TEST_CONTEXT_RE = re.compile(r"(?:\|\s*|is\s+|is\s+not\s+)$")
_VALID_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_WHEN_OPERATOR_KEYWORDS: frozenset[str] = frozenset(
    {
        # Logical operators
        "and",
        "or",
        "not",
        # Comparison/membership operators and textual aliases
        "is",
        "in",
        "eq",
        "ne",
        "lt",
        "gt",
        "le",
        "ge",
    }
)

# ---------------------------------------------------------------------------
# Policy-derived constants (refreshed by scanner._refresh_policy)
# ---------------------------------------------------------------------------

_POLICY = load_pattern_config()
_SENSITIVITY = _POLICY["sensitivity"]
_SECRET_NAME_TOKENS: tuple[str, ...] = tuple(_SENSITIVITY["name_tokens"])
_VAULT_MARKERS: tuple[str, ...] = tuple(_SENSITIVITY["vault_markers"])
_CREDENTIAL_PREFIXES: tuple[str, ...] = tuple(_SENSITIVITY["credential_prefixes"])
_URL_PREFIXES: tuple[str, ...] = tuple(_SENSITIVITY["url_prefixes"])


def _coerce_identifier(value: object) -> str | None:
    """Return a lower-cased identifier token when ``value`` looks like one."""
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token:
        return None
    if "." in token:
        token = token.rsplit(".", 1)[-1]
    lowered = token.lower()
    if _VALID_IDENTIFIER_RE.match(lowered):
        return lowered
    return None


def _iter_strings(value: Any) -> Iterable[str]:
    """Yield string items recursively from nested containers."""
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str):
                yield key
            yield from _iter_strings(nested)
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _iter_strings(item)


def _load_ansible_core_builtin_variables() -> set[str]:
    """Best-effort import of ansible-core builtin/reserved variable names."""
    names: set[str] = set()

    try:
        from ansible.vars.reserved import get_reserved_names  # type: ignore

        for raw in get_reserved_names() or []:
            token = _coerce_identifier(raw)
            if token:
                names.add(token)
    except Exception:
        pass

    try:
        from ansible import constants as ansible_constants  # type: ignore

        for attr_name in (
            "MAGIC_VARIABLE_MAPPING",
            "COMMON_CONNECTION_VARS",
            "INTERNAL_RESULT_KEYS",
            "RESTRICTED_RESULT_KEYS",
        ):
            raw_value = getattr(ansible_constants, attr_name, None)
            for raw in _iter_strings(raw_value):
                token = _coerce_identifier(raw)
                if token:
                    names.add(token)
    except Exception:
        pass

    return names


def _build_task_keyword_ignored_identifiers() -> set[str]:
    """Return keyword-like task parser tokens that must never be treated as vars."""
    names: set[str] = set()
    for raw in (
        *TASK_META_KEYS,
        *TASK_BLOCK_KEYS,
        *TASK_INCLUDE_KEYS,
        *ROLE_INCLUDE_KEYS,
        *INCLUDE_VARS_KEYS,
        *SET_FACT_KEYS,
    ):
        token = _coerce_identifier(raw)
        if token:
            names.add(token)
    return names


def _build_effective_ignored_identifiers(policy: dict[str, Any]) -> set[str]:
    """Merge policy ignores with task keywords and ansible builtin variables."""
    ignored: set[str] = {
        token.lower()
        for token in policy.get("ignored_identifiers", set())
        if isinstance(token, str)
    }
    ignored.update(_build_task_keyword_ignored_identifiers())
    ignored.update(
        {
            token.lower()
            for token in policy.get("ansible_builtin_variables", set())
            if isinstance(token, str)
        }
    )
    ignored.update(_load_ansible_core_builtin_variables())
    return ignored


IGNORED_IDENTIFIERS: set[str] = _build_effective_ignored_identifiers(_POLICY)


def _refresh_policy_derived_state(policy: dict[str, Any]) -> None:
    """Refresh module-level policy state after scanner policy reloads."""
    global _SENSITIVITY
    global _SECRET_NAME_TOKENS
    global _VAULT_MARKERS
    global _CREDENTIAL_PREFIXES
    global _URL_PREFIXES
    global IGNORED_IDENTIFIERS

    _SENSITIVITY = policy["sensitivity"]
    _SECRET_NAME_TOKENS = tuple(_SENSITIVITY["name_tokens"])
    _VAULT_MARKERS = tuple(_SENSITIVITY["vault_markers"])
    _CREDENTIAL_PREFIXES = tuple(_SENSITIVITY["credential_prefixes"])
    _URL_PREFIXES = tuple(_SENSITIVITY["url_prefixes"])
    IGNORED_IDENTIFIERS = _build_effective_ignored_identifiers(policy)


_REGISTERED_RESULT_ATTRS: frozenset[str] = frozenset(
    {
        "stdout",
        "stderr",
        "rc",
        "stdout_lines",
        "stderr_lines",
        "results",
        "changed",
        "failed",
        "skipped",
        "msg",
    }
)

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


def _collect_register_names(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> set[str]:
    """Return variable names assigned by task-level ``register`` statements."""
    role_root = Path(role_path).resolve()
    task_files = _collect_task_files(role_root, exclude_paths=exclude_paths)
    names: set[str] = set()
    for task_file in task_files:
        data = _load_yaml_file(task_file)
        for task in _iter_task_mappings(data):
            register_name = task.get("register")
            if not isinstance(register_name, str):
                continue
            # Skip dynamic register names and invalid identifiers.
            if "{{" in register_name or "{%" in register_name:
                continue
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", register_name):
                continue
            names.add(register_name)
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
    from . import _iter_task_include_targets

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
    scan_dirs = ["tasks", "templates", "handlers", "vars"]
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
                if lowered in IGNORED_IDENTIFIERS:
                    continue
                candidates.add(name)
            for match in JINJA_VAR_RE.findall(text):
                lowered = match.lower()
                if lowered not in IGNORED_IDENTIFIERS and match not in local_bindings:
                    candidates.add(match)
            if file_path.suffix in {".yml", ".yaml"}:
                for line in text.splitlines():
                    if "when:" not in line:
                        continue
                    expression = _QUOTED_STRING_RE.sub("", line.split("when:", 1)[1])
                    for token_match in JINJA_IDENTIFIER_RE.finditer(expression):
                        token = token_match.group(1)
                        if not _is_when_expression_token_candidate(
                            expression, token_match
                        ):
                            continue
                        lowered = token.lower()
                        if lowered in IGNORED_IDENTIFIERS:
                            continue
                        candidates.add(token)
    candidates -= _REGISTERED_RESULT_ATTRS
    return candidates


def _is_when_expression_token_candidate(
    expression: str,
    token_match: re.Match[str],
) -> bool:
    """Return whether a token from a ``when:`` expression should count as input."""
    token = token_match.group(1).lower()
    if token in _WHEN_OPERATOR_KEYWORDS:
        return False

    start = token_match.start(1)
    end = token_match.end(1)

    # Ignore dotted attributes like result.stdout or result.rc.
    if start > 0 and expression[start - 1] == ".":
        return False

    before = expression[:start].rstrip()
    if _WHEN_FILTER_OR_TEST_CONTEXT_RE.search(before):
        return False

    # Ignore callable/filter-like names such as version(...), search(...), etc.
    after = expression[end:].lstrip()
    if after.startswith("("):
        return False

    return True


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
