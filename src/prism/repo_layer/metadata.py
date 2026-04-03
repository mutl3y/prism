"""Repository metadata, transport, and payload normalization helpers."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from ..errors import (
    PrismRuntimeError,
    REPO_SCAN_PAYLOAD_JSON_INVALID,
    REPO_SCAN_PAYLOAD_SHAPE_INVALID,
    REPO_SCAN_PAYLOAD_TYPE_INVALID,
)

_ROLE_MARKER_DIRS = frozenset(
    {"defaults", "files", "handlers", "meta", "tasks", "templates", "tests", "vars"}
)
_REQUIRED_ROLE_DIRS = frozenset({"defaults", "tasks", "meta"})
_REPO_TRANSPORT_POLICY_ENV_VAR = "PRISM_REPO_TRANSPORT_POLICY"
_REPO_TRANSPORT_POLICY_DEFAULT = "preserve"


def _normalize_repo_transport_policy(policy: str | None) -> str:
    """Return a supported transport policy with safe fallback semantics."""
    raw_policy = (policy or os.environ.get(_REPO_TRANSPORT_POLICY_ENV_VAR, "")).strip()
    if not raw_policy:
        return _REPO_TRANSPORT_POLICY_DEFAULT

    normalized = raw_policy.lower()
    alias_map = {
        "default": "preserve",
        "https": "preserve",
        "legacy": "ssh",
        "compat": "ssh",
    }
    normalized = alias_map.get(normalized, normalized)
    if normalized in {"preserve", "ssh"}:
        return normalized
    return _REPO_TRANSPORT_POLICY_DEFAULT


def _resolve_repo_clone_url(repo_url: str, transport_policy: str | None = None) -> str:
    """Resolve clone URL according to deterministic transport policy."""
    policy = _normalize_repo_transport_policy(transport_policy)
    if policy != "ssh":
        return repo_url

    parsed = urlparse(repo_url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "github.com":
        return repo_url

    repo_path = parsed.path.strip("/")
    if not repo_path or repo_path.count("/") < 1:
        return repo_url

    if not repo_path.endswith(".git"):
        repo_path = f"{repo_path}.git"
    return f"git@github.com:{repo_path}"


def _repo_name_from_url(repo_url: str) -> str | None:
    """Extract a best-effort repository name from a URL or SSH git URL."""
    parsed = urlparse(repo_url)
    if parsed.scheme in {"http", "https", "ssh"} and parsed.path:
        name = Path(parsed.path).name
        return name.removesuffix(".git") or None
    if repo_url.startswith("git@") and ":" in repo_url:
        path = repo_url.split(":", 1)[1]
        name = Path(path).name
        return name.removesuffix(".git") or None
    return None


def _repo_path_looks_like_role(dir_names: set[str] | None) -> bool:
    """Return True when a directory listing looks like a useful role source."""
    if not dir_names:
        return False

    role_markers = _ROLE_MARKER_DIRS & dir_names
    if _REQUIRED_ROLE_DIRS <= role_markers:
        return True
    return False


def _build_repo_style_readme_candidates(
    repo_style_readme_path: str | None,
) -> list[str]:
    """Build deterministic README path candidates for case-variant fallback."""
    normalized = (repo_style_readme_path or "").strip().strip("/")
    if normalized in {"", "."}:
        return []

    candidates: list[str] = [normalized]
    path_obj = Path(normalized)
    file_name = path_obj.name
    parent = path_obj.parent.as_posix()
    if parent == ".":
        parent = ""

    if file_name.lower() == "readme.md":
        for variant in ("README.md", "Readme.md", "readme.md"):
            candidate = f"{parent}/{variant}" if parent else variant
            if candidate not in candidates:
                candidates.append(candidate)

    return candidates


def _resolve_repo_scan_scanner_report_relpath(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    primary_output_path: str,
) -> str | None:
    """Resolve logical scanner sidecar relpath for repo-backed scan metadata."""
    if not concise_readme:
        return None

    primary_path = Path(primary_output_path)
    scanner_report_path = (
        Path(scanner_report_output)
        if scanner_report_output
        else primary_path.with_suffix(".scan-report.md")
    )
    relpath = os.path.relpath(scanner_report_path, primary_path.parent)
    return relpath.replace("\\", "/")


def _normalize_repo_scan_metadata_paths(
    payload: dict[str, Any],
    *,
    repo_style_readme_path: str | None = None,
    scanner_report_relpath: str | None = None,
) -> dict[str, Any]:
    """Replace temp-backed metadata paths with logical repo-relative paths."""
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return payload

    normalized_metadata = dict(metadata)

    if repo_style_readme_path:
        style_guide = normalized_metadata.get("style_guide")
        if isinstance(style_guide, dict):
            normalized_style_guide = dict(style_guide)
            normalized_style_guide["path"] = repo_style_readme_path
            normalized_metadata["style_guide"] = normalized_style_guide

    if scanner_report_relpath:
        normalized_metadata["scanner_report_relpath"] = scanner_report_relpath

    normalized_payload = dict(payload)
    normalized_payload["metadata"] = normalized_metadata
    return normalized_payload


def _normalize_repo_scan_result_payload(
    payload: dict[str, Any] | str,
    *,
    repo_style_readme_path: str | None = None,
    scanner_report_relpath: str | None = None,
) -> dict[str, Any] | str:
    """Normalize repo scan payload metadata for dict and JSON-string payloads."""
    if isinstance(payload, dict):
        _validate_repo_scan_payload_shape(payload)
        return _normalize_repo_scan_metadata_paths(
            payload,
            repo_style_readme_path=repo_style_readme_path,
            scanner_report_relpath=scanner_report_relpath,
        )

    if not isinstance(payload, str):
        return payload

    parsed_payload = _decode_repo_scan_payload_json(payload)
    _validate_repo_scan_payload_shape(parsed_payload)

    normalized_payload = _normalize_repo_scan_metadata_paths(
        parsed_payload,
        repo_style_readme_path=repo_style_readme_path,
        scanner_report_relpath=scanner_report_relpath,
    )
    return json.dumps(normalized_payload, indent=2)


def _decode_repo_scan_payload_json(payload: str) -> dict[str, Any]:
    """Decode repo-scan JSON payload and enforce top-level mapping contract."""
    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PrismRuntimeError(
            code=REPO_SCAN_PAYLOAD_JSON_INVALID,
            category="parser",
            message="payload is not valid JSON",
        ) from exc

    if not isinstance(parsed_payload, dict):
        raise PrismRuntimeError(
            code=REPO_SCAN_PAYLOAD_TYPE_INVALID,
            category="validation",
            message="top-level payload must be a JSON object",
        )

    return parsed_payload


def _validate_repo_scan_payload_shape(payload: dict[str, Any]) -> None:
    """Validate optional nested shape assumptions for repo-scan payloads."""
    metadata = payload.get("metadata")
    if metadata is None:
        return
    if not isinstance(metadata, dict):
        raise PrismRuntimeError(
            code=REPO_SCAN_PAYLOAD_SHAPE_INVALID,
            category="validation",
            message="metadata must be a JSON object",
        )

    style_guide = metadata.get("style_guide")
    if style_guide is not None and not isinstance(style_guide, dict):
        raise PrismRuntimeError(
            code=REPO_SCAN_PAYLOAD_SHAPE_INVALID,
            category="validation",
            message="metadata.style_guide must be a JSON object",
        )


def _github_repo_from_url(repo_url: str) -> tuple[str, str] | None:
    """Return ``(owner, repo)`` for GitHub repo URLs when parseable."""
    parsed = urlparse(repo_url)
    repo_path = ""
    if parsed.scheme in {"http", "https", "ssh"} and parsed.netloc == "github.com":
        repo_path = parsed.path.strip("/")
    elif repo_url.startswith("git@github.com:"):
        repo_path = repo_url.split(":", 1)[1].strip("/")

    parts = [segment for segment in repo_path.split("/") if segment]
    if len(parts) < 2:
        return None

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo:
        return None
    return owner, repo


def _normalize_repo_path(repo_path: str | None) -> str:
    """Normalize repository-relative paths used for remote GitHub probes."""
    normalized_repo_path = (repo_path or "").strip().strip("/")
    if normalized_repo_path in {"", "."}:
        return ""
    return normalized_repo_path


def _fetch_repo_contents_payload(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
    *,
    opener=urlopen,
) -> dict | list | None:
    """Fetch GitHub contents API payload for a repo path when possible."""
    repo_coords = _github_repo_from_url(repo_url)
    if repo_coords is None:
        return None

    normalized_repo_path = _normalize_repo_path(repo_path)
    owner, repo = repo_coords
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    if normalized_repo_path:
        api_url = f"{api_url}/{quote(normalized_repo_path, safe='/')}"
    if ref:
        api_url = f"{api_url}?ref={quote(ref, safe='')}"

    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github.object",
            "User-Agent": "prism",
        },
    )

    try:
        with opener(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        OSError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None


def _fetch_repo_directory_names(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
    *,
    opener=urlopen,
    fetch_payload=None,
) -> set[str] | None:
    """Fetch directory names for a GitHub repo path when possible."""
    payload_fetcher = fetch_payload or _fetch_repo_contents_payload
    payload = payload_fetcher(
        repo_url,
        repo_path=repo_path,
        ref=ref,
        timeout=timeout,
        opener=opener,
    )
    if not isinstance(payload, list):
        return None

    dir_names: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict) or entry.get("type") != "dir":
            continue
        name = entry.get("name")
        if isinstance(name, str) and name:
            dir_names.add(name)
    return dir_names


def _fetch_repo_file(
    repo_url: str,
    repo_path: str | None,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
    *,
    opener=urlopen,
    fetch_payload=None,
    decode_base64=None,
) -> Path | None:
    """Fetch a single file from GitHub into ``destination`` when possible.

    Returns ``None`` for unsupported hosts or when the remote fetch fails so
    callers can fall back to clone-based resolution.
    """
    normalized_repo_path = _normalize_repo_path(repo_path)
    if not normalized_repo_path:
        return None

    payload_fetcher = fetch_payload or _fetch_repo_contents_payload
    payload = payload_fetcher(
        repo_url,
        repo_path=normalized_repo_path,
        ref=ref,
        timeout=timeout,
        opener=opener,
    )
    if not isinstance(payload, dict):
        return None

    if payload.get("type") != "file":
        return None

    content = payload.get("content")
    encoding = payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        return None

    base64_decoder = decode_base64 or base64.b64decode
    try:
        decoded = base64_decoder(content)
    except ValueError:
        return None

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(decoded)
    return destination
