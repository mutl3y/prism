"""Public library API for scanner consumers.

This module provides a stable import surface for external tooling that wants
machine-readable scan results without coupling to CLI internals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cli import (
    _build_repo_style_readme_candidates,
    _build_sparse_clone_paths,
    _clone_repo,
    _fetch_repo_directory_names,
    _fetch_repo_file,
    _repo_scan_workspace,
    _repo_path_looks_like_role,
    _repo_name_from_url,
)
from .scanner import run_scan

_REQUIRED_ROLE_DIRS = ("defaults", "tasks", "meta")


def _normalize_repo_style_guide_path(
    payload: dict[str, Any], repo_style_readme_path: str | None
) -> dict[str, Any]:
    """Replace temp-backed style guide paths with the logical repo path."""
    if not repo_style_readme_path:
        return payload

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return payload

    style_guide = metadata.get("style_guide")
    if not isinstance(style_guide, dict):
        return payload

    normalized_style_guide = dict(style_guide)
    normalized_style_guide["path"] = repo_style_readme_path

    normalized_metadata = dict(metadata)
    normalized_metadata["style_guide"] = normalized_style_guide

    normalized_payload = dict(payload)
    normalized_payload["metadata"] = normalized_metadata
    return normalized_payload


def scan_role(
    role_path: str,
    *,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    role_name_override: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
) -> dict[str, Any]:
    """Return the scanner payload as a Python dictionary.

    External orchestrators should prefer this wrapper over importing internal
    scanner helpers directly. The wrapper forces JSON dry-run behavior so the
    caller receives a deterministic, machine-readable payload without writing
    output files.
    """

    payload = run_scan(
        role_path,
        output="scan.json",
        output_format="json",
        compare_role_path=compare_role_path,
        style_readme_path=style_readme_path,
        role_name_override=role_name_override,
        vars_seed_paths=vars_seed_paths,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        readme_config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
        style_guide_skeleton=style_guide_skeleton,
        keep_unknown_style_sections=keep_unknown_style_sections,
        exclude_path_patterns=exclude_path_patterns,
        style_source_path=style_source_path,
        policy_config_path=policy_config_path,
        dry_run=True,
    )
    return json.loads(payload)


def scan_repo(
    repo_url: str,
    *,
    repo_ref: str | None = None,
    repo_role_path: str = ".",
    repo_timeout: int = 60,
    repo_style_readme_path: str | None = None,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    lightweight_readme_only: bool = False,
) -> dict[str, Any]:
    """Clone a repository source, scan the requested role path, and return a dict.

    This mirrors the CLI repo-intake path but remains file-write free for callers
    that want to orchestrate scans programmatically.
    """

    with _repo_scan_workspace() as workspace:
        checkout_dir = workspace / "repo"
        resolved_repo_style_readme_path = repo_style_readme_path
        repo_dir_names = _fetch_repo_directory_names(
            repo_url,
            repo_path=repo_role_path,
            ref=repo_ref,
            timeout=repo_timeout,
        )
        if repo_dir_names is not None and not _repo_path_looks_like_role(
            repo_dir_names
        ):
            raise FileNotFoundError(
                f"repository path does not look like an Ansible role: {repo_role_path}"
            )

        style_candidates = _build_repo_style_readme_candidates(repo_style_readme_path)
        fetched_repo_style_readme_path = None
        for style_candidate in style_candidates:
            fetched_repo_style_readme_path = _fetch_repo_file(
                repo_url,
                style_candidate,
                workspace / "repo-style-readme" / Path(style_candidate).name,
                ref=repo_ref,
                timeout=repo_timeout,
            )
            if fetched_repo_style_readme_path is not None:
                resolved_repo_style_readme_path = style_candidate
                break

        if lightweight_readme_only:
            if not style_candidates:
                raise FileNotFoundError(
                    "lightweight repo scan requires repo_style_readme_path"
                )

            effective_style_readme_path: str | None = None
            if fetched_repo_style_readme_path is not None:
                effective_style_readme_path = str(
                    fetched_repo_style_readme_path.resolve()
                )
            else:
                if repo_dir_names is None:
                    if repo_role_path.strip() in {"", "."}:
                        role_sparse_paths = list(_REQUIRED_ROLE_DIRS)
                    else:
                        role_sparse_paths = [
                            f"{repo_role_path.rstrip('/')}/{required_dir}"
                            for required_dir in _REQUIRED_ROLE_DIRS
                        ]

                    sparse_paths = []
                    for sparse_path in [*role_sparse_paths, *style_candidates]:
                        if sparse_path and sparse_path not in sparse_paths:
                            sparse_paths.append(sparse_path)

                    _clone_repo(
                        repo_url,
                        checkout_dir,
                        repo_ref,
                        repo_timeout,
                        sparse_paths=sparse_paths,
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
                    if not _repo_path_looks_like_role(local_dir_names):
                        raise FileNotFoundError(
                            "repository path does not look like an Ansible role: "
                            f"{repo_role_path}"
                        )

                    for style_candidate in style_candidates:
                        candidate_path = (checkout_dir / style_candidate).resolve()
                        if candidate_path.is_file():
                            effective_style_readme_path = str(candidate_path)
                            resolved_repo_style_readme_path = style_candidate
                            break

            if effective_style_readme_path is None:
                expected = repo_style_readme_path or "README.md"
                raise FileNotFoundError(
                    f"style README not found in repository: {expected}"
                )

            role_stub_dir = workspace / "role-stub"
            role_stub_dir.mkdir(parents=True, exist_ok=True)
            payload = scan_role(
                str(role_stub_dir),
                compare_role_path=compare_role_path,
                style_readme_path=effective_style_readme_path,
                role_name_override=_repo_name_from_url(repo_url),
                vars_seed_paths=vars_seed_paths,
                concise_readme=concise_readme,
                scanner_report_output=scanner_report_output,
                include_vars_main=include_vars_main,
                include_scanner_report_link=include_scanner_report_link,
                readme_config_path=readme_config_path,
                adopt_heading_mode=adopt_heading_mode,
                style_guide_skeleton=style_guide_skeleton,
                keep_unknown_style_sections=keep_unknown_style_sections,
                exclude_path_patterns=exclude_path_patterns,
                style_source_path=style_source_path,
                policy_config_path=policy_config_path,
            )
            return _normalize_repo_style_guide_path(
                payload,
                resolved_repo_style_readme_path,
            )

        _clone_repo(
            repo_url,
            checkout_dir,
            repo_ref,
            repo_timeout,
            sparse_paths=_build_sparse_clone_paths(
                repo_role_path,
                (
                    None
                    if fetched_repo_style_readme_path is not None
                    else style_candidates
                ),
            ),
        )

        role_path = (checkout_dir / repo_role_path).resolve()
        if not role_path.exists() or not role_path.is_dir():
            raise FileNotFoundError(
                f"role path not found in cloned repository: {repo_role_path}"
            )

        effective_style_readme_path = style_readme_path
        if fetched_repo_style_readme_path is not None:
            effective_style_readme_path = str(fetched_repo_style_readme_path.resolve())
        elif style_candidates:
            for style_candidate in style_candidates:
                candidate_path = (checkout_dir / style_candidate).resolve()
                if candidate_path.is_file():
                    effective_style_readme_path = str(candidate_path)
                    resolved_repo_style_readme_path = style_candidate
                    break

        payload = scan_role(
            str(role_path),
            compare_role_path=compare_role_path,
            style_readme_path=effective_style_readme_path,
            role_name_override=_repo_name_from_url(repo_url),
            vars_seed_paths=vars_seed_paths,
            concise_readme=concise_readme,
            scanner_report_output=scanner_report_output,
            include_vars_main=include_vars_main,
            include_scanner_report_link=include_scanner_report_link,
            readme_config_path=readme_config_path,
            adopt_heading_mode=adopt_heading_mode,
            style_guide_skeleton=style_guide_skeleton,
            keep_unknown_style_sections=keep_unknown_style_sections,
            exclude_path_patterns=exclude_path_patterns,
            style_source_path=style_source_path,
            policy_config_path=policy_config_path,
        )
        return _normalize_repo_style_guide_path(
            payload,
            resolved_repo_style_readme_path,
        )


__all__ = ["scan_repo", "scan_role"]
