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
) -> list[Path]:
    role_root = Path(role_path).resolve()
    include_files: set[Path] = set()
    for task_file in collect_task_files(role_root, exclude_paths=exclude_paths):
        data = load_yaml_file(task_file)
        if not isinstance(data, list):
            continue
        for task in data:
            if not isinstance(task, dict):
                continue
            for key in INCLUDE_VARS_KEYS:
                if key not in task:
                    continue
                value = task.get(key)
                if isinstance(value, str):
                    include_path = (task_file.parent / value).resolve()
                    if include_path.is_file():
                        include_files.add(include_path)
                elif isinstance(value, dict):
                    file_value = value.get("file") or value.get("_raw_params")
                    if isinstance(file_value, str):
                        include_path = (task_file.parent / file_value).resolve()
                        if include_path.is_file():
                            include_files.add(include_path)
    return sorted(include_files)


__all__ = ["collect_include_vars_files"]
