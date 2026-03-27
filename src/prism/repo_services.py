"""Shared repository-intake helpers for API and CLI layers.

These helpers are intentionally free of CLI argument handling so the public API
can depend on them without importing CLI orchestration code.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
import subprocess
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from typing import Any

_ROLE_MARKER_DIRS = frozenset(
    {"defaults", "files", "handlers", "meta", "tasks", "templates", "tests", "vars"}
)
_REQUIRED_ROLE_DIRS = frozenset({"defaults", "tasks", "meta"})
_REQUIRED_ROLE_DIR_SEQUENCE = ("defaults", "tasks", "meta")
_SHARED_TMP_ROOT_NAME = "prism"


@dataclass(frozen=True)
class _RepoScanPreparation:
    """Prepared preflight inputs for repository-backed scan orchestration."""

    repo_dir_names: set[str] | None
    style_candidates: list[str]
    fetched_repo_style_readme_path: Path | None
    resolved_repo_style_readme_path: str | None


@dataclass(frozen=True)
class _RepoCheckoutResult:
    """Resolved checkout inputs for repo-backed scan execution."""

    checkout_dir: Path
    role_path: Path
    effective_style_readme_path: str | None
    resolved_repo_style_readme_path: str | None
    style_candidates: list[str]
    fetched_repo_style_readme_path: Path | None


@dataclass(frozen=True)
class _RepoLightweightCheckoutResult:
    """Resolved lightweight repo-style inputs for README-only scans."""

    role_stub_dir: Path
    effective_style_readme_path: str
    resolved_repo_style_readme_path: str


@contextmanager
def _repo_scan_workspace():
    """Yield a repo-scan workspace under a shared temp root and clean it up."""
    shared_root = Path(tempfile.gettempdir()) / _SHARED_TMP_ROOT_NAME
    shared_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="scan-", dir=shared_root))
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        try:
            if shared_root.exists() and not any(shared_root.iterdir()):
                shared_root.rmdir()
        except OSError:
            pass


def _repo_name_from_url(repo_url: str) -> str | None:
    """Extract a best-effort repository name from a URL or SSH git URL."""
    from urllib.parse import urlparse

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


def _build_sparse_clone_paths(
    repo_role_path: str,
    repo_style_readme_path: str | list[str] | None,
) -> list[str]:
    """Build sparse checkout targets for repo-based scans."""
    role_path = (repo_role_path or ".").strip()
    if role_path in {"", "."}:
        return []

    paths = [role_path]
    if isinstance(repo_style_readme_path, list):
        paths.extend(
            path.strip() for path in repo_style_readme_path if path and path.strip()
        )
    elif repo_style_readme_path and repo_style_readme_path.strip():
        paths.append(repo_style_readme_path.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def _build_lightweight_sparse_clone_paths(
    repo_role_path: str,
    style_candidates: list[str],
) -> list[str]:
    """Build sparse paths for lightweight README-only scans."""
    if repo_role_path.strip() in {"", "."}:
        role_sparse_paths = list(_REQUIRED_ROLE_DIR_SEQUENCE)
    else:
        role_sparse_paths = [
            f"{repo_role_path.rstrip('/')}/{required_dir}"
            for required_dir in _REQUIRED_ROLE_DIR_SEQUENCE
        ]

    sparse_paths: list[str] = []
    for sparse_path in [*role_sparse_paths, *style_candidates]:
        if sparse_path and sparse_path not in sparse_paths:
            sparse_paths.append(sparse_path)
    return sparse_paths


def _prepare_repo_scan_inputs(
    repo_url: str,
    *,
    workspace: Path,
    repo_role_path: str = ".",
    repo_style_readme_path: str | None = None,
    repo_ref: str | None = None,
    repo_timeout: int = 60,
    fetch_repo_directory_names=None,
    repo_path_looks_like_role=None,
    fetch_repo_file=None,
) -> _RepoScanPreparation:
    """Resolve shared preflight inputs used by API and CLI repo scan flows."""
    directory_names_fetcher = fetch_repo_directory_names or _fetch_repo_directory_names
    role_path_detector = repo_path_looks_like_role or _repo_path_looks_like_role
    repo_file_fetcher = fetch_repo_file or _fetch_repo_file

    repo_dir_names = directory_names_fetcher(
        repo_url,
        repo_path=repo_role_path,
        ref=repo_ref,
        timeout=repo_timeout,
    )
    if repo_dir_names is not None and not role_path_detector(repo_dir_names):
        raise FileNotFoundError(
            f"repository path does not look like an Ansible role: {repo_role_path}"
        )

    style_candidates = _build_repo_style_readme_candidates(repo_style_readme_path)
    fetched_repo_style_readme_path = None
    resolved_repo_style_readme_path = repo_style_readme_path
    for style_candidate in style_candidates:
        fetched_repo_style_readme_path = repo_file_fetcher(
            repo_url,
            style_candidate,
            workspace / "repo-style-readme" / Path(style_candidate).name,
            ref=repo_ref,
            timeout=repo_timeout,
        )
        if fetched_repo_style_readme_path is not None:
            resolved_repo_style_readme_path = style_candidate
            break

    return _RepoScanPreparation(
        repo_dir_names=repo_dir_names,
        style_candidates=style_candidates,
        fetched_repo_style_readme_path=fetched_repo_style_readme_path,
        resolved_repo_style_readme_path=resolved_repo_style_readme_path,
    )


def _resolve_style_readme_candidate(
    *,
    checkout_dir: Path,
    style_readme_path: str | None,
    style_candidates: list[str],
    fetched_repo_style_readme_path: Path | None,
    resolved_repo_style_readme_path: str | None,
) -> tuple[str | None, str | None]:
    """Resolve effective and logical style README path after checkout/fetch."""
    effective_style_readme_path = style_readme_path
    logical_style_readme_path = resolved_repo_style_readme_path

    if fetched_repo_style_readme_path is not None:
        effective_style_readme_path = str(fetched_repo_style_readme_path.resolve())
        return effective_style_readme_path, logical_style_readme_path

    for style_candidate in style_candidates:
        candidate_path = (checkout_dir / style_candidate).resolve()
        if candidate_path.is_file():
            effective_style_readme_path = str(candidate_path)
            logical_style_readme_path = style_candidate
            break

    return effective_style_readme_path, logical_style_readme_path


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
    """Normalize repo scan payload metadata for dict and JSON-string payloads.

    This keeps API and CLI repo-scan metadata normalization behavior aligned while
    preserving their existing payload formats.
    """
    if isinstance(payload, dict):
        return _normalize_repo_scan_metadata_paths(
            payload,
            repo_style_readme_path=repo_style_readme_path,
            scanner_report_relpath=scanner_report_relpath,
        )

    if not isinstance(payload, str):
        return payload

    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError:
        return payload

    if not isinstance(parsed_payload, dict):
        return payload

    normalized_payload = _normalize_repo_scan_metadata_paths(
        parsed_payload,
        repo_style_readme_path=repo_style_readme_path,
        scanner_report_relpath=scanner_report_relpath,
    )
    return json.dumps(normalized_payload, indent=2)


def _checkout_repo_scan_role(
    repo_url: str,
    *,
    workspace: Path,
    repo_role_path: str = ".",
    repo_style_readme_path: str | None = None,
    style_readme_path: str | None = None,
    repo_ref: str | None = None,
    repo_timeout: int = 60,
    prepare_repo_scan_inputs=None,
    fetch_repo_directory_names=None,
    repo_path_looks_like_role=None,
    fetch_repo_file=None,
    clone_repo=None,
    build_sparse_clone_paths=None,
    resolve_style_readme_candidate=None,
) -> _RepoCheckoutResult:
    """Prepare, clone, and resolve role/style paths for repo-backed scans."""
    checkout_dir = workspace / "repo"
    prepare_inputs = prepare_repo_scan_inputs or _prepare_repo_scan_inputs
    clone_repository = clone_repo or _clone_repo
    sparse_path_builder = build_sparse_clone_paths or _build_sparse_clone_paths
    style_resolver = resolve_style_readme_candidate or _resolve_style_readme_candidate

    prepared = prepare_inputs(
        repo_url,
        workspace=workspace,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        fetch_repo_directory_names=fetch_repo_directory_names,
        repo_path_looks_like_role=repo_path_looks_like_role,
        fetch_repo_file=fetch_repo_file,
    )

    clone_repository(
        repo_url,
        checkout_dir,
        repo_ref,
        repo_timeout,
        sparse_paths=sparse_path_builder(
            repo_role_path,
            (
                None
                if prepared.fetched_repo_style_readme_path is not None
                else prepared.style_candidates
            ),
        ),
    )

    role_path = (checkout_dir / repo_role_path).resolve()
    if not role_path.exists() or not role_path.is_dir():
        raise FileNotFoundError(
            f"role path not found in cloned repository: {repo_role_path}"
        )

    (
        effective_style_readme_path,
        resolved_repo_style_readme_path,
    ) = style_resolver(
        checkout_dir=checkout_dir,
        style_readme_path=style_readme_path,
        style_candidates=prepared.style_candidates,
        fetched_repo_style_readme_path=prepared.fetched_repo_style_readme_path,
        resolved_repo_style_readme_path=prepared.resolved_repo_style_readme_path,
    )

    return _RepoCheckoutResult(
        checkout_dir=checkout_dir,
        role_path=role_path,
        effective_style_readme_path=effective_style_readme_path,
        resolved_repo_style_readme_path=resolved_repo_style_readme_path,
        style_candidates=prepared.style_candidates,
        fetched_repo_style_readme_path=prepared.fetched_repo_style_readme_path,
    )


def _checkout_repo_lightweight_style_readme(
    repo_url: str,
    *,
    workspace: Path,
    repo_role_path: str = ".",
    repo_style_readme_path: str | None = None,
    repo_ref: str | None = None,
    repo_timeout: int = 60,
    prepare_repo_scan_inputs=None,
    fetch_repo_directory_names=None,
    repo_path_looks_like_role=None,
    fetch_repo_file=None,
    clone_repo=None,
    build_lightweight_sparse_clone_paths=None,
    resolve_style_readme_candidate=None,
) -> _RepoLightweightCheckoutResult:
    """Prepare lightweight style README checkout inputs for repo-backed scans."""
    checkout_dir = workspace / "repo"
    prepare_inputs = prepare_repo_scan_inputs or _prepare_repo_scan_inputs
    clone_repository = clone_repo or _clone_repo
    sparse_path_builder = (
        build_lightweight_sparse_clone_paths or _build_lightweight_sparse_clone_paths
    )
    role_path_detector = repo_path_looks_like_role or _repo_path_looks_like_role
    style_resolver = resolve_style_readme_candidate or _resolve_style_readme_candidate

    prepared = prepare_inputs(
        repo_url,
        workspace=workspace,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        fetch_repo_directory_names=fetch_repo_directory_names,
        repo_path_looks_like_role=role_path_detector,
        fetch_repo_file=fetch_repo_file,
    )

    if not prepared.style_candidates:
        raise FileNotFoundError("lightweight repo scan requires repo_style_readme_path")

    effective_style_readme_path: str | None = None
    resolved_repo_style_readme_path = prepared.resolved_repo_style_readme_path
    if prepared.fetched_repo_style_readme_path is not None:
        effective_style_readme_path = str(
            prepared.fetched_repo_style_readme_path.resolve()
        )
    else:
        if prepared.repo_dir_names is None:
            clone_repository(
                repo_url,
                checkout_dir,
                repo_ref,
                repo_timeout,
                sparse_paths=sparse_path_builder(
                    repo_role_path,
                    prepared.style_candidates,
                ),
                allow_sparse_fallback_to_full=False,
            )

            role_path = (checkout_dir / repo_role_path).resolve()
            if not role_path.exists() or not role_path.is_dir():
                raise FileNotFoundError(
                    f"role path not found in cloned repository: {repo_role_path}"
                )

            local_dir_names = {
                child.name for child in role_path.iterdir() if child.is_dir()
            }
            if not role_path_detector(local_dir_names):
                raise FileNotFoundError(
                    "repository path does not look like an Ansible role: "
                    f"{repo_role_path}"
                )

            (
                effective_style_readme_path,
                resolved_repo_style_readme_path,
            ) = style_resolver(
                checkout_dir=checkout_dir,
                style_readme_path=effective_style_readme_path,
                style_candidates=prepared.style_candidates,
                fetched_repo_style_readme_path=None,
                resolved_repo_style_readme_path=resolved_repo_style_readme_path,
            )

    if effective_style_readme_path is None:
        expected = repo_style_readme_path or "README.md"
        raise FileNotFoundError(f"style README not found in repository: {expected}")

    role_stub_dir = workspace / "role-stub"
    role_stub_dir.mkdir(parents=True, exist_ok=True)
    return _RepoLightweightCheckoutResult(
        role_stub_dir=role_stub_dir,
        effective_style_readme_path=effective_style_readme_path,
        resolved_repo_style_readme_path=resolved_repo_style_readme_path
        or (repo_style_readme_path or "README.md"),
    )


def _clone_repo(
    repo_url: str,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
    sparse_paths: list[str] | None = None,
    allow_sparse_fallback_to_full: bool = True,
    *,
    run_command=None,
    environment=None,
    remove_tree=None,
) -> None:
    """Clone a git repository into ``destination`` with shallow history.

    When ``sparse_paths`` is provided, first attempt a sparse/partial checkout to
    reduce downloaded content. If sparse setup fails, behavior depends on
    ``allow_sparse_fallback_to_full``.
    """
    parsed = urlparse(repo_url)
    clone_url = repo_url
    if parsed.scheme in {"http", "https"} and parsed.netloc == "github.com":
        repo_path = parsed.path.strip("/")
        if repo_path and repo_path.count("/") >= 1:
            if not repo_path.endswith(".git"):
                repo_path = f"{repo_path}.git"
            clone_url = f"git@github.com:{repo_path}"

    clone_cmd = ["git", "clone", "--depth", "1"]
    if ref:
        clone_cmd.extend(["--branch", ref, "--single-branch"])

    requested_sparse_paths = [
        path.strip() for path in (sparse_paths or []) if path and path.strip()
    ]
    use_sparse_clone = bool(requested_sparse_paths)
    if use_sparse_clone:
        clone_cmd.extend(["--filter=blob:none", "--sparse"])

    clone_cmd.extend([clone_url, str(destination)])

    clone_runner = run_command or subprocess.run
    env_source = environment if environment is not None else os.environ
    cleanup_tree = remove_tree or shutil.rmtree

    env = env_source.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

    def _run_clone(cmd: list[str]) -> None:
        clone_runner(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )

    def _run_sparse_checkout(paths: list[str]) -> None:
        sparse_cmd = [
            "git",
            "-C",
            str(destination),
            "sparse-checkout",
            "set",
            "--no-cone",
            *paths,
        ]
        clone_runner(
            sparse_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )

    try:
        if use_sparse_clone:
            try:
                _run_clone(clone_cmd)
                _run_sparse_checkout(requested_sparse_paths)
                return
            except subprocess.CalledProcessError as sparse_exc:
                cleanup_tree(destination, ignore_errors=True)
                if not allow_sparse_fallback_to_full:
                    sparse_stderr = (sparse_exc.stderr or "").strip()
                    raise RuntimeError(
                        "repository sparse checkout failed"
                        + (f": {sparse_stderr}" if sparse_stderr else "")
                    ) from sparse_exc

        fallback_cmd = ["git", "clone", "--depth", "1"]
        if ref:
            fallback_cmd.extend(["--branch", ref, "--single-branch"])
        fallback_cmd.extend([clone_url, str(destination)])
        _run_clone(fallback_cmd)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"repository clone timed out after {timeout}s: {repo_url}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"repository clone failed: {stderr or repo_url}") from exc


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
