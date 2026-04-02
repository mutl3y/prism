"""Task file traversal, include resolution, and path handling.

This module handles filesystem operations: path exclusions, YAML loading,
task file discovery, and include target resolution.

Functions exported:
  _normalize_exclude_patterns, _is_relpath_excluded, _is_path_excluded,
  _format_inline_yaml, _load_yaml_file,
  _iter_task_mappings, _iter_task_include_targets, _expand_include_target_candidates,
  _iter_role_include_targets, _iter_dynamic_role_include_targets,
  _resolve_task_include, _collect_task_files,
  _collect_unconstrained_dynamic_task_includes, _collect_unconstrained_dynamic_role_includes
"""

from __future__ import annotations

import yaml
from fnmatch import fnmatch
from pathlib import Path

from . import task_line_parsing as tlp

# ---------------------------------------------------------------------------
# Path exclusion helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# YAML utility
# ---------------------------------------------------------------------------


def _format_inline_yaml(value: object) -> str:
    """Render a value as compact inline YAML for README tables."""
    text = yaml.safe_dump(value, default_flow_style=True, sort_keys=False).strip()
    return text.replace("\n", " ").replace("...", "").strip()


# ---------------------------------------------------------------------------
# YAML file loading
# ---------------------------------------------------------------------------


def _load_yaml_file(file_path: Path) -> object | None:
    """Load a YAML file and return its contents, or ``None`` on failure."""
    try:
        return yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Task document iteration
# ---------------------------------------------------------------------------


def _iter_task_mappings(data: object):
    """Yield task dictionaries from a YAML task document recursively."""
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            yield item
            for key in tlp.TASK_BLOCK_KEYS:
                nested = item.get(key)
                if nested is not None:
                    yield from _iter_task_mappings(nested)


# ---------------------------------------------------------------------------
# Task include target extraction
# ---------------------------------------------------------------------------


def _iter_task_include_targets(data: object) -> list[str]:
    """Return include/import task targets found in a task YAML structure."""
    targets: list[str] = []
    for task in _iter_task_mappings(data):
        for key in tlp.TASK_INCLUDE_KEYS:
            if key not in task:
                continue
            value = task[key]
            if isinstance(value, str):
                expanded = _expand_include_target_candidates(task, value)
                if expanded:
                    targets.extend(expanded)
                else:
                    candidate = value.strip()
                    if candidate:
                        targets.append(candidate)
            elif isinstance(value, dict):
                file_value = value.get("file") or value.get("_raw_params")
                if isinstance(file_value, str):
                    expanded = _expand_include_target_candidates(task, file_value)
                    if expanded:
                        targets.extend(expanded)
                    else:
                        candidate = file_value.strip()
                        if candidate:
                            targets.append(candidate)
    return targets


def _expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
    """Return concrete include candidates from static or constrained dynamic target."""
    candidate = include_target.strip()
    if not candidate:
        return []
    if "{{" not in candidate and "{%" not in candidate:
        return [candidate]

    match = tlp.TEMPLATED_INCLUDE_RE.match(candidate)
    if not match:
        return []

    variable = (match.group("var") or "").strip()
    if not variable:
        return []
    allowed_values = tlp._extract_constrained_when_values(task, variable)
    if not allowed_values:
        return []

    prefix = (match.group("prefix") or "").strip()
    suffix = (match.group("suffix") or "").strip()
    return [f"{prefix}{value}{suffix}" for value in allowed_values]


# ---------------------------------------------------------------------------
# Role include target extraction
# ---------------------------------------------------------------------------


def _iter_role_include_targets(task: dict) -> list[str]:
    """Return static role names referenced by include_role/import_role keys."""
    role_targets: list[str] = []
    for key in tlp.ROLE_INCLUDE_KEYS:
        if key not in task:
            continue
        value = task[key]
        ref: str | None = None
        if isinstance(value, str):
            ref = value
        elif isinstance(value, dict):
            candidate = value.get("name") or value.get("_raw_params")
            if isinstance(candidate, str):
                ref = candidate
        if not ref:
            continue
        ref = ref.strip()
        if not ref or "{{" in ref or "{%" in ref:
            continue
        role_targets.append(ref)
    return role_targets


