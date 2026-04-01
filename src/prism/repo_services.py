"""Shared repository-intake helpers for API and CLI layers.

This module remains the compatibility facade while focused responsibilities live
in ``repo_intake`` and ``repo_metadata``.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .errors import FailureDetail, to_failure_detail
from .repo_intake import (
    _RepoCheckoutResult as _IntakeRepoCheckoutResult,
    _RepoLightweightCheckoutResult as _IntakeRepoLightweightCheckoutResult,
    _RepoScanPreparation as _IntakeRepoScanPreparation,
    _build_lightweight_sparse_clone_paths,
    _build_sparse_clone_paths,
    _checkout_repo_lightweight_style_readme,
    _checkout_repo_scan_role,
    _clone_repo,
    _prepare_repo_scan_inputs,
    _repo_scan_workspace,
    _resolve_style_readme_candidate,
)
from .repo_metadata import (
    _build_repo_style_readme_candidates,
    _fetch_repo_contents_payload as _metadata_fetch_repo_contents_payload,
    _fetch_repo_directory_names,
    _fetch_repo_file,
    _github_repo_from_url as _metadata_github_repo_from_url,
    _normalize_repo_path as _metadata_normalize_repo_path,
    _normalize_repo_scan_metadata_paths,
    _normalize_repo_scan_result_payload,
    _repo_name_from_url,
    _repo_path_looks_like_role,
    _resolve_repo_scan_scanner_report_relpath,
)

# Compatibility export for callers monkeypatching repo_services.os.path.
os = os

# Compatibility dataclass exports used by tests and legacy seams.
_RepoScanPreparation = _IntakeRepoScanPreparation
_RepoCheckoutResult = _IntakeRepoCheckoutResult
_RepoLightweightCheckoutResult = _IntakeRepoLightweightCheckoutResult


@dataclass(frozen=True)
class RepoScanTarget:
    """Canonical resolved checkout target used by API and CLI repo scan flows."""

    role_path: Path
    effective_style_readme_path: str | None
    resolved_repo_style_readme_path: str | None


_RepoScanTarget = RepoScanTarget

# Compatibility metadata helper exports used by CLI imports.
_fetch_repo_contents_payload = _metadata_fetch_repo_contents_payload
_github_repo_from_url = _metadata_github_repo_from_url
_normalize_repo_path = _metadata_normalize_repo_path


def build_repo_intake_error(
    *,
    code: str,
    message: str,
    cause: Exception | None = None,
    source: str | None = None,
) -> FailureDetail:
    """Build a normalized repo-intake failure payload."""
    return to_failure_detail(
        code=code,
        message=message,
        source=source,
        cause=cause,
    )


@dataclass(frozen=True)
class RepoScanFacade:
    """Cohesive repo-scan facade for API and CLI orchestration layers."""

    build_lightweight_sparse_clone_paths: object
    build_repo_style_readme_candidates: object
    build_sparse_clone_paths: object
    checkout_repo_lightweight_style_readme: object
    checkout_repo_scan_role: object
    clone_repo: object
    fetch_repo_contents_payload: object
    fetch_repo_directory_names: object
    fetch_repo_file: object
    github_repo_from_url: object
    normalize_repo_path: object
    normalize_repo_scan_result_payload: object
    normalize_repo_scan_metadata_paths: object
    prepare_repo_scan_inputs: object
    repo_name_from_url: object
    repo_path_looks_like_role: object
    repo_scan_workspace: object
    resolve_repo_scan_target: object
    resolve_repo_scan_scanner_report_relpath: object
    resolve_style_readme_candidate: object


def resolve_repo_scan_target(
    *,
    repo_url: str,
    workspace: Path,
    repo_role_path: str,
    repo_style_readme_path: str | None,
    style_readme_path: str | None,
    repo_ref: str | None,
    repo_timeout: int,
    lightweight_readme_only: bool,
    checkout_repo_lightweight_style_readme_fn=None,
    checkout_repo_scan_role_fn=None,
    prepare_repo_scan_inputs_fn=None,
    fetch_repo_directory_names_fn=None,
    repo_path_looks_like_role_fn=None,
    fetch_repo_file_fn=None,
    clone_repo_fn=None,
    build_lightweight_sparse_clone_paths_fn=None,
    build_sparse_clone_paths_fn=None,
    resolve_style_readme_candidate_fn=None,
) -> RepoScanTarget:
    """Resolve checkout + style-guide target through one canonical orchestration path."""
    checkout_repo_lightweight_style_readme_fn = (
        checkout_repo_lightweight_style_readme_fn or _checkout_repo_lightweight_style_readme
    )
    checkout_repo_scan_role_fn = checkout_repo_scan_role_fn or _checkout_repo_scan_role
    prepare_repo_scan_inputs_fn = prepare_repo_scan_inputs_fn or _prepare_repo_scan_inputs
    fetch_repo_directory_names_fn = (
        fetch_repo_directory_names_fn or _fetch_repo_directory_names
    )
    repo_path_looks_like_role_fn = (
        repo_path_looks_like_role_fn or _repo_path_looks_like_role
    )
    fetch_repo_file_fn = fetch_repo_file_fn or _fetch_repo_file
    clone_repo_fn = clone_repo_fn or _clone_repo
    build_lightweight_sparse_clone_paths_fn = (
        build_lightweight_sparse_clone_paths_fn or _build_lightweight_sparse_clone_paths
    )
    build_sparse_clone_paths_fn = build_sparse_clone_paths_fn or _build_sparse_clone_paths
    resolve_style_readme_candidate_fn = (
        resolve_style_readme_candidate_fn or _resolve_style_readme_candidate
    )

    if lightweight_readme_only:
        checkout = checkout_repo_lightweight_style_readme_fn(
            repo_url,
            workspace=workspace,
            repo_role_path=repo_role_path,
            repo_style_readme_path=repo_style_readme_path,
            repo_ref=repo_ref,
            repo_timeout=repo_timeout,
            prepare_repo_scan_inputs=prepare_repo_scan_inputs_fn,
            fetch_repo_directory_names=fetch_repo_directory_names_fn,
            repo_path_looks_like_role=repo_path_looks_like_role_fn,
            fetch_repo_file=fetch_repo_file_fn,
            clone_repo=clone_repo_fn,
            build_lightweight_sparse_clone_paths=build_lightweight_sparse_clone_paths_fn,
            resolve_style_readme_candidate=resolve_style_readme_candidate_fn,
        )
        return RepoScanTarget(
            role_path=checkout.role_stub_dir,
            effective_style_readme_path=checkout.effective_style_readme_path,
            resolved_repo_style_readme_path=checkout.resolved_repo_style_readme_path,
        )

    checkout = checkout_repo_scan_role_fn(
        repo_url,
        workspace=workspace,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        style_readme_path=style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        prepare_repo_scan_inputs=prepare_repo_scan_inputs_fn,
        fetch_repo_directory_names=fetch_repo_directory_names_fn,
        repo_path_looks_like_role=repo_path_looks_like_role_fn,
        fetch_repo_file=fetch_repo_file_fn,
        clone_repo=clone_repo_fn,
        build_sparse_clone_paths=build_sparse_clone_paths_fn,
        resolve_style_readme_candidate=resolve_style_readme_candidate_fn,
    )
    return RepoScanTarget(
        role_path=checkout.role_path,
        effective_style_readme_path=checkout.effective_style_readme_path,
        resolved_repo_style_readme_path=checkout.resolved_repo_style_readme_path,
    )


# Public surface for API consumers.
build_lightweight_sparse_clone_paths = _build_lightweight_sparse_clone_paths
build_repo_style_readme_candidates = _build_repo_style_readme_candidates
build_sparse_clone_paths = _build_sparse_clone_paths
checkout_repo_lightweight_style_readme = _checkout_repo_lightweight_style_readme
checkout_repo_scan_role = _checkout_repo_scan_role
clone_repo = _clone_repo
fetch_repo_directory_names = _fetch_repo_directory_names
fetch_repo_file = _fetch_repo_file
normalize_repo_scan_result_payload = _normalize_repo_scan_result_payload
normalize_repo_scan_metadata_paths = _normalize_repo_scan_metadata_paths
fetch_repo_contents_payload = _metadata_fetch_repo_contents_payload
github_repo_from_url = _metadata_github_repo_from_url
normalize_repo_path = _metadata_normalize_repo_path
prepare_repo_scan_inputs = _prepare_repo_scan_inputs
repo_name_from_url = _repo_name_from_url
repo_path_looks_like_role = _repo_path_looks_like_role
repo_scan_workspace = _repo_scan_workspace
resolve_repo_scan_scanner_report_relpath = _resolve_repo_scan_scanner_report_relpath
resolve_style_readme_candidate = _resolve_style_readme_candidate
_resolve_repo_scan_target = resolve_repo_scan_target

repo_scan_facade = RepoScanFacade(
    build_lightweight_sparse_clone_paths=build_lightweight_sparse_clone_paths,
    build_repo_style_readme_candidates=build_repo_style_readme_candidates,
    build_sparse_clone_paths=build_sparse_clone_paths,
    checkout_repo_lightweight_style_readme=checkout_repo_lightweight_style_readme,
    checkout_repo_scan_role=checkout_repo_scan_role,
    clone_repo=clone_repo,
    fetch_repo_contents_payload=fetch_repo_contents_payload,
    fetch_repo_directory_names=fetch_repo_directory_names,
    fetch_repo_file=fetch_repo_file,
    github_repo_from_url=github_repo_from_url,
    normalize_repo_path=normalize_repo_path,
    normalize_repo_scan_result_payload=normalize_repo_scan_result_payload,
    normalize_repo_scan_metadata_paths=normalize_repo_scan_metadata_paths,
    prepare_repo_scan_inputs=prepare_repo_scan_inputs,
    repo_name_from_url=repo_name_from_url,
    repo_path_looks_like_role=repo_path_looks_like_role,
    repo_scan_workspace=repo_scan_workspace,
    resolve_repo_scan_target=resolve_repo_scan_target,
    resolve_repo_scan_scanner_report_relpath=resolve_repo_scan_scanner_report_relpath,
    resolve_style_readme_candidate=resolve_style_readme_candidate,
)
