"""Scan policy configuration loaders.

Provides functions for loading scan-time toggle flags from role configuration.
"""

from __future__ import annotations


import yaml

from .section import SECTION_CONFIG_FILENAME, SECTION_CONFIG_FILENAMES
from .readme import resolve_role_config_file


def _coerce_bool(value: object) -> bool | None:
    """Return a normalized bool for common YAML-friendly truthy/falsey values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return None


def _coerce_positive_int(value: object) -> int | None:
    """Return a positive integer for integer-like values, otherwise None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = int(text)
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None


def load_fail_on_unconstrained_dynamic_includes(
    role_path: str,
    config_path: str | None = None,
    default: bool = False,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> bool:
    """Load scan policy toggle for unconstrained dynamic include failures."""
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return default

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default

    value: object | None = None
    scan_cfg = raw.get("scan")
    if isinstance(scan_cfg, dict):
        value = scan_cfg.get("fail_on_unconstrained_dynamic_includes")
    if value is None:
        value = raw.get("fail_on_unconstrained_dynamic_includes")

    coerced = _coerce_bool(value)
    if coerced is None:
        return default
    return coerced


def load_fail_on_yaml_like_task_annotations(
    role_path: str,
    config_path: str | None = None,
    default: bool = False,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> bool:
    """Load scan policy toggle for YAML-like task annotation strict failures."""
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return default

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default

    value: object | None = None
    scan_cfg = raw.get("scan")
    if isinstance(scan_cfg, dict):
        value = scan_cfg.get("fail_on_yaml_like_task_annotations")
    if value is None:
        value = raw.get("fail_on_yaml_like_task_annotations")

    coerced = _coerce_bool(value)
    if coerced is None:
        return default
    return coerced


def load_ignore_unresolved_internal_underscore_references(
    role_path: str,
    config_path: str | None = None,
    default: bool = True,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> bool:
    """Load unresolved underscore-reference suppression toggle."""
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return default

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default

    value: object | None = None
    scan_cfg = raw.get("scan")
    if isinstance(scan_cfg, dict):
        value = scan_cfg.get("ignore_unresolved_internal_underscore_references")
    if value is None:
        value = raw.get("ignore_unresolved_internal_underscore_references")

    coerced = _coerce_bool(value)
    if coerced is None:
        return default
    return coerced


def load_non_authoritative_test_evidence_max_file_bytes(
    role_path: str,
    config_path: str | None = None,
    default: int = 512 * 1024,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> int:
    """Load max bytes per evidence file for tests/molecule evidence scanning."""
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return default

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default

    value: object | None = None
    scan_cfg = raw.get("scan")
    if isinstance(scan_cfg, dict):
        value = scan_cfg.get("non_authoritative_test_evidence_max_file_bytes")
    if value is None:
        value = raw.get("non_authoritative_test_evidence_max_file_bytes")

    coerced = _coerce_positive_int(value)
    if coerced is None:
        return default
    return coerced


def load_non_authoritative_test_evidence_max_files_scanned(
    role_path: str,
    config_path: str | None = None,
    default: int = 400,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> int:
    """Load max number of files scanned for tests/molecule evidence."""
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return default

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default

    value: object | None = None
    scan_cfg = raw.get("scan")
    if isinstance(scan_cfg, dict):
        value = scan_cfg.get("non_authoritative_test_evidence_max_files_scanned")
    if value is None:
        value = raw.get("non_authoritative_test_evidence_max_files_scanned")

    coerced = _coerce_positive_int(value)
    if coerced is None:
        return default
    return coerced


def load_non_authoritative_test_evidence_max_total_bytes(
    role_path: str,
    config_path: str | None = None,
    default: int = 8 * 1024 * 1024,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> int:
    """Load max aggregate bytes scanned for tests/molecule evidence."""
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return default

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default

    value: object | None = None
    scan_cfg = raw.get("scan")
    if isinstance(scan_cfg, dict):
        value = scan_cfg.get("non_authoritative_test_evidence_max_total_bytes")
    if value is None:
        value = raw.get("non_authoritative_test_evidence_max_total_bytes")

    coerced = _coerce_positive_int(value)
    if coerced is None:
        return default
    return coerced


__all__ = [
    "load_fail_on_unconstrained_dynamic_includes",
    "load_fail_on_yaml_like_task_annotations",
    "load_ignore_unresolved_internal_underscore_references",
    "load_non_authoritative_test_evidence_max_file_bytes",
    "load_non_authoritative_test_evidence_max_files_scanned",
    "load_non_authoritative_test_evidence_max_total_bytes",
]
