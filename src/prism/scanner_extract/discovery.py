"""Role discovery and path-handling helpers for scanner orchestration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, NamedTuple

from prism.scanner_io.loader import load_yaml_file
from prism.scanner_io.loader import parse_yaml_candidate

logger = logging.getLogger(__name__)


class ScanIdentity(NamedTuple):
    role_root: Path
    meta: dict[str, Any]
    role_name: str
    description: str


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


def _record_warning(
    warning_collector: list[str] | None,
    *,
    code: str,
    path: Path,
    error: Exception | str,
) -> None:
    if warning_collector is None:
        return
    warning_collector.append(f"{code}: {path}: {error}")


def iter_role_variable_map_candidates(role_root: Path, subdir: str) -> list[Path]:
    """Return role variable map files in deterministic merge order."""
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
    di: object | None = None,
) -> dict:
    """Load the role metadata file meta/main.yml if present."""
    meta_file = Path(role_path) / "meta" / "main.yml"
    if meta_file.exists():
        role_root = Path(role_path).resolve()
        failure = parse_yaml_candidate(meta_file, role_root, di=di)
        if failure is not None:
            failure_error = str(failure.get("error", "")).strip() or "unknown"
            failure_line = failure.get("line")
            failure_column = failure.get("column")
            failure_detail = (
                f"{failure_error}"
                if failure_line is None
                else f"{failure_error} (line={failure_line}, column={failure_column})"
            )
            if str(failure_error).startswith("read_error:"):
                if strict:
                    raise RuntimeError(
                        f"{ROLE_METADATA_IO_ERROR}: {meta_file}: {failure_detail}"
                    )
                _record_metadata_warning(
                    warning_collector,
                    code=ROLE_METADATA_IO_ERROR,
                    meta_file=meta_file,
                    error=failure_detail,
                )
                return {}

            if strict:
                raise RuntimeError(
                    f"{ROLE_METADATA_YAML_INVALID}: {meta_file}: {failure_detail}"
                )
            logger.warning(
                "YAML parsing failed for %s: %s (non-strict mode: returning empty dict)",
                meta_file,
                failure_detail,
            )
            _record_metadata_warning(
                warning_collector,
                code=ROLE_METADATA_YAML_INVALID,
                meta_file=meta_file,
                error=failure_detail,
            )
            return {}

        try:
            _raw = load_yaml_file(meta_file, di=di)
            loaded = {} if _raw is None else _raw
        except Exception as exc:
            if strict:
                raise RuntimeError(
                    f"{ROLE_METADATA_IO_ERROR}: {meta_file}: {exc}"
                ) from exc
            logger.warning(
                "Failed to load %s: %s (type=%s, non-strict mode: returning empty dict)",
                meta_file,
                exc,
                type(exc).__name__,
            )
            _record_metadata_warning(
                warning_collector,
                code=ROLE_METADATA_IO_ERROR,
                meta_file=meta_file,
                error=exc,
            )
            return {}
        if not isinstance(loaded, dict):
            shape_error = "metadata root must be a mapping"
            if strict:
                raise RuntimeError(
                    f"{ROLE_METADATA_SHAPE_INVALID}: {meta_file}: {shape_error}"
                )
            logger.warning(
                "Invalid metadata shape for %s: %s (non-strict mode: returning empty dict)",
                meta_file,
                shape_error,
            )
            _record_metadata_warning(
                warning_collector,
                code=ROLE_METADATA_SHAPE_INVALID,
                meta_file=meta_file,
                error=shape_error,
            )
            return {}
        return loaded
    return {}


REQUIREMENTS_IO_ERROR = "REQUIREMENTS_IO_ERROR"
REQUIREMENTS_YAML_INVALID = "REQUIREMENTS_YAML_INVALID"


def load_requirements(
    role_path: str,
    *,
    strict: bool = False,
    warning_collector: list[str] | None = None,
    di: object | None = None,
) -> list:
    """Load meta/requirements.yml as a list, or return an empty list."""
    path = Path(role_path) / "meta" / "requirements.yml"
    if not path.exists():
        return []
    role_root = Path(role_path).resolve()
    failure = parse_yaml_candidate(path, role_root, di=di)
    if failure is not None:
        failure_error = str(failure.get("error", "")).strip() or "unknown"
        failure_line = failure.get("line")
        failure_column = failure.get("column")
        failure_detail = (
            f"{failure_error}"
            if failure_line is None
            else f"{failure_error} (line={failure_line}, column={failure_column})"
        )
        if str(failure_error).startswith("read_error:"):
            if strict:
                raise RuntimeError(f"{REQUIREMENTS_IO_ERROR}: {path}: {failure_detail}")
            logger.warning(
                "Failed to read requirements from %s: %s (non-strict mode: returning empty list)",
                path,
                failure_detail,
            )
            _record_warning(
                warning_collector,
                code=REQUIREMENTS_IO_ERROR,
                path=path,
                error=failure_detail,
            )
            return []

        if strict:
            raise RuntimeError(f"{REQUIREMENTS_YAML_INVALID}: {path}: {failure_detail}")
        logger.warning(
            "YAML parsing failed for requirements %s: %s (non-strict mode: returning empty list)",
            path,
            failure_detail,
        )
        _record_warning(
            warning_collector,
            code=REQUIREMENTS_YAML_INVALID,
            path=path,
            error=failure_detail,
        )
        return []
    try:
        payload = load_yaml_file(path, di=di)
    except Exception as exc:
        if strict:
            raise RuntimeError(f"{REQUIREMENTS_IO_ERROR}: {path}: {exc}") from exc
        logger.warning(
            "Failed to load requirements from %s: %s (type=%s, non-strict mode: returning empty list)",
            path,
            exc,
            type(exc).__name__,
        )
        _record_warning(
            warning_collector,
            code=REQUIREMENTS_IO_ERROR,
            path=path,
            error=exc,
        )
        return []
    if not isinstance(payload, list):
        msg = f"{REQUIREMENTS_YAML_INVALID}: {path}: root must be a list"
        if strict:
            raise RuntimeError(msg)
        logger.warning(
            "Invalid requirements shape for %s: root must be a list (non-strict mode: returning empty list)",
            path,
        )
        _record_warning(
            warning_collector,
            code=REQUIREMENTS_YAML_INVALID,
            path=path,
            error="root must be a list",
        )
        return []
    return payload


VARIABLE_FILE_IO_ERROR = "VARIABLE_FILE_IO_ERROR"


def load_variables(
    role_path: str,
    *,
    include_vars_main: bool = True,
    exclude_paths: list[str] | None = None,
    collect_include_vars_files: Callable[[str, list[str] | None], list[Path]],
    strict: bool = False,
    warning_collector: list[str] | None = None,
    di: object | None = None,
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
                data = load_yaml_file(path, di=di)
                if data is None:
                    data = {}
                if isinstance(data, dict):
                    vars_out.update(data)
            except Exception as exc:
                if strict:
                    raise RuntimeError(
                        f"{VARIABLE_FILE_IO_ERROR}: {path}: {exc}"
                    ) from exc
                logger.warning(
                    "Failed to load variable file %s: %s (type=%s, non-strict mode: skipping file)",
                    path,
                    exc,
                    type(exc).__name__,
                )
                if warning_collector is not None:
                    warning_collector.append(f"{VARIABLE_FILE_IO_ERROR}: {path}: {exc}")

    for extra_path in collect_include_vars_files(role_path, exclude_paths):
        try:
            data = load_yaml_file(extra_path, di=di)
            if data is None:
                data = {}
            if isinstance(data, dict):
                vars_out.update(data)
        except Exception as exc:
            if strict:
                raise RuntimeError(
                    f"{VARIABLE_FILE_IO_ERROR}: {extra_path}: {exc}"
                ) from exc
            logger.warning(
                "Failed to load include_vars file %s: %s (type=%s, non-strict mode: skipping file)",
                extra_path,
                exc,
                type(exc).__name__,
            )
            if warning_collector is not None:
                warning_collector.append(
                    f"{VARIABLE_FILE_IO_ERROR}: {extra_path}: {exc}"
                )

    return vars_out


def resolve_scan_identity(
    role_path: str,
    role_name_override: str | None,
    *,
    load_meta_fn: Callable[[str], dict[str, Any]],
) -> ScanIdentity:
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

    return ScanIdentity(role_root, meta, role_name, description)
