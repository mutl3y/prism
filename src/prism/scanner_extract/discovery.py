"""Role discovery and path-handling helpers for scanner orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml


ROLE_METADATA_YAML_INVALID = "ROLE_METADATA_YAML_INVALID"
ROLE_METADATA_IO_ERROR = "ROLE_METADATA_IO_ERROR"
ROLE_METADATA_SHAPE_INVALID = "ROLE_METADATA_SHAPE_INVALID"


def _record_metadata_warning(
    warning_collector: list[str] | None,
    *,
    code: str,
    meta_file: Path,
    error: Exception | str,
) -> None:
    if warning_collector is None:
        return
    warning_collector.append(f"{code}: {meta_file}: {error}")


def iter_role_variable_map_candidates(role_root: Path, subdir: str) -> list[Path]:
    """Return role variable map files in deterministic merge order.

    Order is:
    1) ``<subdir>/main.yml`` then ``<subdir>/main.yaml`` fallback
    2) sorted fragments under ``<subdir>/main/*.yml`` then ``*.yaml``
    """
    candidates: list[Path] = []

    main_yml = role_root / subdir / "main.yml"
    main_yaml = role_root / subdir / "main.yaml"
    if main_yml.exists():
        candidates.append(main_yml)
    elif main_yaml.exists():
        candidates.append(main_yaml)

    fragment_dir = role_root / subdir / "main"
    if fragment_dir.is_dir():
        candidates.extend(sorted(fragment_dir.glob("*.yml")))
        candidates.extend(sorted(fragment_dir.glob("*.yaml")))

    return candidates


def load_meta(
    role_path: str,
    *,
    strict: bool = False,
    warning_collector: list[str] | None = None,
) -> dict:
    """Load the role metadata file ``meta/main.yml`` if present.

    Returns a mapping (empty if missing or unparsable).
    """
    meta_file = Path(role_path) / "meta" / "main.yml"
    if meta_file.exists():
        try:
            loaded = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            if strict:
                raise RuntimeError(
                    f"{ROLE_METADATA_YAML_INVALID}: {meta_file}: {exc}"
                ) from exc
            _record_metadata_warning(
                warning_collector,
                code=ROLE_METADATA_YAML_INVALID,
                meta_file=meta_file,
                error=exc,
            )
            return {}
        except (OSError, UnicodeDecodeError) as exc:
            if strict:
                raise RuntimeError(
                    f"{ROLE_METADATA_IO_ERROR}: {meta_file}: {exc}"
                ) from exc
            _record_metadata_warning(
                warning_collector,
                code=ROLE_METADATA_IO_ERROR,
                meta_file=meta_file,
                error=exc,
            )
            return {}
        if not isinstance(loaded, dict):
            _record_metadata_warning(
                warning_collector,
                code=ROLE_METADATA_SHAPE_INVALID,
                meta_file=meta_file,
                error="metadata root must be a mapping",
            )
            return {}
        return loaded
    return {}


def load_requirements(role_path: str) -> list:
    """Load ``meta/requirements.yml`` as a list, or return an empty list."""
    path = Path(role_path) / "meta" / "requirements.yml"
    if path.exists():
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
            return []
    return []


def load_variables(
    role_path: str,
    *,
    include_vars_main: bool = True,
    exclude_paths: list[str] | None = None,
    collect_include_vars_files: Callable[[str, list[str] | None], list[Path]],
) -> dict:
    """Load role variables from defaults/vars and static include_vars targets."""
    vars_out: dict = {}
    role_root = Path(role_path)
    subdirs = ["defaults"]
    if include_vars_main:
        subdirs.append("vars")

    for sub in subdirs:
        for path in iter_role_variable_map_candidates(role_root, sub):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    vars_out.update(data)
            except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
                continue

    for extra_path in collect_include_vars_files(role_path, exclude_paths):
        try:
            data = yaml.safe_load(extra_path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                vars_out.update(data)
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
            continue

    return vars_out


def resolve_scan_identity(
    role_path: str,
    role_name_override: str | None,
    *,
    load_meta_fn: Callable[[str], dict],
) -> tuple[Path, dict, str, str]:
    """Resolve role path, metadata, role name, and description."""
    role_root = Path(role_path)
    if not role_root.is_dir():
        raise FileNotFoundError(f"role path not found: {role_path}")

    meta = load_meta_fn(role_path)
    galaxy = meta.get("galaxy_info", {}) if isinstance(meta, dict) else {}
    role_name = galaxy.get("role_name", role_root.name)
    if role_name_override and (not galaxy.get("role_name") or role_name == "repo"):
        role_name = role_name_override
    description = galaxy.get("description", "")

    return role_root, meta, role_name, description
