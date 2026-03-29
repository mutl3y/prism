"""Pattern policy loader for prism.

Loads the built-in token lists and alias mappings from YAML files in ``data/``.
Supports override files and remote pattern repositories.
"""

from __future__ import annotations

import copy
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

# Directory containing the built-in per-topic YAML files shipped with the package
_BUILTIN_DATA_DIR = Path(__file__).parent.parent / "data"

# Override filename constants
REPO_OVERRIDE_FILENAME = ".prism_patterns.yml"
CWD_OVERRIDE_FILENAME = ".prism_patterns.yml"
ENV_PATTERNS_OVERRIDE_PATH = "PRISM_PATTERNS_PATH"

# System mutable-data locations
XDG_DATA_HOME_ENV = "XDG_DATA_HOME"
APP_DATA_DIRNAME = "prism"
SYSTEM_PATTERN_OVERRIDE_PATH = (
    Path("/var/lib") / APP_DATA_DIRNAME / CWD_OVERRIDE_FILENAME
)

# Default remote source (community-curated patterns repo)
DEFAULT_REMOTE_URL = (
    "https://raw.githubusercontent.com/mutl3y/prism_patterns" "/main/pattern_policy.yml"
)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict on any failure."""
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into a copy of *base*."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _normalise(policy: dict[str, Any]) -> dict[str, Any]:
    """Ensure expected keys exist and convert sets."""
    policy.setdefault("section_aliases", {})
    policy.setdefault("sensitivity", {})
    policy["sensitivity"].setdefault("name_tokens", [])
    policy["sensitivity"].setdefault("vault_markers", [])
    policy["sensitivity"].setdefault("credential_prefixes", [])
    policy["sensitivity"].setdefault("url_prefixes", [])
    policy.setdefault("variable_guidance", {})
    policy["variable_guidance"].setdefault("priority_keywords", [])
    policy.setdefault("ansible_builtin_variables", [])
    policy.setdefault("ignored_identifiers", [])
    policy["ansible_builtin_variables"] = set(policy["ansible_builtin_variables"])
    policy["ignored_identifiers"] = set(policy["ignored_identifiers"])
    return policy


def _load_builtin_policy() -> dict[str, Any]:
    """Load and merge all per-topic YAML files from the data directory."""
    policy: dict[str, Any] = {}
    for yml_file in sorted(_BUILTIN_DATA_DIR.glob("*.yml")):
        chunk = _load_yaml(yml_file)
        policy = _deep_merge(policy, chunk)
    return policy


def _default_user_data_home() -> Path:
    """Return the user data home path honoring ``XDG_DATA_HOME`` when set."""
    raw = os.environ.get(XDG_DATA_HOME_ENV)
    if raw:
        return Path(raw).expanduser()
    return (Path.home() / ".local" / "share").expanduser()


def _iter_default_override_paths() -> list[Path]:
    """Return default mutable override paths in merge order.

    Returned in low -> high precedence order (later ones override earlier ones).
    """
    paths = []

    # system-level mutable defaults (lowest precedence)
    paths.append(SYSTEM_PATTERN_OVERRIDE_PATH)

    # user-level mutable defaults (XDG)
    user_data_home = _default_user_data_home()
    paths.append(user_data_home / APP_DATA_DIRNAME / CWD_OVERRIDE_FILENAME)

    # repo-local/cwd override
    paths.append(Path.cwd() / CWD_OVERRIDE_FILENAME)

    # optional env var override (highest precedence among implicit defaults)
    env_override = os.environ.get(ENV_PATTERNS_OVERRIDE_PATH)
    if env_override:
        paths.append(Path(env_override).expanduser())

    return paths


def load_pattern_config(override_path: str | None = None) -> dict[str, Any]:
    """Load pattern configuration policy from built-in and override sources.

    Loads all built-in policy YAML files, then applies overrides in precedence
    order. Returns all state needed for pattern detection and policy queries.

    Parameters
    ----------
    override_path:
        Path to a YAML override file. Non-existent paths are ignored.

    Returns
    -------
    dict with keys:
        ``section_aliases``, ``sensitivity``, ``variable_guidance``,
        ``ansible_builtin_variables``, ``ignored_identifiers``
    """
    policy = _load_builtin_policy()

    for override_file in _iter_default_override_paths():
        if override_file.exists():
            override = _load_yaml(override_file)
            if override:
                policy = _deep_merge(policy, override)

    if override_path is not None:
        override_file = Path(override_path)
        if override_file.exists():
            override = _load_yaml(override_file)
            if override:
                policy = _deep_merge(policy, override)

    return _normalise(policy)


def fetch_remote_policy(
    url: str = DEFAULT_REMOTE_URL,
    cache_path: str | Path | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """Fetch a ``pattern_policy.yml`` from *url* and return the parsed policy.

    If *cache_path* is provided the raw YAML bytes are written there.

    Raises ``RuntimeError`` if the fetch fails and no cached copy exists.
    """
    raw_bytes: bytes | None = None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            raw_bytes = resp.read()
    except urllib.error.URLError as exc:
        if cache_path is None:
            raise RuntimeError(
                f"Failed to fetch remote patterns from {url}: {exc}"
            ) from exc

    if raw_bytes is not None and cache_path is not None:
        cache_file = Path(cache_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(raw_bytes)

    if raw_bytes is None:
        if cache_path is not None:
            cache_file = Path(cache_path)
            if cache_file.exists():
                raw_bytes = cache_file.read_bytes()
            else:
                raise RuntimeError(
                    f"Failed to fetch remote patterns from {url} and no cache found at {cache_path}"
                )

    try:
        data = yaml.safe_load(raw_bytes)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to parse remote pattern policy YAML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("Remote pattern policy YAML did not parse to a mapping")

    return _normalise(data)


def write_unknown_headings_log(
    unknown: dict[str, int],
    output_path: str | Path,
) -> None:
    """Write a JSON log of *unknown* heading counts to *output_path*."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"unknown_headings": unknown}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


__all__ = [
    "load_pattern_config",
    "fetch_remote_policy",
    "write_unknown_headings_log",
]
