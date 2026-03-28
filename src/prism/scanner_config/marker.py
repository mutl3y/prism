"""Marker configuration loading.

Provides functions for loading marker/prefix configuration from role files.
"""

from __future__ import annotations

import re

import yaml

from .section import (
    DEFAULT_DOC_MARKER_PREFIX,
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
)
from .readme import resolve_role_config_file


def load_readme_marker_prefix(
    role_path: str,
    config_path: str | None = None,
    default_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
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
    except Exception:
        return default_prefix
    if not isinstance(raw, dict):
        return default_prefix

    marker_cfg = raw.get("markers")
    if marker_cfg is None and isinstance(raw.get("readme"), dict):
        marker_cfg = raw["readme"].get("markers")
    if not isinstance(marker_cfg, dict):
        return default_prefix

    prefix = marker_cfg.get("prefix")
    if not isinstance(prefix, str):
        return default_prefix
    prefix = prefix.strip()
    if not prefix:
        return default_prefix
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        return default_prefix
    return prefix


__all__ = [
    "load_readme_marker_prefix",
]
