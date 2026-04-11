"""Task file traversal and include-resolution helpers for fsrc."""

from __future__ import annotations

from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
import re

import yaml

from prism.scanner_extract import task_line_parsing as tlp


def _normalize_exclude_patterns(exclude_paths: list[str] | None) -> list[str]:
    if not exclude_paths:
        return []
    normalized_patterns: list[str] = []
    for item in exclude_paths:
        if not isinstance(item, str):
            continue
        candidate = item.strip().replace("\\", "/")
        if not candidate:
            continue
        if candidate.startswith("/") or re.match(r"^[A-Za-z]:/", candidate):
            continue

        segments = [
            segment for segment in candidate.split("/") if segment not in {"", "."}
        ]
        if any(segment == ".." for segment in segments):
            continue

        normalized = "/".join(segments)
        if normalized:
            normalized_patterns.append(normalized)
    return normalized_patterns


def _is_relpath_excluded(relpath: str, exclude_paths: list[str] | None) -> bool:
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
    try:
        relpath = str(path.resolve().relative_to(role_root.resolve()))
    except ValueError:
        return False
    return _is_relpath_excluded(relpath, exclude_paths)


def _format_inline_yaml(value: object) -> str:
    text = yaml.safe_dump(value, default_flow_style=True, sort_keys=False).strip()
    return text.replace("\n", " ").replace("...", "").strip()


def _yaml_cache_identity(file_path: Path) -> tuple[str, int, int] | None:
    try:
        stat = file_path.stat()
    except OSError:
        return None
    return (str(file_path.resolve()), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=512)
def _load_yaml_file_cached(
    resolved_path: str,
    modified_time_ns: int,
    size_bytes: int,
) -> object | None:
    _ = modified_time_ns
    _ = size_bytes
    try:
        return yaml.safe_load(Path(resolved_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
        return None


def _load_yaml_file(file_path: Path) -> object | None:
    identity = _yaml_cache_identity(file_path)
    if identity is None:
        return None
    return _load_yaml_file_cached(*identity)


def _iter_task_mappings(data: object):
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            yield item
            for key in tlp.TASK_BLOCK_KEYS:
                nested = item.get(key)
                if nested is not None:
                    yield from _iter_task_mappings(nested)


def _iter_task_include_targets(data: object) -> list[str]:
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


def _iter_role_include_targets(task: dict) -> list[str]:
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


def _resolve_task_include(
    role_root: Path, current_file: Path, include_target: str
) -> Path | None:
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


def _collect_task_files(
    role_root: Path,
    exclude_paths: list[str] | None = None,
) -> list[Path]:
    tasks_dir = role_root / "tasks"
    if not tasks_dir.is_dir():
        return []

    main_file = tasks_dir / "main.yml"
    if not main_file.is_file() or _is_path_excluded(
        main_file, role_root, exclude_paths
    ):
        return sorted(
            path
            for path in tasks_dir.rglob("*")
            if path.is_file()
            and path.suffix in {".yml", ".yaml"}
            and not _is_path_excluded(path, role_root, exclude_paths)
        )

    ordered: list[Path] = []
    visited: set[Path] = set()

    def _visit(task_file: Path) -> None:
        if task_file in visited:
            return
        if _is_path_excluded(task_file, role_root, exclude_paths):
            return
        visited.add(task_file)
        ordered.append(task_file)

        data = _load_yaml_file(task_file)
        for include_target in _iter_task_include_targets(data):
            resolved = _resolve_task_include(role_root, task_file, include_target)
            if resolved is not None:
                _visit(resolved)

    _visit(main_file)
    return ordered


def _collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
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
