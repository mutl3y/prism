"""Scanner data loading and file discovery helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from prism.scanner_io.loader import (
    collect_yaml_parse_failures,
    iter_role_yaml_candidates,
    map_argument_spec_type,
    parse_yaml_candidate,
)

__all__ = [
    "collect_yaml_parse_failures",
    "iter_role_yaml_candidates",
    "map_argument_spec_type",
    "parse_yaml_candidate",
    "load_role_variable_maps",
    "iter_role_argument_spec_entries",
]


def load_role_variable_maps(
    role_path: str,
    include_vars_main: bool,
    iter_variable_map_candidates_fn: Callable[[Path, str], list[Path]],
    load_yaml_file_fn: Callable[[Path], object],
) -> tuple[dict, dict, dict[str, Path], dict[str, Path]]:
    """Load defaults/vars variable maps from conventional role paths."""
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
    """Yield argument spec variable entries discovered in role metadata files."""
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
