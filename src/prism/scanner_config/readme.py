"""README section configuration loading helpers.

Provides functions for resolving and loading README section configuration
from role-level YAML files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from .legacy_retirement import (
    LEGACY_SECTION_CONFIG_FILENAME,
    LEGACY_SECTION_CONFIG_UNSUPPORTED,
    LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE,
    format_legacy_retirement_error,
)
from .section import SECTION_CONFIG_FILENAME, SECTION_CONFIG_FILENAMES


def resolve_role_config_file(
    role_path: str,
    config_path: str | None = None,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> Path:
    """Resolve role config path from explicit or auto-discovered location."""
    if config_path:
        explicit_path = Path(config_path)
        if explicit_path.name == LEGACY_SECTION_CONFIG_FILENAME:
            raise RuntimeError(
                format_legacy_retirement_error(
                    LEGACY_SECTION_CONFIG_UNSUPPORTED,
                    LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE,
                )
            )
        return explicit_path
    role_root = Path(role_path)
    legacy_cfg = role_root / LEGACY_SECTION_CONFIG_FILENAME
    if legacy_cfg.is_file():
        raise RuntimeError(
            format_legacy_retirement_error(
                LEGACY_SECTION_CONFIG_UNSUPPORTED,
                LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE,
            )
        )
    for filename in config_filenames:
        candidate = role_root / filename
        if candidate.is_file():
            return candidate
    return role_root / default_filename


def _load_section_display_titles(path: Path) -> dict[str, str]:
    """Load optional section display-title overrides from bundled data YAML."""
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    payload = raw.get("display_titles")
    if not isinstance(payload, dict):
        return {}

    parsed: dict[str, str] = {}
    for section_id, display_title in payload.items():
        if not isinstance(section_id, str) or not isinstance(display_title, str):
            continue
        sid = section_id.strip()
        label = display_title.strip()
        if sid and label:
            parsed[sid] = label
    return parsed


def _resolve_section_selector(
    selector: str,
    all_section_ids: set[str],
    section_aliases: dict[str, str],
    normalize_heading: Callable[[str], str],
) -> str | None:
    """Resolve a section selector to a canonical section id."""
    value = selector.strip()
    if not value:
        return None
    if value in all_section_ids:
        return value
    normalized = normalize_heading(value)
    if normalized in all_section_ids:
        return normalized
    return section_aliases.get(normalized)


def load_readme_section_config(
    role_path: str,
    config_path: str | None,
    adopt_heading_mode: str | None,
    all_section_ids: set[str],
    section_aliases: dict[str, str],
    normalize_heading: Callable[[str], str],
    display_titles_path: Path,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> dict | None:
    """Load README section visibility and rendering controls from role config."""
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
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None

    readme_cfg = raw.get("readme", raw)
    if not isinstance(readme_cfg, dict):
        return None

    include_raw = readme_cfg.get("include_sections")
    exclude_raw = readme_cfg.get("exclude_sections")
    content_modes_raw = readme_cfg.get("section_content_modes")
    config_adopt_heading_mode = readme_cfg.get("adopt_heading_mode")
    if include_raw is None and exclude_raw is None and content_modes_raw is None:
        return None

    if adopt_heading_mode is None and isinstance(config_adopt_heading_mode, str):
        adopt_heading_mode = config_adopt_heading_mode.strip().lower()
    if adopt_heading_mode is None:
        adopt_heading_mode = "canonical"
    if adopt_heading_mode not in {"canonical", "style", "popular"}:
        adopt_heading_mode = "canonical"

    include_items = include_raw if isinstance(include_raw, list) else None
    exclude_items = exclude_raw if isinstance(exclude_raw, list) else []
    content_modes_items = (
        content_modes_raw if isinstance(content_modes_raw, dict) else {}
    )

    title_overrides: dict[str, str] = {}
    display_titles = _load_section_display_titles(display_titles_path)
    section_content_modes: dict[str, str] = {}
    include_selector_map: dict[str, str] = {}

    if include_items is None:
        enabled: set[str] = set(all_section_ids)
    else:
        enabled = set()
        for item in include_items:
            if not isinstance(item, str):
                continue
            resolved = _resolve_section_selector(
                item,
                all_section_ids=all_section_ids,
                section_aliases=section_aliases,
                normalize_heading=normalize_heading,
            )
            if not resolved:
                continue
            enabled.add(resolved)
            normalized_item = normalize_heading(item)
            if normalized_item:
                include_selector_map[normalized_item] = resolved
            if adopt_heading_mode == "style":
                title_overrides[resolved] = item.strip()

    for item in exclude_items:
        if not isinstance(item, str):
            continue
        resolved = _resolve_section_selector(
            item,
            all_section_ids=all_section_ids,
            section_aliases=section_aliases,
            normalize_heading=normalize_heading,
        )
        if resolved:
            enabled.discard(resolved)

    if adopt_heading_mode == "popular":
        for section_id in enabled:
            display_title = display_titles.get(section_id)
            if display_title:
                title_overrides[section_id] = display_title

    for selector, mode in content_modes_items.items():
        if not isinstance(selector, str) or not isinstance(mode, str):
            continue
        normalized_selector = normalize_heading(selector)
        resolved = include_selector_map.get(normalized_selector)
        if not resolved:
            resolved = _resolve_section_selector(
                selector,
                all_section_ids=all_section_ids,
                section_aliases=section_aliases,
                normalize_heading=normalize_heading,
            )
        if not resolved:
            continue
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"generate", "replace", "merge"}:
            continue
        section_content_modes[resolved] = normalized_mode

    return {
        "enabled_sections": enabled,
        "section_title_overrides": title_overrides,
        "adopt_heading_mode": adopt_heading_mode,
        "section_content_modes": section_content_modes,
    }


def load_readme_section_visibility(
    role_path: str,
    config_path: str | None,
    adopt_heading_mode: str | None,
    all_section_ids: set[str],
    section_aliases: dict[str, str],
    normalize_heading: Callable[[str], str],
    display_titles_path: Path,
    config_filenames: tuple[str, ...] = SECTION_CONFIG_FILENAMES,
    default_filename: str = SECTION_CONFIG_FILENAME,
) -> set[str] | None:
    """Return enabled section ids from README config, if configured."""
    config = load_readme_section_config(
        role_path=role_path,
        config_path=config_path,
        adopt_heading_mode=adopt_heading_mode,
        all_section_ids=all_section_ids,
        section_aliases=section_aliases,
        normalize_heading=normalize_heading,
        display_titles_path=display_titles_path,
        config_filenames=config_filenames,
        default_filename=default_filename,
    )
    if config is None:
        return None
    return config["enabled_sections"]


__all__ = [
    "resolve_role_config_file",
    "load_readme_section_config",
    "load_readme_section_visibility",
]
