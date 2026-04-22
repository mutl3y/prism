"""Scan policy configuration loaders."""

from __future__ import annotations

import yaml

from prism.scanner_config.section import (
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
)
from prism.scanner_config.readme import resolve_role_config_file

POLICY_CONFIG_YAML_INVALID = "POLICY_CONFIG_YAML_INVALID"
_POLICY_CONFIG_YAML_INVALID_MESSAGE = "policy config YAML is invalid"


def _load_policy_config_dict(
    role_path: str,
    config_path: str | None,
    config_filenames: tuple[str, ...],
    default_filename: str,
) -> dict | None:
    """Load parsed policy config dict or return None when no config exists.

    Raises RuntimeError with a stable public code when YAML parsing fails.
    """
    cfg_file = resolve_role_config_file(
        role_path,
        config_path=config_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if not cfg_file.is_file():
        return None

    try:
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"{POLICY_CONFIG_YAML_INVALID}: {_POLICY_CONFIG_YAML_INVALID_MESSAGE}: {cfg_file}"
        ) from exc

    if not isinstance(raw, dict):
        return {}
    return raw


def _coerce_bool(value: object) -> bool | None:
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
    raw = _load_policy_config_dict(
        role_path,
        config_path,
        config_filenames,
        default_filename,
    )
    if raw is None:
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
    raw = _load_policy_config_dict(
        role_path,
        config_path,
        config_filenames,
        default_filename,
    )
    if raw is None:
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
    raw = _load_policy_config_dict(
        role_path,
        config_path,
        config_filenames,
        default_filename,
    )
    if raw is None:
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
    raw = _load_policy_config_dict(
        role_path,
        config_path,
        config_filenames,
        default_filename,
    )
    if raw is None:
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


def load_policy_rules_from_config(
    role_path: str,
    config_path: str | None = None,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> list[dict]:
    """Load policy_rules entries from the role's .prism.yml.

    Returns a list of raw rule dicts from the 'policy_rules' key.
    Returns empty list if no config or no policy_rules key present.
    """
    raw = _load_policy_config_dict(
        role_path, config_path, config_filenames, default_filename
    )
    if not raw:
        return []
    policy_rules = raw.get("policy_rules")
    if not isinstance(policy_rules, list):
        return []
    return [r for r in policy_rules if isinstance(r, dict)]
