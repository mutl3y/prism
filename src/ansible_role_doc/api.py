"""Public library API for scanner consumers.

This module provides a stable import surface for external tooling that wants
machine-readable scan results without coupling to CLI internals.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

from .cli import (
    _build_sparse_clone_paths,
    _clone_repo,
    _fetch_repo_directory_names,
    _fetch_repo_file,
    _repo_path_looks_like_role,
    _repo_name_from_url,
)
from .scanner import run_scan


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
    adopt_style_headings: bool | None = None,
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
        adopt_style_headings=adopt_style_headings,
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
    adopt_style_headings: bool | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
) -> dict[str, Any]:
    """Clone a repository source, scan the requested role path, and return a dict.

    This mirrors the CLI repo-intake path but remains file-write free for callers
    that want to orchestrate scans programmatically.
    """

    with tempfile.TemporaryDirectory(prefix="ansible-role-doc-") as tmp_dir:
        checkout_dir = Path(tmp_dir) / "repo"
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
        fetched_repo_style_readme_path = None
        if repo_style_readme_path:
            fetched_repo_style_readme_path = _fetch_repo_file(
                repo_url,
                repo_style_readme_path,
                Path(tmp_dir) / "repo-style-readme" / Path(repo_style_readme_path).name,
                ref=repo_ref,
                timeout=repo_timeout,
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
                    else repo_style_readme_path
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
        elif repo_style_readme_path:
            effective_style_readme_path = str(
                (checkout_dir / repo_style_readme_path).resolve()
            )

        return scan_role(
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
            adopt_style_headings=adopt_style_headings,
            style_guide_skeleton=style_guide_skeleton,
            keep_unknown_style_sections=keep_unknown_style_sections,
            exclude_path_patterns=exclude_path_patterns,
            style_source_path=style_source_path,
            policy_config_path=policy_config_path,
        )


__all__ = ["scan_repo", "scan_role"]
