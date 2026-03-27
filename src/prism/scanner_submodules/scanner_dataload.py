"""Scanner data loading and file discovery helpers.

This module contains data loading, YAML parsing, and file discovery functions
extracted from scanner.py for improved maintainability and testability.
"""

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


def load_role_variable_maps(
    role_path: str,
    include_vars_main: bool,
    iter_variable_map_candidates_fn: Callable[[Path, str], list[Path]],
    load_yaml_file_fn: Callable[[Path], object],
) -> tuple[dict, dict, dict[str, Path], dict[str, Path]]:
    """Load defaults/vars variable maps from conventional role paths.

    Args:
        role_path: Path to role directory
        include_vars_main: Whether to include vars/main.yml in addition to defaults
        iter_variable_map_candidates_fn: Function to find variable map files
        load_yaml_file_fn: Function to load and parse YAML files

    Returns:
        Tuple of (defaults_data, vars_data, defaults_sources, vars_sources)
        where sources track which file each variable came from
    """
    defaults_data: dict = {}
    vars_data: dict = {}
    defaults_sources: dict[str, Path] = {}
    vars_sources: dict[str, Path] = {}
    role_root = Path(role_path)

    for candidate in iter_variable_map_candidates_fn(role_root, "defaults"):
        loaded = load_yaml_file_fn(candidate)
        if isinstance(loaded, dict):
            for name in loaded:
                defaults_sources[name] = candidate
            defaults_data.update(loaded)

    if include_vars_main:
        for candidate in iter_variable_map_candidates_fn(role_root, "vars"):
            loaded = load_yaml_file_fn(candidate)
            if isinstance(loaded, dict):
                for name in loaded:
                    vars_sources[name] = candidate
                vars_data.update(loaded)

    return defaults_data, vars_data, defaults_sources, vars_sources


def iter_role_argument_spec_entries(
    role_path: str,
    load_yaml_file_fn: Callable[[Path], object],
    load_meta_fn: Callable[[str], dict],
):
    """Yield argument spec variable entries discovered in role metadata files.

    Supported layouts:
    - ``meta/argument_specs.yml`` with top-level ``argument_specs`` mapping
    - ``meta/main.yml`` with embedded ``argument_specs`` mapping

    Args:
        role_path: Path to role directory
        load_yaml_file_fn: Function to load and parse YAML files
        load_meta_fn: Function to load role meta/main.yml

    Yields:
        Tuples of (source_file, var_name, spec_dict)
    """
    role_root = Path(role_path)
    arg_specs_file = role_root / "meta" / "argument_specs.yml"
    sources: list[tuple[str, dict]] = []

    if arg_specs_file.is_file():
        loaded = load_yaml_file_fn(arg_specs_file)
        if isinstance(loaded, dict):
            sources.append(("meta/argument_specs.yml", loaded))

    meta_main = load_meta_fn(role_path)
    if isinstance(meta_main, dict):
        sources.append(("meta/main.yml", meta_main))

    for source_file, payload in sources:
        argument_specs = payload.get("argument_specs")
        if not isinstance(argument_specs, dict):
            continue
        for task_spec in argument_specs.values():
            if not isinstance(task_spec, dict):
                continue
            options = task_spec.get("options")
            if not isinstance(options, dict):
                continue
            for var_name, spec in options.items():
                if not isinstance(var_name, str) or not isinstance(spec, dict):
                    continue
                if "{{" in var_name or "{%" in var_name:
                    continue
                yield source_file, var_name, spec
