"""Shared repository-intake helpers for API and CLI layers.

This module remains the compatibility facade while focused responsibilities live
in ``repo_intake`` and ``repo_metadata``.
"""

from __future__ import annotations

import os

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
