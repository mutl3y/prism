"""Pattern policy loader for prism."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from prism.scanner_data.contracts_request import PolicyContext

# Try fsrc data dir first, fall back to src data dir (sibling in repo)
_CANDIDATE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if not _CANDIDATE_DATA_DIR.is_dir():
    _CANDIDATE_DATA_DIR = (
        Path(__file__).resolve().parent.parent.parent.parent.parent
        / "src"
        / "prism"
        / "data"
    )
_BUILTIN_DATA_DIR = _CANDIDATE_DATA_DIR

REPO_OVERRIDE_FILENAME = ".prism_patterns.yml"
CWD_OVERRIDE_FILENAME = ".prism_patterns.yml"
ENV_PATTERNS_OVERRIDE_PATH = "PRISM_PATTERNS_PATH"

XDG_DATA_HOME_ENV = "XDG_DATA_HOME"
APP_DATA_DIRNAME = "prism"
SYSTEM_PATTERN_OVERRIDE_PATH = (
    Path("/var/lib") / APP_DATA_DIRNAME / CWD_OVERRIDE_FILENAME
)

DEFAULT_REMOTE_URL = (
    "https://raw.githubusercontent.com/mutl3y/prism_patterns" "/main/pattern_policy.yml"
)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _normalise(policy: dict[str, Any]) -> dict[str, Any]:
    def _normalise_token_collection(raw: Any) -> set[str]:
        if isinstance(raw, str):
            value = raw.strip()
            return {value} if value else set()
        if isinstance(raw, (list, tuple, set)):
            values: set[str] = set()
            for item in raw:
                if isinstance(item, str):
                    value = item.strip()
                    if value:
                        values.add(value)
            return values
        return set()

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
    policy["ansible_builtin_variables"] = _normalise_token_collection(
        policy["ansible_builtin_variables"]
    )
    policy["ignored_identifiers"] = _normalise_token_collection(
        policy["ignored_identifiers"]
    )
    return policy


def _load_builtin_policy() -> dict[str, Any]:
    """Load and merge all per-topic YAML files from the data directory."""
    if not _BUILTIN_DATA_DIR.is_dir():
        return {}
    policy: dict[str, Any] = {}
    for yml_file in sorted(_BUILTIN_DATA_DIR.glob("*.yml")):
        chunk = _load_yaml(yml_file)
        policy = _deep_merge(policy, chunk)
    return policy


def _default_user_data_home() -> Path:
    raw = os.environ.get(XDG_DATA_HOME_ENV)
    if raw:
        return Path(raw).expanduser()
    return (Path.home() / ".local" / "share").expanduser()


def _resolve_search_root(search_root: str | Path | None) -> Path | None:
    if search_root is None:
        return None
    root_path = Path(search_root).expanduser()
    if root_path.exists() and root_path.is_file():
        return root_path.parent.resolve()
    return root_path.resolve()


def _iter_default_override_paths(
    *,
    search_root: str | Path | None = None,
) -> list[Path]:
    paths = []
    paths.append(SYSTEM_PATTERN_OVERRIDE_PATH)
    user_data_home = _default_user_data_home()
    paths.append(user_data_home / APP_DATA_DIRNAME / CWD_OVERRIDE_FILENAME)
    local_override_root = _resolve_search_root(search_root)
    if local_override_root is not None:
        paths.append(local_override_root / REPO_OVERRIDE_FILENAME)
    env_override = os.environ.get(ENV_PATTERNS_OVERRIDE_PATH)
    if env_override:
        paths.append(Path(env_override).expanduser())
    return paths


def load_pattern_config(
    override_path: str | Path | None = None,
    *,
    search_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load pattern configuration policy from built-in and override sources."""
    policy = _load_builtin_policy()

    for override_file in _iter_default_override_paths(search_root=search_root):
        if override_file.exists():
            override = _load_yaml(override_file)
            if override:
                policy = _deep_merge(policy, override)

    if override_path is not None:
        override_file = Path(override_path).expanduser()
        if override_file.exists():
            override = _load_yaml(override_file)
            if override:
                policy = _deep_merge(policy, override)

    return _normalise(policy)


def build_policy_context(policy: dict[str, Any]) -> PolicyContext:
    """Build a normalized immutable per-scan policy snapshot contract."""
    return {
        "section_aliases": dict(policy.get("section_aliases") or {}),
        "ignored_identifiers": frozenset(
            token.lower()
            for token in (policy.get("ignored_identifiers") or set())
            if isinstance(token, str)
        ),
        "variable_guidance_keywords": tuple(
            token
            for token in (
                policy.get("variable_guidance", {}).get("priority_keywords") or []
            )
            if isinstance(token, str)
        ),
    }


def load_pattern_policy_with_context(
    override_path: str | Path | None = None,
    *,
    search_root: str | Path | None = None,
) -> tuple[dict[str, Any], PolicyContext]:
    """Load pattern policy plus its normalized per-scan policy context."""
    policy = load_pattern_config(
        override_path=override_path,
        search_root=search_root,
    )
    return policy, build_policy_context(policy)


def fetch_remote_policy(
    url: str = DEFAULT_REMOTE_URL,
    cache_path: str | Path | None = None,
    timeout: int = 10,
    expected_integrity: str | None = None,
) -> dict[str, Any]:
    """Fetch a ``pattern_policy.yml`` from *url* and return the parsed policy."""

    def _parse_expected_sha256(integrity: str | None) -> str | None:
        if integrity is None:
            return None
        if not isinstance(integrity, str):
            raise RuntimeError(
                "REMOTE_POLICY_INTEGRITY_CONTRACT_INVALID: expected_integrity must be a string"
            )
        value = integrity.strip().lower()
        if not value.startswith("sha256:"):
            raise RuntimeError(
                "REMOTE_POLICY_INTEGRITY_CONTRACT_INVALID: expected format is sha256:<64 hex>"
            )
        digest = value.split(":", 1)[1]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise RuntimeError(
                "REMOTE_POLICY_INTEGRITY_CONTRACT_INVALID: expected format is sha256:<64 hex>"
            )
        return digest

    expected_sha256 = _parse_expected_sha256(expected_integrity)

    def _verify_integrity(raw: bytes) -> None:
        if expected_sha256 is None:
            return
        actual_sha256 = hashlib.sha256(raw).hexdigest()
        if actual_sha256 != expected_sha256:
            raise RuntimeError(
                "REMOTE_POLICY_INTEGRITY_MISMATCH: remote policy checksum mismatch"
            )

    raw_bytes: bytes | None = None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            raw_bytes = resp.read()
    except urllib.error.URLError as exc:
        if cache_path is None:
            raise RuntimeError(
                f"Failed to fetch remote patterns from {url}: {exc}"
            ) from exc

    if raw_bytes is not None:
        _verify_integrity(raw_bytes)

    if raw_bytes is not None and cache_path is not None:
        cache_file = Path(cache_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(raw_bytes)

    if raw_bytes is None:
        if cache_path is not None:
            cache_file = Path(cache_path)
            if cache_file.exists():
                raw_bytes = cache_file.read_bytes()
                _verify_integrity(raw_bytes)
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
