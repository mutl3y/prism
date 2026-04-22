"""Marker configuration loading."""

from __future__ import annotations

import re

import yaml

from prism.scanner_config.section import (
    DEFAULT_DOC_MARKER_PREFIX,
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
)
from prism.scanner_config.readme import resolve_role_config_file


README_MARKER_CONFIG_YAML_INVALID = "README_MARKER_CONFIG_YAML_INVALID"
README_MARKER_CONFIG_IO_ERROR = "README_MARKER_CONFIG_IO_ERROR"
README_MARKER_CONFIG_SHAPE_INVALID = "README_MARKER_CONFIG_SHAPE_INVALID"


def _record_marker_config_warning(
    warning_collector: list[str] | None,
    *,
    code: str,
    cfg_file: object,
    error: Exception | str,
) -> None:
    if warning_collector is None:
        return
    warning_collector.append(f"{code}: {cfg_file}: {error}")


def load_readme_marker_prefix(
    role_path: str,
    config_path: str | None = None,
    default_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
    warning_collector: list[str] | None = None,
) -> str:
    """Load marker prefix from role config with strict fallback behavior."""
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return default_prefix

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        _record_marker_config_warning(
            warning_collector,
            code=README_MARKER_CONFIG_YAML_INVALID,
            cfg_file=cfg_file,
            error=exc,
        )
        return default_prefix
    except (OSError, UnicodeDecodeError) as exc:
        _record_marker_config_warning(
            warning_collector,
            code=README_MARKER_CONFIG_IO_ERROR,
            cfg_file=cfg_file,
            error=exc,
        )
        return default_prefix
    if not isinstance(raw, dict):
        _record_marker_config_warning(
            warning_collector,
            code=README_MARKER_CONFIG_SHAPE_INVALID,
            cfg_file=cfg_file,
            error="config root must be a mapping",
        )
        return default_prefix

    marker_cfg = raw.get("markers")
    if marker_cfg is None and isinstance(raw.get("readme"), dict):
        marker_cfg = raw["readme"].get("markers")
    if marker_cfg is None:
        return default_prefix
    if not isinstance(marker_cfg, dict):
        _record_marker_config_warning(
            warning_collector,
            code=README_MARKER_CONFIG_SHAPE_INVALID,
            cfg_file=cfg_file,
            error="markers config must be a mapping",
        )
        return default_prefix

    prefix = marker_cfg.get("prefix")
    if not isinstance(prefix, str):
        _record_marker_config_warning(
            warning_collector,
            code=README_MARKER_CONFIG_SHAPE_INVALID,
            cfg_file=cfg_file,
            error="markers.prefix must be a non-empty string",
        )
        return default_prefix
    prefix = prefix.strip()
    if not prefix:
        _record_marker_config_warning(
            warning_collector,
            code=README_MARKER_CONFIG_SHAPE_INVALID,
            cfg_file=cfg_file,
            error="markers.prefix must be a non-empty string",
        )
        return default_prefix
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        _record_marker_config_warning(
            warning_collector,
            code=README_MARKER_CONFIG_SHAPE_INVALID,
            cfg_file=cfg_file,
            error="markers.prefix contains unsupported characters",
        )
        return default_prefix
    return prefix


__all__ = [
    "load_readme_marker_prefix",
]
