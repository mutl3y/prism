"""Scanner data loading and file discovery helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, NamedTuple

from prism.scanner_io.loader import (
    _ordered_parallel_map,
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
    "RoleVariableMaps",
]


class RoleVariableMaps(NamedTuple):
    """Defaults/vars variable maps and their source-file lookup tables."""

    defaults_data: dict
    vars_data: dict
    defaults_sources: dict[str, Path]
    vars_sources: dict[str, Path]


def load_role_variable_maps(
    role_path: str,
    include_vars_main: bool,
    iter_variable_map_candidates_fn: Callable[[Path, str], list[Path]],
    load_yaml_file_fn: Callable[[Path], object],
) -> RoleVariableMaps:
    """Load defaults/vars variable maps from conventional role paths."""
    defaults_data: dict = {}
    vars_data: dict = {}
    defaults_sources: dict[str, Path] = {}
    vars_sources: dict[str, Path] = {}
    role_root = Path(role_path)
    default_candidates = iter_variable_map_candidates_fn(role_root, "defaults")

    for candidate, loaded in zip(
        default_candidates,
        _ordered_parallel_map(default_candidates, load_yaml_file_fn),
        strict=True,
    ):
        if isinstance(loaded, dict):
            for name in loaded:
                defaults_sources[name] = candidate
            defaults_data.update(loaded)

    if include_vars_main:
        vars_candidates = iter_variable_map_candidates_fn(role_root, "vars")
        for candidate, loaded in zip(
            vars_candidates,
            _ordered_parallel_map(vars_candidates, load_yaml_file_fn),
            strict=True,
        ):
            if isinstance(loaded, dict):
                for name in loaded:
                    vars_sources[name] = candidate
                vars_data.update(loaded)

    return RoleVariableMaps(defaults_data, vars_data, defaults_sources, vars_sources)


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
