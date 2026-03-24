"""Pattern policy loader for prism.

Loads the built-in token lists and alias mappings from the YAML files in
``data/``.  Each file contributes its top-level keys to the policy dict
and is loaded in filename order so the merge is deterministic:

* ``data/ignored_identifiers.yml``
* ``data/section_aliases.yml``
* ``data/sensitivity.yml``
* ``data/variable_guidance.yml``
* ``data/ansible_builtin_variables.yml``

Typical usage in scanner.py::

    from .pattern_config import load_pattern_config
    _POLICY = load_pattern_config()
    STYLE_SECTION_ALIASES = _POLICY["section_aliases"]

Override file (e.g. ``.prism_patterns.yml`` in the role repo)
should be a YAML file with the same top-level keys as the above files.
Only the keys you include are replaced; omitted keys keep the built-in value.
Dicts are merged recursively; lists replace wholesale (no partial merge).

Remote patterns repo
--------------------
When internet access is available the ``fetch_remote_policy`` helper can
pull a merged ``pattern_policy.yml`` from a remote URL (e.g. the raw
GitHub URL of ``prism_patterns``) and cache it locally.  This
is intentionally *not* called automatically at scan time; invoke it
explicitly via ``prism update-patterns``.
"""

from __future__ import annotations

import copy
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

import yaml

# Directory containing the built-in per-topic YAML files shipped with the package
_BUILTIN_DATA_DIR = Path(__file__).parent / "data"

# Default name for a repo-level override sitting next to the role being scanned
REPO_OVERRIDE_FILENAME = ".prism_patterns.yml"
LEGACY_REPO_OVERRIDE_FILENAME = ".ansible_role_doc_patterns.yml"

# Optional current-working-directory override name
CWD_OVERRIDE_FILENAME = ".prism_patterns.yml"
LEGACY_CWD_OVERRIDE_FILENAME = ".ansible_role_doc_patterns.yml"

# Optional environment-variable override file path
ENV_PATTERNS_OVERRIDE_PATH = "PRISM_PATTERNS_PATH"
LEGACY_ENV_PATTERNS_OVERRIDE_PATH = "ANSIBLE_ROLE_DOC_PATTERNS_PATH"

# Linux user/system mutable-data locations
XDG_DATA_HOME_ENV = "XDG_DATA_HOME"
APP_DATA_DIRNAME = "prism"
LEGACY_APP_DATA_DIRNAME = "ansible_role_doc"
SYSTEM_PATTERN_OVERRIDE_PATH = (
    Path("/var/lib") / APP_DATA_DIRNAME / CWD_OVERRIDE_FILENAME
)
LEGACY_SYSTEM_PATTERN_OVERRIDE_PATH = (
    Path("/var/lib") / LEGACY_APP_DATA_DIRNAME / LEGACY_CWD_OVERRIDE_FILENAME
)

# Default remote source (community-curated patterns repo)
DEFAULT_REMOTE_URL = (
    "https://raw.githubusercontent.com/mutl3y/prism_patterns" "/main/pattern_policy.yml"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict on any failure."""
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into a copy of *base*.

    - Dicts are merged recursively.
    - All other types (lists, scalars) are replaced wholesale by the override
      value.  This means a list in the override fully replaces the base list
      rather than extending it.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _normalise(policy: dict[str, Any]) -> dict[str, Any]:
    """Ensure expected keys exist and convert ``ignored_identifiers`` to a set."""
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
    # Return a mutable set so callers can use ``in`` without converting
    policy["ansible_builtin_variables"] = set(policy["ansible_builtin_variables"])
    policy["ignored_identifiers"] = set(policy["ignored_identifiers"])
    return policy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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

    Returned order is low -> high precedence.
    """
    candidates: list[Path] = []

    # system-level mutable defaults
    candidates.append(SYSTEM_PATTERN_OVERRIDE_PATH)
    candidates.append(LEGACY_SYSTEM_PATTERN_OVERRIDE_PATH)

    # user-level mutable defaults (XDG)
    user_data_home = _default_user_data_home()
    candidates.append(user_data_home / APP_DATA_DIRNAME / CWD_OVERRIDE_FILENAME)
    candidates.append(
        user_data_home / LEGACY_APP_DATA_DIRNAME / LEGACY_CWD_OVERRIDE_FILENAME
    )

    # repo-local/cwd override
    candidates.append(Path.cwd() / CWD_OVERRIDE_FILENAME)
    candidates.append(Path.cwd() / LEGACY_CWD_OVERRIDE_FILENAME)

    # optional env var override (highest among implicit defaults)
    env_override_raw = os.environ.get(ENV_PATTERNS_OVERRIDE_PATH)
    if env_override_raw:
        candidates.append(Path(env_override_raw).expanduser())

    legacy_env_override_raw = os.environ.get(LEGACY_ENV_PATTERNS_OVERRIDE_PATH)
    if legacy_env_override_raw:
        candidates.append(Path(legacy_env_override_raw).expanduser())

    return candidates


def load_pattern_config(
    override_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return the merged pattern policy.

    Load order (later wins):

    1. Built-in per-topic YAML files from ``data/`` (always present, ship with package)
     2. ``/var/lib/prism/.prism_patterns.yml`` (system mutable data)
     3. ``/var/lib/ansible_role_doc/.ansible_role_doc_patterns.yml`` (legacy)
     4. ``$XDG_DATA_HOME/prism/.prism_patterns.yml``
         or ``~/.local/share/prism/.prism_patterns.yml``
     5. ``$XDG_DATA_HOME/ansible_role_doc/.ansible_role_doc_patterns.yml`` (legacy)
     6. ``./.prism_patterns.yml`` in current working directory
     7. ``./.ansible_role_doc_patterns.yml`` (legacy)
     8. ``$PRISM_PATTERNS_PATH`` if set
     9. ``$ANSIBLE_ROLE_DOC_PATTERNS_PATH`` if set (legacy)
    10. *override_path* if supplied (explicit highest precedence)

    Parameters
    ----------
    override_path:
        Path to a YAML override file.  Non-existent paths are silently ignored
        so callers can always pass the default repo filename without checking
        for its existence.

    Returns
    -------
    dict with keys:
        ``section_aliases`` – dict[str, str]
        ``sensitivity``     – dict with ``name_tokens``, ``vault_markers``,
                              ``credential_prefixes``, ``url_prefixes``
        ``variable_guidance`` – dict with ``priority_keywords``
        ``ansible_builtin_variables`` – set[str]
        ``ignored_identifiers`` – set[str]
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

    If *cache_path* is provided the raw YAML bytes are written there so
    subsequent calls can work offline.

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
        # Fetch failed but we have a cache path to fall back on
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
    """Write a JSON log of *unknown* heading counts to *output_path*.

    This is the input consumed by the ``generate-aliases`` curator command.

    Parameters
    ----------
    unknown:
        Mapping of normalised heading text -> occurrence count.
    output_path:
        File path to write (created/overwritten).
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"unknown_headings": unknown}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