def _iter_dynamic_role_include_targets(task: dict) -> list[str]:
    """Return templated role refs from include_role/import_role keys."""
    dynamic_targets: list[str] = []
    for key in tlp.ROLE_INCLUDE_KEYS:
        if key not in task:
            continue
        value = task[key]
        ref: str | None = None
        if isinstance(value, str):
            ref = value
        elif isinstance(value, dict):
            candidate = value.get("name") or value.get("_raw_params")
            if isinstance(candidate, str):
                ref = candidate
        if not ref:
            continue
        ref = ref.strip()
        if ref and ("{{" in ref or "{%" in ref):
            dynamic_targets.append(ref)
    return dynamic_targets


# ---------------------------------------------------------------------------
# Task include resolution
# ---------------------------------------------------------------------------


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

    # Heuristic fallback for role fixtures/docs: if include target has no
    # directory segment, try finding a unique basename under tasks/**.
    if not path.is_absolute() and len(path.parts) == 1:
        tasks_dir = role_root / "tasks"
        suffixes = [path.suffix] if path.suffix else [".yml", ".yaml"]
        fallback_matches: list[Path] = []
        for suffix in suffixes:
            name = path.name if path.suffix else f"{path.name}{suffix}"
            fallback_matches.extend(p for p in tasks_dir.rglob(name) if p.is_file())
        unique_matches = sorted({p.resolve() for p in fallback_matches})
        if len(unique_matches) == 1:
            return unique_matches[0]

    return None


# ---------------------------------------------------------------------------
# Task file collection
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Unconstrained dynamic include detection
# ---------------------------------------------------------------------------


def _collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    """Return unconstrained dynamic include/import task references.

    A dynamic include is considered unconstrained when it contains templating
    and cannot be expanded into static candidates via simple ``when`` allow-lists.
    """
    role_root = Path(role_path).resolve()
    findings: list[dict[str, str]] = []

    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in _iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in tlp.TASK_INCLUDE_KEYS:
                if include_key not in task:
                    continue
                include_target = task[include_key]
                include_path: str | None = None
                if isinstance(include_target, str):
                    include_path = include_target
                elif isinstance(include_target, dict):
                    candidate = include_target.get("file") or include_target.get(
                        "_raw_params"
                    )
                    if isinstance(candidate, str):
                        include_path = candidate

                if not include_path:
                    continue
                include_path = include_path.strip()
                if "{{" not in include_path and "{%" not in include_path:
                    continue
                if _expand_include_target_candidates(task, include_path):
                    continue

                findings.append(
                    {
                        "file": relpath,
                        "task": task_name,
                        "module": (
                            "import_tasks"
                            if "import_tasks" in include_key
                            else "include_tasks"
                        ),
                        "target": include_path,
                    }
                )

    return findings


def _collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    """Return unconstrained dynamic include/import role references.

    A dynamic include role reference is considered unconstrained when it
    contains templating and cannot be expanded into static candidates via
    simple ``when`` allow-lists.
    """
    role_root = Path(role_path).resolve()
    findings: list[dict[str, str]] = []

    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in _iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in tlp.ROLE_INCLUDE_KEYS:
                if include_key not in task:
                    continue
                include_target = task[include_key]
                role_ref: str | None = None
                if isinstance(include_target, str):
                    role_ref = include_target
                elif isinstance(include_target, dict):
                    candidate = include_target.get("name") or include_target.get(
                        "_raw_params"
                    )
                    if isinstance(candidate, str):
                        role_ref = candidate

                if not role_ref:
                    continue
                role_ref = role_ref.strip()
                if "{{" not in role_ref and "{%" not in role_ref:
                    continue
                if _expand_include_target_candidates(task, role_ref):
                    continue

                findings.append(
                    {
                        "file": relpath,
                        "task": task_name,
                        "module": (
                            "import_role"
                            if "import_role" in include_key
                            else "include_role"
                        ),
                        "target": role_ref,
                    }
                )

    return findings
