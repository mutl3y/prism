"""Ansible-owned variable extraction helpers for fsrc."""

from __future__ import annotations

from pathlib import Path

from prism.scanner_plugins.ansible.task_line_parsing import INCLUDE_VARS_KEYS


def collect_include_vars_files(
    *,
    role_path: str,
    exclude_paths: list[str] | None,
    collect_task_files,
    load_yaml_file,
    include_vars_keys: set[str] | None = None,
) -> list[Path]:
    role_root = Path(role_path).resolve()
    _keys = include_vars_keys if include_vars_keys is not None else INCLUDE_VARS_KEYS
    result: list[Path] = []
    seen: set[Path] = set()
    for task_file in collect_task_files(role_root, exclude_paths=exclude_paths):
        data = load_yaml_file(task_file)
        if not isinstance(data, list):
            continue
        for task in data:
            if not isinstance(task, dict):
                continue
            for key in _keys:
                if key not in task:
                    continue
                value = task[key]
                ref: str | None = None
                if isinstance(value, str):
                    ref = value
                elif isinstance(value, dict):
                    file_candidate = value.get("file")
                    name_candidate = value.get("name")
                    ref = (
                        file_candidate
                        if isinstance(file_candidate, str)
                        else name_candidate if isinstance(name_candidate, str) else None
                    )
                if not ref or "{{" in ref or "{%" in ref:
                    continue
                for candidate in (
                    (task_file.parent / ref).resolve(),
                    (role_root / "vars" / ref).resolve(),
                    (role_root / ref).resolve(),
                ):
                    if not candidate.is_file() or candidate in seen:
                        continue
                    try:
                        candidate.relative_to(role_root)
                    except ValueError:
                        continue
                    seen.add(candidate)
                    result.append(candidate)
                    break
    return result


__all__ = ["collect_include_vars_files"]
