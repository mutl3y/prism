"""Task file traversal and include-resolution helpers for fsrc."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
import re

import yaml

from prism.scanner_core.di_helpers import _scan_options_from_di
from prism.scanner_io.loader import parse_yaml_candidate


def _get_prepared_policy(di: object | None, policy_name: str) -> object | None:
    scan_options = _scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        return None
    prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(prepared_policy_bundle, dict):
        return None
    return prepared_policy_bundle.get(policy_name)


def _get_task_traversal_policy(di: object | None = None):
    prepared_policy = _get_prepared_policy(di, "task_traversal")
    if prepared_policy is not None:
        return prepared_policy
    raise ValueError(
        "prepared_policy_bundle.task_traversal must be provided before "
        "task_file_traversal canonical execution"
    )


def _get_yaml_parsing_policy(di: object | None = None):
    prepared_policy = _get_prepared_policy(di, "yaml_parsing")
    if prepared_policy is not None:
        return prepared_policy
    raise ValueError(
        "prepared_policy_bundle.yaml_parsing must be provided before "
        "yaml_parsing canonical execution"
    )


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


def _load_yaml_file(
    file_path: Path,
    *,
    yaml_failure_collector: list[dict[str, object]] | None = None,
    role_root: Path | None = None,
    di: object | None = None,
) -> object | None:
    return _load_yaml_file_with_metadata(
        file_path,
        yaml_failure_collector=yaml_failure_collector,
        role_root=role_root,
        di=di,
    )


def _derive_role_root_from_task_file(file_path: Path) -> Path | None:
    resolved = file_path.resolve()
    parts = resolved.parts
    if "tasks" not in parts:
        return None
    index = parts.index("tasks")
    if index <= 0:
        return None
    return Path(*parts[:index])


def _load_yaml_file_with_metadata(
    file_path: Path,
    *,
    yaml_failure_collector: list[dict[str, object]] | None = None,
    role_root: Path | None = None,
    di: object | None = None,
) -> object | None:
    identity = _yaml_cache_identity(file_path)
    if identity is None:
        if yaml_failure_collector is not None:
            collector_root = role_root or _derive_role_root_from_task_file(file_path)
            if collector_root is None:
                collector_root = file_path.resolve().parent
            failure = parse_yaml_candidate(file_path, collector_root, di=di)
            if isinstance(failure, dict):
                yaml_failure_collector.append(failure)
        return None
    parsed = _get_yaml_parsing_policy(di).load_yaml_file(Path(identity[0]))
    if parsed is None and yaml_failure_collector is not None:
        collector_root = role_root or _derive_role_root_from_task_file(file_path)
        if collector_root is None:
            collector_root = file_path.resolve().parent
        failure = parse_yaml_candidate(file_path, collector_root, di=di)
        if isinstance(failure, dict):
            yaml_failure_collector.append(failure)
    return parsed


def _iter_task_mappings(data: object, *, di: object | None = None):
    yield from _get_task_traversal_policy(di).iter_task_mappings(data)


def _iter_task_include_targets(data: object, *, di: object | None = None) -> list[str]:
    return _get_task_traversal_policy(di).iter_task_include_targets(data)


def _iter_task_include_edges(
    data: object, *, di: object | None = None
) -> list[dict[str, str]]:
    plugin = _get_task_traversal_policy(di)
    iter_edges = getattr(plugin, "iter_task_include_edges", None)
    if callable(iter_edges):
        edges = iter_edges(data)
        if isinstance(edges, list):
            return [
                edge
                for edge in edges
                if isinstance(edge, dict) and isinstance(edge.get("target"), str)
            ]
    return [
        {"module": "include_tasks", "target": target}
        for target in _iter_task_include_targets(data)
    ]


def _expand_include_target_candidates(
    task: dict,
    include_target: str,
    *,
    di: object | None = None,
) -> list[str]:
    return _get_task_traversal_policy(di).expand_include_target_candidates(
        task, include_target
    )


def _iter_role_include_targets(task: dict, *, di: object | None = None) -> list[str]:
    return _get_task_traversal_policy(di).iter_role_include_targets(task)


def _iter_dynamic_role_include_targets(
    task: dict,
    *,
    di: object | None = None,
) -> list[str]:
    return _get_task_traversal_policy(di).iter_dynamic_role_include_targets(task)


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
    *,
    di: object | None = None,
) -> list[Path]:
    ordered, _unresolved = _collect_task_files_with_unresolved_includes(
        role_root,
        exclude_paths=exclude_paths,
        di=di,
    )
    return ordered


def _collect_task_files_with_unresolved_includes(
    role_root: Path,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> tuple[list[Path], list[dict[str, str]]]:
    tasks_dir = role_root / "tasks"
    if not tasks_dir.is_dir():
        return [], []

    main_file = tasks_dir / "main.yml"
    if not main_file.is_file() or _is_path_excluded(
        main_file, role_root, exclude_paths
    ):
        return (
            sorted(
                path
                for path in tasks_dir.rglob("*")
                if path.is_file()
                and path.suffix in {".yml", ".yaml"}
                and not _is_path_excluded(path, role_root, exclude_paths)
            ),
            [],
        )

    ordered: list[Path] = []
    visited: set[Path] = set()
    unresolved_edges: list[dict[str, str]] = []
    unresolved_keys: set[tuple[str, str, str]] = set()

    def _visit(task_file: Path) -> None:
        if task_file in visited:
            return
        if _is_path_excluded(task_file, role_root, exclude_paths):
            return
        visited.add(task_file)
        ordered.append(task_file)

        data = _load_yaml_file(task_file, di=di)
        for edge in _iter_task_include_edges(data, di=di):
            include_target = str(edge.get("target") or "").strip()
            if not include_target:
                continue
            resolved = _resolve_task_include(role_root, task_file, include_target)
            if resolved is not None:
                _visit(resolved)
                continue

            task_file_rel = task_file.relative_to(role_root).as_posix()
            unresolved_key = (
                task_file_rel,
                str(edge.get("module") or "include_tasks"),
                include_target,
            )
            if unresolved_key in unresolved_keys:
                continue
            unresolved_keys.add(unresolved_key)
            unresolved_edges.append(
                {
                    "task_file": task_file_rel,
                    "module": unresolved_key[1],
                    "include_target": include_target,
                    "resolution": "unresolved",
                }
            )

    _visit(main_file)
    return ordered, unresolved_edges


def _collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    role_root = Path(role_path).resolve()
    return _get_task_traversal_policy(di).collect_unconstrained_dynamic_task_includes(
        role_root=role_root,
        task_files=_collect_task_files(
            role_root,
            exclude_paths=exclude_paths,
            di=di,
        ),
        load_yaml_file=lambda file_path: _load_yaml_file(file_path, di=di),
    )


def _collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    role_root = Path(role_path).resolve()
    return _get_task_traversal_policy(di).collect_unconstrained_dynamic_role_includes(
        role_root=role_root,
        task_files=_collect_task_files(
            role_root,
            exclude_paths=exclude_paths,
            di=di,
        ),
        load_yaml_file=lambda file_path: _load_yaml_file(file_path, di=di),
    )


def is_path_excluded(
    path: Path, role_root: Path, exclude_paths: list[str] | None
) -> bool:
    return _is_path_excluded(path, role_root, exclude_paths)


def load_yaml_file(
    path: Path,
    *,
    yaml_failure_collector: list[dict[str, object]] | None = None,
    role_root: Path | None = None,
    di: object | None = None,
) -> object:
    return _load_yaml_file(
        path,
        yaml_failure_collector=yaml_failure_collector,
        role_root=role_root,
        di=di,
    )


def iter_task_mappings(data: object, *, di: object | None = None):
    yield from _iter_task_mappings(data, di=di)


def iter_task_include_targets(data: object, *, di: object | None = None) -> list[str]:
    return _iter_task_include_targets(data, di=di)


def iter_role_include_targets(task: dict, *, di: object | None = None) -> list[str]:
    return _iter_role_include_targets(task, di=di)


def iter_dynamic_role_include_targets(
    task: dict,
    *,
    di: object | None = None,
) -> list[str]:
    return _iter_dynamic_role_include_targets(task, di=di)


def collect_task_files(
    role_root: Path,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
) -> list[Path]:
    return _collect_task_files(role_root, exclude_paths=exclude_paths, di=di)


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    return _collect_unconstrained_dynamic_task_includes(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    return _collect_unconstrained_dynamic_role_includes(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )
