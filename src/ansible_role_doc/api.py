"""Public library API for scanner consumers.

This module provides a stable import surface for external tooling that wants
machine-readable scan results without coupling to CLI internals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import yaml

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


def _load_yaml_document(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(loaded, (dict, list)):
        return loaded
    return None


def _requirements_entries_from_document(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, list):
        return [item for item in document if isinstance(item, dict)]
    if isinstance(document, dict):
        entries: list[dict[str, Any]] = []
        for key in ("collections", "roles"):
            value = document.get(key)
            if isinstance(value, list):
                entries.extend(item for item in value if isinstance(item, dict))
        return entries
    return []


def _collection_dependency_key(entry: dict[str, Any], index: int) -> str | None:
    name = str(entry.get("name") or "").strip()
    if name and "." in name:
        return name
    src = str(entry.get("src") or "").strip()
    if src and "." in src and "/" not in src:
        return src
    return None


def _role_dependency_key(entry: dict[str, Any], index: int) -> str:
    name = str(entry.get("name") or "").strip()
    if name:
        return name
    src = str(entry.get("src") or "").strip()
    if src:
        return src
    return f"unknown:{index}"


def _merge_dependency_entry(
    bucket: dict[str, dict[str, Any]],
    *,
    key: str,
    dep_type: str,
    entry: dict[str, Any],
    source: str,
) -> None:
    item = bucket.setdefault(
        key,
        {
            "key": key,
            "type": dep_type,
            "name": str(entry.get("name") or "").strip() or None,
            "src": str(entry.get("src") or "").strip() or None,
            "versions": set(),
            "sources": set(),
            "raw": [],
        },
    )
    version = str(entry.get("version") or "").strip()
    if version:
        item["versions"].add(version)
    item["sources"].add(source)
    item["raw"].append(dict(entry))


def _finalize_dependency_bucket(
    bucket: dict[str, dict[str, Any]], conflict_label: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    conflicts: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for key in sorted(bucket):
        item = bucket[key]
        versions = sorted(item["versions"])
        sources = sorted(item["sources"])
        finalized = {
            "key": item["key"],
            "type": item["type"],
            "name": item["name"],
            "src": item["src"],
            "version": versions[0] if len(versions) == 1 else None,
            "versions": versions,
            "sources": sources,
        }
        items.append(finalized)
        if len(versions) > 1:
            conflicts.append(
                {
                    "conflict": conflict_label,
                    "key": key,
                    "versions": versions,
                    "sources": sources,
                }
            )
    return items, conflicts


def _aggregate_collection_dependencies(collection_root: Path) -> dict[str, Any]:
    collection_bucket: dict[str, dict[str, Any]] = {}
    role_bucket: dict[str, dict[str, Any]] = {}

    sources: list[tuple[Path, str]] = []
    sources.append(
        (
            collection_root / "collections" / "requirements.yml",
            "collections/requirements.yml",
        )
    )
    sources.append(
        (
            collection_root / "roles" / "requirements.yml",
            "roles/requirements.yml",
        )
    )

    roles_dir = collection_root / "roles"
    if roles_dir.is_dir():
        for role_dir in sorted(path for path in roles_dir.iterdir() if path.is_dir()):
            rel_source = f"roles/{role_dir.name}/meta/requirements.yml"
            sources.append((role_dir / "meta" / "requirements.yml", rel_source))

    for req_path, source_label in sources:
        document = _load_yaml_document(req_path)
        entries = _requirements_entries_from_document(document)
        for index, entry in enumerate(entries):
            entry_type = str(entry.get("type") or "").strip().lower()
            if req_path.parts[-2:] == ("collections", "requirements.yml"):
                entry_type = "collection"
            elif req_path.parts[-2:] == ("roles", "requirements.yml"):
                entry_type = "role"

            if entry_type == "collection":
                key = _collection_dependency_key(entry, index)
                if key:
                    _merge_dependency_entry(
                        collection_bucket,
                        key=key,
                        dep_type="collection",
                        entry=entry,
                        source=source_label,
                    )
                continue

            key = _role_dependency_key(entry, index)
            _merge_dependency_entry(
                role_bucket,
                key=key,
                dep_type="role",
                entry=entry,
                source=source_label,
            )

    collections, collection_conflicts = _finalize_dependency_bucket(
        collection_bucket,
        "version_conflict",
    )
    roles, role_conflicts = _finalize_dependency_bucket(
        role_bucket,
        "dependency_conflict",
    )

    return {
        "collections": collections,
        "roles": roles,
        "conflicts": [*collection_conflicts, *role_conflicts],
    }


def scan_collection(
    collection_path: str,
    *,
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
) -> dict[str, Any]:
    """Scan an Ansible collection root and return per-role payloads + metadata."""
    root = Path(collection_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"collection path not found: {collection_path}")

    galaxy_path = root / "galaxy.yml"
    roles_dir = root / "roles"
    if not galaxy_path.is_file() or not roles_dir.is_dir():
        raise FileNotFoundError(
            "collection root must include galaxy.yml and roles/ directory"
        )

    galaxy_doc = _load_yaml_document(galaxy_path)
    galaxy_metadata = galaxy_doc if isinstance(galaxy_doc, dict) else {}

    role_entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for role_dir in sorted(path for path in roles_dir.iterdir() if path.is_dir()):
        try:
            payload = scan_role(
                str(role_dir),
                compare_role_path=compare_role_path,
                style_readme_path=style_readme_path,
                role_name_override=role_dir.name,
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
            role_entries.append(
                {
                    "role": role_dir.name,
                    "path": str(role_dir),
                    "payload": payload,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "role": role_dir.name,
                    "path": str(role_dir),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    dependencies = _aggregate_collection_dependencies(root)
    return {
        "collection": {
            "path": str(root),
            "metadata": galaxy_metadata,
        },
        "dependencies": dependencies,
        "roles": role_entries,
        "failures": failures,
        "summary": {
            "total_roles": len(role_entries) + len(failures),
            "scanned_roles": len(role_entries),
            "failed_roles": len(failures),
        },
    }


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


__all__ = ["scan_collection", "scan_repo", "scan_role"]
