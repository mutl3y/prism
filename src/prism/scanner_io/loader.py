"""YAML loading and file discovery helpers for scanner I/O."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import yaml


def iter_role_yaml_candidates(
    role_root: Path,
    *,
    exclude_paths: list[str] | None,
    ignored_dirs: set[str],
    is_relpath_excluded_fn: Callable[[str, list[str] | None], bool],
    is_path_excluded_fn: Callable[[Path, Path, list[str] | None], bool],
):
    """Yield role-local YAML files while honoring ignored and excluded paths.

    Args:
        role_root: Role root directory path
        exclude_paths: List of path patterns to exclude
        ignored_dirs: Set of directory names to skip
        is_relpath_excluded_fn: Function to check if relative path is excluded
        is_path_excluded_fn: Function to check if absolute path is excluded

    Yields:
        Path objects for each YAML candidate file
    """
    for root, dirs, files in os.walk(str(role_root)):
        dirs[:] = [
            d
            for d in dirs
            if d not in ignored_dirs
            and not is_relpath_excluded_fn(
                str((Path(root) / d).resolve().relative_to(role_root)),
                exclude_paths,
            )
        ]
        for fname in sorted(files):
            candidate = Path(root) / fname
            if candidate.suffix.lower() not in {".yml", ".yaml"}:
                continue
            if is_path_excluded_fn(candidate, role_root, exclude_paths):
                continue
            yield candidate


def parse_yaml_candidate(candidate: Path, role_root: Path) -> dict[str, object] | None:
    """Parse one YAML candidate and return a failure payload when parsing fails.

    Args:
        candidate: Path to YAML file to parse
        role_root: Role root directory (for relative path calculation)

    Returns:
        None if parsing succeeds, dict with error details if parsing fails
    """
    try:
        text = candidate.read_text(encoding="utf-8")
        yaml.safe_load(text)
        return None
    except (OSError, UnicodeDecodeError) as exc:
        return {
            "file": str(candidate.resolve().relative_to(role_root)),
            "line": None,
            "column": None,
            "error": f"read_error: {exc}",
        }
    except (yaml.YAMLError, ValueError) as exc:
        mark = getattr(exc, "problem_mark", None)
        line = int(mark.line) + 1 if mark is not None else None
        column = int(mark.column) + 1 if mark is not None else None
        problem = str(getattr(exc, "problem", "") or "").strip()
        if not problem:
            problem = str(exc).splitlines()[0].strip()
        return {
            "file": str(candidate.resolve().relative_to(role_root)),
            "line": line,
            "column": column,
            "error": problem,
        }


def map_argument_spec_type(spec_type: object) -> str:
    """Map argument-spec type labels into scanner variable type labels.

    Args:
        spec_type: Type specification from argument_specs YAML

    Returns:
        Normalized type label for scanner variable classification
    """
    if not isinstance(spec_type, str):
        return "documented"
    normalized = spec_type.strip().lower()
    if normalized in {"str", "raw", "path", "bytes", "bits"}:
        return "string"
    if normalized in {"int"}:
        return "int"
    if normalized in {"bool"}:
        return "bool"
    if normalized in {"dict"}:
        return "dict"
    if normalized in {"list"}:
        return "list"
    if normalized in {"float"}:
        return "string"
    return "documented"


def collect_yaml_parse_failures(
    role_path: str,
    exclude_paths: list[str] | None,
    iter_yaml_candidates_fn: Callable[[Path, list[str] | None], list[Path]],
) -> list[dict[str, object]]:
    """Collect YAML parse failures with file/line context across a role tree.

    Args:
        role_path: Path to role directory
        exclude_paths: List of path patterns to exclude
        iter_yaml_candidates_fn: Function to find YAML candidates

    Returns:
        List of error dictionaries, one per parsing failure
    """
    role_root = Path(role_path).resolve()
    failures: list[dict[str, object]] = []

    for candidate in iter_yaml_candidates_fn(
        role_root,
        exclude_paths,
    ):
        failure = parse_yaml_candidate(candidate, role_root)
        if failure is not None:
            failures.append(failure)

    return failures


def load_yaml_file(path: Path) -> object:
    """Load and parse a YAML file safely.

    Args:
        path: Path to YAML file

    Returns:
        Parsed YAML content (dict, list, or None on empty file)
    """
    try:
        text = path.read_text(encoding="utf-8")
        return yaml.safe_load(text)
    except Exception:
        return None
