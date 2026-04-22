"""Tests for fsrc filter_scanner module and api.py public wrappers."""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# scan_for_default_filters — empty role dir
# ---------------------------------------------------------------------------


def test_scan_for_default_filters_empty_role(fs):
    """Returns empty list when role directory contains no files."""
    fs.create_dir("/role")

    from prism.scanner_extract.filter_scanner import scan_for_default_filters

    result = scan_for_default_filters(
        "/role",
        exclude_paths=None,
        ignored_dirs=(".git", "__pycache__"),
        collect_task_files=lambda r, e: [],
        is_relpath_excluded=lambda rel, exc: False,
        is_path_excluded=lambda p, root, exc: False,
        scan_file_for_default_filters=lambda f, r: [],
    )

    assert result == []


# ---------------------------------------------------------------------------
# scan_for_all_filters — empty role dir
# ---------------------------------------------------------------------------


def test_scan_for_all_filters_empty_role(fs):
    """Returns empty list when role directory contains no files."""
    fs.create_dir("/role")

    from prism.scanner_extract.filter_scanner import scan_for_all_filters

    result = scan_for_all_filters(
        "/role",
        exclude_paths=None,
        ignored_dirs=(".git", "__pycache__"),
        collect_task_files=lambda r, e: [],
        is_relpath_excluded=lambda rel, exc: False,
        is_path_excluded=lambda p, root, exc: False,
        scan_file_for_all_filters=lambda f, r: [],
    )

    assert result == []


# ---------------------------------------------------------------------------
# scan_file_for_default_filters — injectable mock regex
# ---------------------------------------------------------------------------


def test_scan_file_for_default_filters_injectable_regex(fs):
    """Returns correct structure when regex matches a line."""
    fs.create_dir("/role")
    fs.create_file("/role/tasks/main.yml", contents="value | default('x')\n")

    default_re = re.compile(
        r"""(?P<context>.{0,40}?)(\|\s*default\b|\bdefault\s*\()\s*(?P<args>[^)\n]{0,200})""",
        flags=re.IGNORECASE,
    )

    from prism.scanner_extract.filter_scanner import scan_file_for_default_filters

    rows = scan_file_for_default_filters(
        Path("/role/tasks/main.yml"),
        Path("/role"),
        default_re=default_re,
        scan_text_for_default_filters_with_ast=lambda text, lines: [],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["file"] == "tasks/main.yml"
    assert row["line_no"] == 1
    assert "args" in row
    assert "match" in row
    assert "line" in row


# ---------------------------------------------------------------------------
# scan_for_default_filters — occurrences returned and sorted
# ---------------------------------------------------------------------------


def test_scan_for_default_filters_returns_sorted_occurrences(fs):
    """Returns sorted occurrences from injected file scanner."""
    fs.create_dir("/role/tasks")
    fs.create_file("/role/tasks/b.yml", contents="")
    fs.create_file("/role/tasks/a.yml", contents="")

    b_occurrence = {
        "file": "tasks/b.yml",
        "line_no": 1,
        "line": "",
        "match": "",
        "args": "",
    }
    a_occurrence = {
        "file": "tasks/a.yml",
        "line_no": 1,
        "line": "",
        "match": "",
        "args": "",
    }

    def mock_scan_file(f: Path, r: Path) -> list[dict]:
        name = f.name
        if name == "b.yml":
            return [b_occurrence]
        if name == "a.yml":
            return [a_occurrence]
        return []

    from prism.scanner_extract.filter_scanner import scan_for_default_filters

    result = scan_for_default_filters(
        "/role",
        exclude_paths=None,
        ignored_dirs=(".git", "__pycache__"),
        collect_task_files=lambda r, e: [],
        is_relpath_excluded=lambda rel, exc: False,
        is_path_excluded=lambda p, root, exc: False,
        scan_file_for_default_filters=mock_scan_file,
    )

    files = [r["file"] for r in result]
    assert files == sorted(files), "Results must be sorted by file then line_no"


# ---------------------------------------------------------------------------
# api.scan_for_default_filters — importable and callable
# ---------------------------------------------------------------------------


def test_api_scan_for_default_filters_importable_and_callable(fs):
    """api.scan_for_default_filters is importable, callable, and returns a list."""
    fs.create_dir("/role")

    import prism.api as api

    assert callable(api.scan_for_default_filters)
    result = api.scan_for_default_filters("/role")
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# api.scan_for_all_filters — importable and callable
# ---------------------------------------------------------------------------


def test_api_scan_for_all_filters_importable_and_callable(fs):
    """api.scan_for_all_filters is importable, callable, and returns a list."""
    fs.create_dir("/role")

    import prism.api as api

    assert callable(api.scan_for_all_filters)
    result = api.scan_for_all_filters("/role")
    assert isinstance(result, list)
