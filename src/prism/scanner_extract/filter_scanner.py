"""Canonical filter scanner primitives used by scanner runtime and tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable


def scan_for_default_filters(
    role_path: str,
    *,
    exclude_paths: list[str] | None,
    ignored_dirs: tuple[str, ...],
    collect_task_files: Callable[[Path, list[str] | None], list[Path]],
    is_relpath_excluded: Callable[[str, list[str] | None], bool],
    is_path_excluded: Callable[[Path, Path, list[str] | None], bool],
    scan_file_for_default_filters: Callable[[Path, Path], list[dict]],
) -> list[dict]:
    """Scan files under role_path for uses of the default() filter."""
    occurrences: list[dict] = []
    role_root = Path(role_path).resolve()
    scanned_files: set[Path] = set()

    for task_file in collect_task_files(role_root, exclude_paths):
        scanned_files.add(task_file.resolve())
        occurrences.extend(scan_file_for_default_filters(task_file, role_root))

    role_path_str = str(role_root)
    for root, dirs, files in os.walk(role_path_str):
        dirs[:] = [
            d
            for d in dirs
            if d not in ignored_dirs
            and not is_relpath_excluded(
                str((Path(root) / d).resolve().relative_to(role_root)),
                exclude_paths,
            )
        ]
        for fname in files:
            fpath = Path(root) / fname
            if is_path_excluded(fpath, role_root, exclude_paths):
                continue
            if fpath.resolve() in scanned_files:
                continue
            occurrences.extend(scan_file_for_default_filters(fpath, role_root))

    return sorted(occurrences, key=lambda item: (item["file"], item["line_no"]))


def scan_for_all_filters(
    role_path: str,
    *,
    exclude_paths: list[str] | None,
    ignored_dirs: tuple[str, ...],
    collect_task_files: Callable[[Path, list[str] | None], list[Path]],
    is_relpath_excluded: Callable[[str, list[str] | None], bool],
    is_path_excluded: Callable[[Path, Path, list[str] | None], bool],
    scan_file_for_all_filters: Callable[[Path, Path], list[dict]],
) -> list[dict]:
    """Scan files under role_path for all discovered Jinja filters."""
    occurrences: list[dict] = []
    role_root = Path(role_path).resolve()
    scanned_files: set[Path] = set()

    for task_file in collect_task_files(role_root, exclude_paths):
        scanned_files.add(task_file.resolve())
        occurrences.extend(scan_file_for_all_filters(task_file, role_root))

    role_path_str = str(role_root)
    for root, dirs, files in os.walk(role_path_str):
        dirs[:] = [
            d
            for d in dirs
            if d not in ignored_dirs
            and not is_relpath_excluded(
                str((Path(root) / d).resolve().relative_to(role_root)),
                exclude_paths,
            )
        ]
        for fname in files:
            fpath = Path(root) / fname
            if is_path_excluded(fpath, role_root, exclude_paths):
                continue
            if fpath.resolve() in scanned_files:
                continue
            occurrences.extend(scan_file_for_all_filters(fpath, role_root))

    return sorted(occurrences, key=lambda item: (item["file"], item["line_no"]))


def scan_file_for_default_filters(
    file_path: Path,
    role_root: Path,
    *,
    default_re,
    scan_text_for_default_filters_with_ast: Callable[[str, list[str]], list[dict]],
) -> list[dict]:
    """Scan a single file for uses of the default() filter."""
    occurrences: list[dict] = []
    seen: set[tuple[int, str, str]] = set()
    try:
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        ast_rows = scan_text_for_default_filters_with_ast(text, lines)
        ast_line_numbers = {row["line_no"] for row in ast_rows}

        for row in ast_rows:
            key = (row["line_no"], row["match"], row["args"])
            if key in seen:
                continue
            seen.add(key)
            row["file"] = str(file_path.relative_to(role_root))
            occurrences.append(row)

        for idx, line in enumerate(lines, start=1):
            if idx in ast_line_numbers and ("{{" in line or "{%" in line):
                continue
            for match in default_re.finditer(line):
                args = (match.group("args") or "").strip()
                excerpt = line[max(0, match.start() - 80) : match.end() + 80].strip()
                key = (idx, excerpt, args)
                if key in seen:
                    continue
                seen.add(key)
                occurrences.append(
                    {
                        "file": str(file_path.relative_to(role_root)),
                        "line_no": idx,
                        "line": line,
                        "match": excerpt,
                        "args": args,
                    }
                )
    except (UnicodeDecodeError, PermissionError, OSError):
        return []
    return occurrences


def scan_file_for_all_filters(
    file_path: Path,
    role_root: Path,
    *,
    any_filter_re,
    scan_text_for_all_filters_with_ast: Callable[[str, list[str]], list[dict]],
) -> list[dict]:
    """Scan a single file for uses of any Jinja filter."""
    occurrences: list[dict] = []
    seen: set[tuple[int, str, str, str]] = set()
    try:
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        ast_rows = scan_text_for_all_filters_with_ast(text, lines)
        ast_line_numbers = {row["line_no"] for row in ast_rows}

        for row in ast_rows:
            filter_name = str(row.get("filter_name") or "")
            key = (row["line_no"], row["match"], row["args"], filter_name)
            if key in seen:
                continue
            seen.add(key)
            row["file"] = str(file_path.relative_to(role_root))
            occurrences.append(row)

        for idx, line in enumerate(lines, start=1):
            if idx in ast_line_numbers and ("{{" in line or "{%" in line):
                continue
            for match in any_filter_re.finditer(line):
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
                        "file": str(file_path.relative_to(role_root)),
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
