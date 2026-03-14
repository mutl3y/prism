"""Core scanner implementation.

This module provides utilities to scan an Ansible role for common
patterns (for example uses of the `default()` filter), load role
metadata and variables, and render a README using a Jinja2 template.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import yaml
import jinja2

STYLE_SECTION_ALIASES = {
    "galaxy info": "galaxy_info",
    "requirements": "requirements",
    "dependencies": "requirements",
    "license": "license",
    "author information": "author_information",
    "license and author": "license_author",
    "sponsors": "sponsors",
    "role purpose and capabilities": "purpose",
    "overview": "purpose",
    "summary": "purpose",
    "inputs variables summary": "variable_summary",
    "inputs / variables summary": "variable_summary",
    "role variables": "role_variables",
    "variables": "role_variables",
    "task module usage summary": "task_summary",
    "task/module usage summary": "task_summary",
    "role contents": "role_contents",
    "role contents summary": "role_contents",
    "auto detected role features": "features",
    "auto-detected role features": "features",
    "comparison against local baseline role": "comparison",
    "example playbook": "example_usage",
    "use with ansible (and docker python library)": "example_usage",
    "inferred example usage": "example_usage",
    "usage": "example_usage",
    "configuring settings not listed in role variables": "variable_guidance",
    "changing the default port and idempotency": "variable_guidance",
    "local testing": "local_testing",
    "faq pitfalls": "faq_pitfalls",
    "contributing": "contributing",
    "detected usages of the default filter": "default_filters",
    "detected usages of the default() filter": "default_filters",
}

DEFAULT_SECTION_SPECS = [
    ("galaxy_info", "Galaxy Info"),
    ("requirements", "Requirements"),
    ("purpose", "Role purpose and capabilities"),
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

DEFAULT_TARGET_RE = re.compile(r"\b(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\|\s*default\b")
JINJA_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
VAULT_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*!vault\b", re.MULTILINE)

IGNORED_IDENTIFIERS = {
    "true",
    "false",
    "none",
    "null",
    "omit",
    "lookup",
    "query",
    "default",
    "item",
    "ansible_facts",
    "hostvars",
    "groups",
    "inventory_hostname",
    "vars",
}


def scan_for_default_filters(role_path: str) -> list:
    """Scan files under ``role_path`` for uses of the ``default()`` filter.

    Returns a list of occurrence dictionaries with keys: ``file``,
    ``line_no``, ``line``, ``match`` and ``args``.
    """
    occurrences: list[dict] = []
    role_root = Path(role_path).resolve()
    scanned_files: set[Path] = set()

    for task_file in _collect_task_files(role_root):
        scanned_files.add(task_file.resolve())
        occurrences.extend(_scan_file_for_default_filters(task_file, role_root))

    role_path = str(role_root)
    for root, dirs, files in os.walk(role_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.resolve() in scanned_files:
                continue
            occurrences.extend(_scan_file_for_default_filters(fpath, role_root))

    return sorted(occurrences, key=lambda item: (item["file"], item["line_no"]))


def _scan_file_for_default_filters(file_path: Path, role_root: Path) -> list[dict]:
    """Scan a single file for uses of the ``default()`` filter."""
    occurrences: list[dict] = []
    try:
        with file_path.open("r", encoding="utf-8") as fh:
            for idx, raw_line in enumerate(fh, start=1):
                line = raw_line.rstrip("\n")
                for match in DEFAULT_RE.finditer(line):
                    args = (match.group("args") or "").strip()
                    excerpt = line[max(0, match.start() - 80) : match.end() + 80]
                    occurrences.append(
                        {
                            "file": os.path.relpath(file_path, role_root),
                            "line_no": idx,
                            "line": line,
                            "match": excerpt.strip(),
                            "args": args,
                        }
                    )
    except UnicodeDecodeError, PermissionError, OSError:
        return []
    return occurrences


def _extract_default_target_var(occurrence: dict) -> str | None:
    """Extract the variable name used with ``| default(...)`` when available."""
    line = str(occurrence.get("line") or occurrence.get("match") or "")
    match = DEFAULT_TARGET_RE.search(line)
    if not match:
        return None
    return match.group("var")


def _collect_task_files(role_root: Path) -> list[Path]:
    """Collect task files reachable from ``tasks/main.yml`` recursively."""
    tasks_dir = role_root / "tasks"
    if not tasks_dir.is_dir():
        return []

    entrypoints = [tasks_dir / "main.yml"] if (tasks_dir / "main.yml").exists() else []
    if not entrypoints:
        entrypoints = sorted(
            path
            for path in tasks_dir.rglob("*")
            if path.is_file() and path.suffix in {".yml", ".yaml"}
        )

    discovered: list[Path] = []
    pending = list(entrypoints)
    seen: set[Path] = set()
    while pending:
        current = pending.pop(0).resolve()
        if current in seen or not current.is_file():
            continue
        seen.add(current)
        discovered.append(current)

        data = _load_yaml_file(current)
        for include_target in _iter_task_include_targets(data):
            resolved = _resolve_task_include(role_root, current, include_target)
            if resolved is not None and resolved not in seen:
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


def _collect_include_vars_files(role_path: str) -> list[Path]:
    """Return var files referenced by static ``include_vars`` tasks within the role.

    Only files whose paths can be resolved to a concrete file inside the role
    directory are returned.  Dynamic paths containing Jinja2 expressions are
    silently ignored.
    """
    role_root = Path(role_path).resolve()
    task_files = _collect_task_files(role_root)
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


def _collect_set_fact_names(role_path: str) -> set[str]:
    """Return variable names assigned by ``set_fact`` tasks within the role.

    Only names with static (non-templated) keys are returned.
    """
    role_root = Path(role_path).resolve()
    task_files = _collect_task_files(role_root)
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


def load_variables(role_path: str, include_vars_main: bool = True) -> dict:
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
    for extra_path in _collect_include_vars_files(role_path):
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


def collect_role_contents(role_path: str) -> dict:
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
                    entries.append(str(p.relative_to(rp)))
        result[name] = entries
    # include parsed meta file for richer template rendering
    try:
        result["meta"] = load_meta(role_path)
    except Exception:
        result["meta"] = {}
    result["features"] = extract_role_features(role_path)
    return result


def extract_role_features(role_path: str) -> dict:
    """Extract adaptive role features from tasks and role structure.

    These heuristics are intentionally lightweight and update automatically
    as task files change, providing richer documentation without manual edits.
    """
    role_root = Path(role_path).resolve()
    task_files = _collect_task_files(role_root)

    include_count = 0
    tasks_scanned = 0
    privileged_tasks = 0
    conditional_tasks = 0
    tagged_tasks = 0
    modules: set[str] = set()
    handlers_notified: set[str] = set()

    for task_file in task_files:
        data = _load_yaml_file(task_file)
        include_count += len(_iter_task_include_targets(data))
        for task in _iter_task_mappings(data):
            tasks_scanned += 1
            module_name = _detect_task_module(task)
            if module_name:
                modules.add(module_name)

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
        "handlers_notified": (
            ", ".join(sorted(handlers_notified)) if handlers_notified else "none"
        ),
        "privileged_tasks": privileged_tasks,
        "conditional_tasks": conditional_tasks,
        "tagged_tasks": tagged_tasks,
    }


def _compute_quality_metrics(role_path: str) -> dict:
    """Compute lightweight role quality metrics for comparison output."""
    contents = collect_role_contents(role_path)
    features = contents.get("features", {}) if isinstance(contents, dict) else {}
    variables = load_variables(role_path)

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

    defaults_hits = len(scan_for_default_filters(role_path))
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


def build_comparison_report(target_role_path: str, baseline_role_path: str) -> dict:
    """Build a compact comparison between a target role and local baseline role."""
    target = _compute_quality_metrics(target_role_path)
    baseline = _compute_quality_metrics(baseline_role_path)

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


def _parse_comma_values(raw_value: str) -> list[str]:
    """Parse a comma-separated feature value into a list."""
    raw = (raw_value or "").strip()
    if not raw or raw == "none":
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


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
    secret_tokens = (
        "password",
        "passwd",
        "secret",
        "token",
        "apikey",
        "api_key",
        "private_key",
        "vault",
    )
    return any(token in lowered for token in secret_tokens)


def _resembles_password_like(value: object) -> bool:
    """Return True when a string value looks like a credential/token."""
    if not isinstance(value, str):
        return False

    raw = value.strip().strip("'\"")
    if not raw:
        return False
    lowered = raw.lower()

    if any(marker in lowered for marker in ("$ansible_vault", "!vault")):
        return True
    if raw.startswith(("ghp_", "gho_", "glpat-", "AKIA", "ASIA")):
        return True
    if raw.startswith(("http://", "https://", "ssh://")):
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
        return (
            "$ansible_vault" in lowered
            or "!vault" in lowered
            or lowered.startswith("vault_")
        )
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


def _collect_referenced_variable_names(role_path: str) -> set[str]:
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
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError, OSError:
                continue
            for match in JINJA_VAR_RE.findall(text):
                if match.lower() not in IGNORED_IDENTIFIERS:
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


def build_variable_insights(
    role_path: str,
    seed_paths: list[str] | None = None,
    include_vars_main: bool = True,
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

    rows: list[dict] = []
    for name in sorted(set(defaults_data) | set(vars_data)):
        has_default = name in defaults_data
        has_var = name in vars_data
        value = vars_data[name] if has_var else defaults_data.get(name)
        source = "defaults/main.yml"
        if has_var and has_default:
            source = "defaults/main.yml + vars/main.yml override"
        elif has_var:
            source = "vars/main.yml"
        rows.append(
            {
                "name": name,
                "type": _infer_variable_type(value),
                "default": _format_inline_yaml(value),
                "source": source,
                "documented": True,
                "required": False,
                "secret": _is_sensitive_variable(name, value),
            }
        )

    # Discover variables from include_vars task references
    known_names: set[str] = {row["name"] for row in rows}
    role_root = Path(role_path).resolve()
    for extra_path in _collect_include_vars_files(role_path):
        extra_data = _load_yaml_file(extra_path)
        if not isinstance(extra_data, dict):
            continue
        rel_source = str(extra_path.relative_to(role_root))
        for name in sorted(extra_data):
            if name in known_names:
                continue
            known_names.add(name)
            rows.append(
                {
                    "name": name,
                    "type": _infer_variable_type(extra_data[name]),
                    "default": _format_inline_yaml(extra_data[name]),
                    "source": rel_source,
                    "documented": True,
                    "required": False,
                    "secret": _is_sensitive_variable(name, extra_data[name]),
                }
            )

    # Discover computed variable names from set_fact tasks
    for name in sorted(_collect_set_fact_names(role_path) - known_names):
        rows.append(
            {
                "name": name,
                "type": "computed",
                "default": "—",
                "source": "tasks (set_fact)",
                "documented": True,
                "required": False,
                "secret": False,
            }
        )

    known_names: set[str] = {row["name"] for row in rows}
    referenced_names = _collect_referenced_variable_names(role_path)

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
            }
        )

    # redact secret defaults before returning rows
    for row in rows:
        if row.get("secret"):
            row["default"] = "<secret>"

    return rows


def build_doc_insights(
    role_name: str,
    description: str,
    metadata: dict,
    variables: dict,
    variable_insights: list[dict],
) -> dict:
    """Build inferred purpose/capability/examples for richer README output."""
    features = metadata.get("features", {}) if isinstance(metadata, dict) else {}
    modules = _parse_comma_values(str(features.get("unique_modules", "none")))
    handlers = _parse_comma_values(str(features.get("handlers_notified", "none")))

    capability_rules = (
        (
            ("template", "ansible.builtin.template", "copy", "ansible.builtin.copy"),
            "Deploy configuration or content files",
        ),
        (
            (
                "service",
                "ansible.builtin.service",
                "systemd",
                "ansible.builtin.systemd",
            ),
            "Manage service lifecycle and state",
        ),
        (
            ("package", "ansible.builtin.package", "apt", "yum", "dnf"),
            "Install and manage packages",
        ),
        (
            ("user", "ansible.builtin.user", "group", "ansible.builtin.group"),
            "Manage users and groups",
        ),
        (
            (
                "lineinfile",
                "ansible.builtin.lineinfile",
                "replace",
                "ansible.builtin.replace",
            ),
            "Modify existing configuration files in-place",
        ),
    )
    capabilities: list[str] = []
    module_set = set(modules)
    for keys, sentence in capability_rules:
        if any(key in module_set for key in keys):
            capabilities.append(sentence)
    if int(features.get("recursive_task_includes", 0) or 0) > 0:
        capabilities.append("Uses nested task includes for modular orchestration")
    if handlers:
        capabilities.append("Triggers role handlers based on task changes")
    if not capabilities:
        capabilities.append("Provides reusable Ansible automation tasks")

    purpose_summary = (
        description.strip()
        if description
        else (
            f"The role `{role_name}` automates setup and configuration tasks with Ansible best-practice structure."
        )
    )

    example_vars = variable_insights[:3]
    example_lines = ["- hosts: all", "  roles:", f"    - role: {role_name}"]
    if example_vars:
        example_lines.append("      vars:")
        for row in example_vars:
            example_lines.append(f"        {row['name']}: {row['default']}")
    elif variables:
        example_lines.append("      vars: {}")

    return {
        "purpose_summary": purpose_summary,
        "capabilities": capabilities,
        "task_summary": {
            "task_files_scanned": int(features.get("task_files_scanned", 0) or 0),
            "tasks_scanned": int(features.get("tasks_scanned", 0) or 0),
            "recursive_task_includes": int(
                features.get("recursive_task_includes", 0) or 0
            ),
            "module_count": len(modules),
            "handler_count": len(handlers),
        },
        "example_playbook": "\n".join(example_lines),
    }


def _normalize_style_heading(heading: str) -> str:
    """Normalize markdown heading text for style-guide matching."""
    normalized = re.sub(r"[^a-z0-9()]+", " ", heading.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def parse_style_readme(style_readme_path: str) -> dict:
    """Parse a README style guide into section order and heading styles."""
    text = Path(style_readme_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    sections: list[dict] = []
    title_text = ""
    title_style = "setext"
    section_style = "setext"

    i = 0
    current_section: dict | None = None
    while i < len(lines):
        line = lines[i].rstrip()
        next_line = lines[i + 1].rstrip() if i + 1 < len(lines) else ""

        atx_match = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if atx_match:
            level = len(atx_match.group(1))
            title = atx_match.group(2).strip()
            if level == 1:
                title_style = "atx"
                title_text = title
            elif level == 2:
                section_style = "atx"
            if level == 2:
                canonical = STYLE_SECTION_ALIASES.get(
                    _normalize_style_heading(title), "unknown"
                )
                current_section = {"id": canonical, "title": title, "body": []}
                sections.append(current_section)
            i += 1
            continue

        if re.match(r"^=+$", next_line):
            title_style = "setext"
            if not title_text:
                title_text = line.strip()
            i += 2
            continue

        if re.match(r"^-+$", next_line):
            section_style = "setext"
            canonical = STYLE_SECTION_ALIASES.get(
                _normalize_style_heading(line), "unknown"
            )
            current_section = {"id": canonical, "title": line.strip(), "body": []}
            sections.append(current_section)
            i += 2
            continue

        if current_section is not None:
            current_section["body"].append(line)

        i += 1

    for section in sections:
        section["body"] = "\n".join(section.get("body", [])).strip()

    variable_section = next(
        (section for section in sections if section["id"] == "role_variables"), None
    )
    variable_style = "simple_list"
    variable_intro = None
    if variable_section:
        body = variable_section.get("body", "")
        if "```yaml" in body:
            variable_style = "yaml_block"
            intro_match = re.split(r"```yaml", body, maxsplit=1)
            intro = intro_match[0].strip() if intro_match else ""
            variable_intro = intro or None
        elif re.search(r"^\s*[*-]\s+`[^`]+`", body, flags=re.MULTILINE) and re.search(
            r"^\s*[*-]\s+Default:", body, flags=re.MULTILINE
        ):
            variable_style = "nested_bullets"

    return {
        "path": str(Path(style_readme_path).resolve()),
        "title_text": title_text,
        "title_style": title_style,
        "section_style": section_style,
        "sections": sections,
        "variable_style": variable_style,
        "variable_intro": variable_intro,
    }


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
    variable_insights = metadata.get("variable_insights") or []

    if variable_style == "nested_bullets":
        lines: list[str] = []
        for row in variable_insights:
            default = str(row["default"]).replace("`", "'")
            lines.append(f"* `{row['name']}`")
            lines.append(f"  * Default: {default}")
            lines.append(
                f"  * Description: {_describe_variable(row['name'], row['source'])}"
            )
        return "\n".join(lines)

    if variable_style == "yaml_block":
        intro = (
            style_guide.get("variable_intro")
            or "Available variables are listed below, along with default values (see `defaults/main.yml`):"
        )
        yaml_block = yaml.safe_dump(
            variables, sort_keys=False, default_flow_style=False
        ).strip()
        return f"{intro}\n\n```yaml\n{yaml_block}\n```"

    lines = ["The following variables are available:"]
    lines.extend(f"- `{name}`: {value}" for name, value in variables.items())
    return "\n".join(lines)


def _format_heading(text: str, level: int, style: str) -> str:
    """Format markdown headings using ATX or setext style."""
    if style == "atx":
        return f"{'#' * level} {text}"
    if level == 1:
        return f"{text}\n{'=' * len(text)}"
    if level == 2:
        return f"{text}\n{'-' * len(text)}"
    return f"{'#' * level} {text}"


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
        return "\n".join(lines)

    if section_id == "variable_guidance":
        rows = metadata.get("variable_insights") or []
        if not rows:
            return "No variable guidance available because no variable defaults were discovered."
        priority = [
            row
            for row in rows
            if any(
                keyword in row["name"]
                for keyword in ("port", "idempot", "state", "enabled")
            )
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
    style_guide = metadata.get("style_guide") or {}
    ordered_sections = list(style_guide.get("sections") or [])

    if not ordered_sections:
        ordered_sections = [
            {"id": section_id, "title": title}
            for section_id, title in DEFAULT_SECTION_SPECS
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

    rendered_title = role_name
    if style_guide.get("title_text"):
        rendered_title = role_name

    parts = [
        _format_heading(rendered_title, 1, style_guide.get("title_style", "setext")),
        "",
        description,
        "",
    ]
    for section in ordered_sections:
        body = _render_guide_section_body(
            section["id"],
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        ).strip()
        if section["id"] == "unknown":
            body = "Style section retained from guide; scanner does not map this section yet."
        if not body:
            continue
        parts.append(
            _format_heading(
                section["title"], 2, style_guide.get("section_style", "setext")
            )
        )
        parts.append("")
        parts.append(body)
        parts.append("")

    scanner_report_relpath = metadata.get("scanner_report_relpath")
    if scanner_report_relpath and metadata.get("include_scanner_report_link", True):
        parts.append(
            _format_heading(
                "Scanner report", 2, style_guide.get("section_style", "setext")
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
    lines = [
        f"{role_name} scanner report",
        "=" * (len(role_name) + len(" scanner report")),
        "",
        description,
        "",
    ]
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
) -> str:
    rp = Path(role_path)
    if not rp.is_dir():
        raise FileNotFoundError(f"role path not found: {role_path}")
    meta = load_meta(role_path)
    galaxy = meta.get("galaxy_info", {}) if isinstance(meta, dict) else {}
    role_name = galaxy.get("role_name", rp.name)
    if role_name_override and (not galaxy.get("role_name") or role_name == "repo"):
        role_name = role_name_override
    description = galaxy.get("description", "")
    variables = load_variables(role_path, include_vars_main=include_vars_main)
    requirements = load_requirements(role_path)
    requirements_display = normalize_requirements(requirements)
    found = scan_for_default_filters(role_path)
    metadata = collect_role_contents(role_path)
    variable_insights = build_variable_insights(
        role_path,
        seed_paths=vars_seed_paths,
        include_vars_main=include_vars_main,
    )
    metadata["variable_insights"] = variable_insights
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
    if style_readme_path:
        style_path = Path(style_readme_path)
        if not style_path.is_file():
            raise FileNotFoundError(f"style README not found: {style_readme_path}")
        metadata["style_guide"] = parse_style_readme(str(style_path))
    if compare_role_path:
        cp = Path(compare_role_path)
        if not cp.is_dir():
            raise FileNotFoundError(
                f"comparison role path not found: {compare_role_path}"
            )
        metadata["comparison"] = build_comparison_report(role_path, compare_role_path)

    out_path = Path(output)
    if output_format == "html" and out_path.suffix.lower() not in (".html", ".htm"):
        out_path = out_path.with_suffix(".html")

    scanner_report_path: Path | None = None
    if concise_readme:
        if scanner_report_output:
            scanner_report_path = Path(scanner_report_output)
        else:
            scanner_report_path = out_path.with_suffix(".scan-report.md")
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
        metadata["concise_readme"] = True
        metadata["include_scanner_report_link"] = include_scanner_report_link
        metadata["scanner_report_relpath"] = os.path.relpath(
            scanner_report_path, out_path.parent
        )

    # Render Markdown content without writing so we can convert if needed
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

    # Convert if necessary
    final_content: str
    if output_format == "md":
        final_content = rendered
    else:
        try:
            import markdown as _md

            html_body = _md.markdown(rendered, extensions=["extra", "toc"])
        except Exception:
            # Fallback: escape and wrap in <pre>
            import html as _html

            html_body = f"<pre>{_html.escape(rendered)}</pre>"

        final_content = f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{role_name}</title></head><body>\n{html_body}\n</body></html>'

    out_path.write_text(final_content, encoding="utf-8")
    return str(out_path.resolve())
