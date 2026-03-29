"""Style guide path resolution and configuration.

Provides functions for locating style guide sources and resolving section
metadata from configuration files.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def default_style_guide_user_paths(
    xdg_data_home_env: str = "XDG_DATA_HOME",
    style_guide_data_dirname: str = "prism",
    style_guide_source_filename: str = "STYLE_GUIDE_SOURCE.md",
) -> list[Path]:
    """Return user-level style guide paths honoring XDG conventions.

    Args:
        xdg_data_home_env: Environment variable name for XDG_DATA_HOME
        style_guide_data_dirname: Prism style guide directory name
        style_guide_source_filename: Style guide filename

    Returns:
        List of Path objects for user-level style guide candidates
    """
    xdg_data_home = os.environ.get(xdg_data_home_env)
    if xdg_data_home:
        data_home = Path(xdg_data_home).expanduser()
    else:
        data_home = (Path.home() / ".local" / "share").expanduser()
    return [
        data_home / style_guide_data_dirname / style_guide_source_filename,
    ]


def resolve_default_style_guide_source(
    explicit_path: str | None = None,
    env_style_guide_source_path: str = "PRISM_STYLE_SOURCE",
    xdg_data_home_env: str = "XDG_DATA_HOME",
    style_guide_data_dirname: str = "prism",
    style_guide_source_filename: str = "STYLE_GUIDE_SOURCE.md",
    system_style_guide_source_path: Path | None = None,
    default_style_guide_source_path: Path | None = None,
) -> str:
    r"""Resolve default style guide source path using Linux-aware precedence.

    Precedence (first existing path wins):
     1. ``$PRISM_STYLE_SOURCE``
        2. ``./STYLE_GUIDE_SOURCE.md``
        3. ``$XDG_DATA_HOME/prism/STYLE_GUIDE_SOURCE.md`` (or ``~/.local/share/...``)
        4. ``/var/lib/prism/STYLE_GUIDE_SOURCE.md``
        5. bundled package template path

    Args:
        explicit_path: Explicit path override (must be a file)
        env_style_guide_source_path: Env var name for primary style source
        xdg_data_home_env: Env var name for XDG_DATA_HOME
        style_guide_data_dirname: Prism style guide directory name
        style_guide_source_filename: Style guide filename
        system_style_guide_source_path: System path for style guide
        default_style_guide_source_path: Bundled default style guide path

    Returns:
        Resolved path to style guide source as string

    Raises:
        FileNotFoundError: If explicit_path is provided but does not exist
    """
    # Set defaults if not provided
    if system_style_guide_source_path is None:
        system_style_guide_source_path = (
            Path("/var/lib") / style_guide_data_dirname / style_guide_source_filename
        )
    if default_style_guide_source_path is None:
        default_style_guide_source_path = (
            Path(__file__).parent.parent / "templates" / style_guide_source_filename
        )

    if explicit_path:
        explicit_candidate = Path(explicit_path).expanduser()
        if explicit_candidate.is_file():
            return str(explicit_candidate.resolve())
        raise FileNotFoundError(f"style source path not found: {explicit_path}")

    candidates: list[Path] = []

    env_style_source = os.environ.get(env_style_guide_source_path)
    if env_style_source:
        candidates.append(Path(env_style_source).expanduser())

    candidates.append(Path.cwd() / style_guide_source_filename)
    candidates.extend(
        default_style_guide_user_paths(
            xdg_data_home_env=xdg_data_home_env,
            style_guide_data_dirname=style_guide_data_dirname,
            style_guide_source_filename=style_guide_source_filename,
        )
    )
    candidates.append(system_style_guide_source_path)
    candidates.append(default_style_guide_source_path)

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    return str(default_style_guide_source_path.resolve())


def resolve_section_selector(
    selector: str,
    all_section_ids: set[str],
    style_section_aliases: dict[str, str],
    normalize_heading_fn,
) -> str | None:
    """Resolve a section selector to a canonical section id.

    Args:
        selector: Section selector string to resolve
        all_section_ids: Set of valid section identifiers
        style_section_aliases: Mapping of aliases to canonical section ids
        normalize_heading_fn: Function to normalize heading strings

    Returns:
        Canonical section id or None if not found
    """
    value = selector.strip()
    if not value:
        return None
    if value in all_section_ids:
        return value
    normalized = normalize_heading_fn(value)
    if normalized in all_section_ids:
        return normalized
    return style_section_aliases.get(normalized)


def load_section_display_titles(display_titles_path: Path) -> dict[str, str]:
    """Load optional section display-title overrides from bundled data YAML.

    Args:
        display_titles_path: Path to section display titles YAML file

    Returns:
        Dictionary mapping section ids to display titles
    """
    if not display_titles_path.is_file():
        return {}
    try:
        raw = yaml.safe_load(display_titles_path.read_text(encoding="utf-8")) or {}
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


def refresh_policy(
    override_path: str | None = None,
) -> tuple[dict, dict, tuple, tuple, tuple, tuple, tuple, dict]:
    """Reload policy-derived globals and return their values.

    This function loads the pattern configuration and extracts policy-derived
    state that would normally be stored in scanner.py globals.

    Args:
        override_path: Optional explicit path to pattern config to load

    Returns:
        Tuple of (policy, section_aliases, secret_name_tokens, vault_markers,
                  credential_prefixes, url_prefixes, variable_guidance_keywords,
                  ignored_identifiers)
    """
    # Import here to avoid circular dependency
    from .patterns import load_pattern_config

    policy = load_pattern_config(override_path=override_path)
    section_aliases = policy["section_aliases"]
    sensitivity = policy["sensitivity"]
    secret_name_tokens = tuple(sensitivity["name_tokens"])
    vault_markers = tuple(sensitivity["vault_markers"])
    credential_prefixes = tuple(sensitivity["credential_prefixes"])
    url_prefixes = tuple(sensitivity["url_prefixes"])
    variable_guidance_keywords = tuple(policy["variable_guidance"]["priority_keywords"])
    ignored_identifiers = policy["ignored_identifiers"]

    return (
        policy,
        section_aliases,
        secret_name_tokens,
        vault_markers,
        credential_prefixes,
        url_prefixes,
        variable_guidance_keywords,
        ignored_identifiers,
    )


__all__ = [
    "default_style_guide_user_paths",
    "resolve_default_style_guide_source",
    "resolve_section_selector",
    "load_section_display_titles",
    "refresh_policy",
]
