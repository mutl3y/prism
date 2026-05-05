"""Shared repository-intake helpers for fsrc API and CLI surfaces."""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Protocol, TypedDict, cast

from prism.errors import (
    REPO_CLONE_FAILED,
    REPO_CONTENT_INVALID,
    REPO_SCAN_PAYLOAD_JSON_INVALID,
    REPO_SCAN_PAYLOAD_SHAPE_INVALID,
    REPO_SCAN_PAYLOAD_TYPE_INVALID,
    PrismRuntimeError,
)
from prism.scanner_data.contracts_output import RunScanOutputPayload


REPO_SERVICE_CANONICAL_SURFACE: tuple[str, ...] = (
    "build_repo_intake_components",
    "clone_repo",
    "normalize_repo_scan_payload",
    "repo_scan_facade",
    "repo_scan_workspace",
    "resolve_repo_scan_target",
    "run_repo_scan",
)
REPO_SERVICE_COMPATIBILITY_SEAMS: tuple[str, ...] = (
    "RepoScanTarget",
    "RepoScanRunResult",
    "os",
)


@dataclass(frozen=True)
class RepoScanTarget:
    """Resolved role + style guide location for repo-scan orchestration."""

    role_path: Path
    effective_style_readme_path: str | None
    resolved_repo_style_readme_path: str | None


@dataclass(frozen=True)
class RepoScanRunResult:
    """Structured result for repo intake + downstream scan output."""

    checkout: RepoScanTarget
    scan_output: RepoScanPayload


RepoScanPayload = RunScanOutputPayload | dict[str, Any] | str


class RepoScanRoleRunner(Protocol):
    """Protocol-owned seam for the downstream role scan used by repo intake."""

    def __call__(
        self,
        role_path: str,
        *,
        style_readme_path: str | None = None,
        role_name_override: str | None = None,
    ) -> RepoScanPayload: ...


class CloneRepoFn(Protocol):
    def __call__(
        self,
        repo_url: str,
        destination: Path,
        *,
        ref: str | None = None,
        timeout: int = 60,
    ) -> Path: ...


class ResolveRepoScanTargetFn(Protocol):
    def __call__(
        self,
        *,
        repo_url: str,
        workspace: Path,
        repo_role_path: str,
        repo_style_readme_path: str | None,
        style_readme_path: str | None,
        repo_ref: str | None,
        repo_timeout: int,
        lightweight_readme_only: bool,
        clone_repo_fn: CloneRepoFn | None = None,
    ) -> RepoScanTarget: ...


class NormalizeRepoScanPayloadFn(Protocol):
    def __call__(
        self,
        payload: RepoScanPayload,
        *,
        repo_style_readme_path: str | None = None,
        scanner_report_relpath: str | None = None,
    ) -> RepoScanPayload: ...


class RunRepoScanFacadeFn(Protocol):
    def __call__(
        self,
        *,
        repo_url: str,
        repo_role_path: str,
        repo_style_readme_path: str | None,
        style_readme_path: str | None,
        repo_ref: str | None,
        repo_timeout: int,
        lightweight_readme_only: bool,
        scan_role_fn: RepoScanRoleRunner,
        resolve_repo_scan_target_fn: ResolveRepoScanTargetFn | None = None,
        repo_scan_workspace_fn: RepoScanWorkspaceFactory | None = None,
        normalize_repo_scan_payload_fn: NormalizeRepoScanPayloadFn | None = None,
    ) -> RepoScanPayload: ...


class RunRepoScanExecutionFn(Protocol):
    def __call__(
        self,
        *,
        repo_url: str,
        repo_role_path: str,
        repo_style_readme_path: str | None,
        style_readme_path: str | None,
        repo_ref: str | None,
        repo_timeout: int,
        lightweight_readme_only: bool,
        scan_role_fn: RepoScanRoleRunner,
        repo_scan_workspace_fn: RepoScanWorkspaceFactory | None = None,
        resolve_repo_scan_target_fn: ResolveRepoScanTargetFn | None = None,
    ) -> RepoScanRunResult: ...


class RepoScanIntakeComponents(TypedDict):
    clone_repo: CloneRepoFn
    repo_scan_workspace: RepoScanWorkspaceFactory
    resolve_repo_scan_target: ResolveRepoScanTargetFn
    normalize_repo_scan_payload: NormalizeRepoScanPayloadFn
    run_repo_scan: RunRepoScanExecutionFn


class BuildRepoIntakeComponentsFn(Protocol):
    def __call__(self) -> RepoScanIntakeComponents: ...


class RepoScanWorkspaceFactory(Protocol):
    def __call__(self, base_dir: str | None = None) -> AbstractContextManager[Path]: ...


@contextmanager
def repo_scan_workspace(base_dir: str | None = None):
    with tempfile.TemporaryDirectory(dir=base_dir) as workspace_dir:
        yield Path(workspace_dir)


def _resolve_repo_relative_path(
    repo_root: Path,
    repo_path: str,
    *,
    field_name: str,
) -> Path:
    repo_root_resolved = repo_root.resolve()
    candidate = Path(repo_path)
    if candidate.is_absolute():
        raise PrismRuntimeError(
            code=REPO_CONTENT_INVALID,
            category="repo",
            message=f"{field_name} must be repository-relative: {repo_path}",
            detail={
                "field": field_name,
                "value": repo_path,
                "repo_root": str(repo_root_resolved),
            },
        )

    resolved = (repo_root_resolved / candidate).resolve()
    try:
        resolved.relative_to(repo_root_resolved)
    except ValueError as exc:
        raise PrismRuntimeError(
            code=REPO_CONTENT_INVALID,
            category="repo",
            message=(
                f"{field_name} resolves outside repository root {repo_root_resolved!s}"
            ),
            detail={
                "field": field_name,
                "value": repo_path,
                "repo_root": str(repo_root_resolved),
            },
        ) from exc

    return resolved


def clone_repo(
    repo_url: str,
    destination: Path,
    *,
    ref: str | None = None,
    timeout: int = 60,
) -> Path:
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend(["--", repo_url, str(destination)])
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise PrismRuntimeError(
            code=REPO_CLONE_FAILED,
            category="repo",
            message=f"Failed to clone repository: {repo_url}",
            detail={"repo_url": repo_url},
        ) from exc
    return destination


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
    clone_repo_fn=None,
) -> RepoScanTarget:
    clone_repo_fn = clone_repo_fn or clone_repo

    source_path = Path(repo_url).expanduser()
    if source_path.exists():
        repo_root = source_path.resolve()
    else:
        repo_root = clone_repo_fn(
            repo_url,
            workspace / "repo",
            ref=repo_ref,
            timeout=repo_timeout,
        ).resolve()

    role_path = _resolve_repo_relative_path(
        repo_root,
        repo_role_path,
        field_name="repo_role_path",
    )
    if not role_path.exists() or not role_path.is_dir():
        raise PrismRuntimeError(
            code=REPO_CONTENT_INVALID,
            category="repo",
            message=f"Repository role path does not exist: {repo_role_path}",
            detail={"repo_role_path": repo_role_path},
        )

    resolved_repo_style = None
    if repo_style_readme_path:
        candidate = _resolve_repo_relative_path(
            repo_root,
            repo_style_readme_path,
            field_name="repo_style_readme_path",
        )
        if candidate.exists() and candidate.is_file():
            resolved_repo_style = str(candidate)

    effective_style = style_readme_path or resolved_repo_style
    if lightweight_readme_only:
        role_path = repo_root

    return RepoScanTarget(
        role_path=role_path,
        effective_style_readme_path=effective_style,
        resolved_repo_style_readme_path=resolved_repo_style,
    )


def normalize_repo_scan_payload(
    payload: RepoScanPayload,
    *,
    repo_style_readme_path: str | None = None,
    scanner_report_relpath: str | None = None,
) -> RepoScanPayload:
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(REPO_SCAN_PAYLOAD_JSON_INVALID) from exc
        normalized = normalize_repo_scan_payload(
            parsed,
            repo_style_readme_path=repo_style_readme_path,
            scanner_report_relpath=scanner_report_relpath,
        )
        return json.dumps(normalized, indent=2, sort_keys=True)

    if not isinstance(payload, dict):
        raise RuntimeError(REPO_SCAN_PAYLOAD_TYPE_INVALID)

    payload_dict = cast(dict[str, Any], payload)

    metadata_value = payload_dict.get("metadata")
    if metadata_value is None:
        metadata_dict: dict[str, Any] = {}
        payload_dict["metadata"] = metadata_dict
    elif isinstance(metadata_value, dict):
        metadata_dict = metadata_value
    else:
        raise RuntimeError(REPO_SCAN_PAYLOAD_SHAPE_INVALID)

    style_guide_value = metadata_dict.get("style_guide")
    if style_guide_value is None:
        style_guide_dict: dict[str, Any] = {}
        metadata_dict["style_guide"] = style_guide_dict
    elif isinstance(style_guide_value, dict):
        style_guide_dict = style_guide_value
    else:
        raise RuntimeError(REPO_SCAN_PAYLOAD_SHAPE_INVALID)

    if repo_style_readme_path:
        style_guide_dict["path"] = repo_style_readme_path
    if scanner_report_relpath:
        metadata_dict["scanner_report_relpath"] = scanner_report_relpath

    return payload


def run_repo_scan(
    *,
    repo_url: str,
    repo_role_path: str,
    repo_style_readme_path: str | None,
    style_readme_path: str | None,
    repo_ref: str | None,
    repo_timeout: int,
    lightweight_readme_only: bool,
    scan_role_fn: RepoScanRoleRunner,
    repo_scan_workspace_fn: RepoScanWorkspaceFactory | None = None,
    resolve_repo_scan_target_fn: ResolveRepoScanTargetFn | None = None,
) -> RepoScanRunResult:
    resolve_repo_scan_target_fn = (
        resolve_repo_scan_target_fn or resolve_repo_scan_target
    )
    repo_scan_workspace_fn = repo_scan_workspace_fn or repo_scan_workspace

    with repo_scan_workspace_fn() as workspace:
        checkout = resolve_repo_scan_target_fn(
            repo_url=repo_url,
            workspace=workspace,
            repo_role_path=repo_role_path,
            repo_style_readme_path=repo_style_readme_path,
            style_readme_path=style_readme_path,
            repo_ref=repo_ref,
            repo_timeout=repo_timeout,
            lightweight_readme_only=lightweight_readme_only,
        )
        role_name_override = Path(repo_role_path.rstrip("/") or ".").name or "role"
        scan_output = scan_role_fn(
            str(checkout.role_path),
            style_readme_path=checkout.effective_style_readme_path,
            role_name_override=role_name_override,
        )

    return RepoScanRunResult(checkout=checkout, scan_output=scan_output)


def _run_repo_scan(
    *,
    repo_url: str,
    repo_role_path: str,
    repo_style_readme_path: str | None,
    style_readme_path: str | None,
    repo_ref: str | None,
    repo_timeout: int,
    lightweight_readme_only: bool,
    scan_role_fn: RepoScanRoleRunner,
    resolve_repo_scan_target_fn: ResolveRepoScanTargetFn | None = None,
    repo_scan_workspace_fn: RepoScanWorkspaceFactory | None = None,
    normalize_repo_scan_payload_fn: NormalizeRepoScanPayloadFn | None = None,
) -> RepoScanPayload:
    normalize_payload = (
        normalize_repo_scan_payload
        if normalize_repo_scan_payload_fn is None
        else normalize_repo_scan_payload_fn
    )

    run_result = run_repo_scan(
        repo_url=repo_url,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        style_readme_path=style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        lightweight_readme_only=lightweight_readme_only,
        scan_role_fn=scan_role_fn,
        repo_scan_workspace_fn=repo_scan_workspace_fn,
        resolve_repo_scan_target_fn=resolve_repo_scan_target_fn,
    )

    return normalize_payload(
        run_result.scan_output,
        repo_style_readme_path=run_result.checkout.resolved_repo_style_readme_path,
    )


def build_repo_intake_components() -> RepoScanIntakeComponents:
    return {
        "clone_repo": clone_repo,
        "repo_scan_workspace": repo_scan_workspace,
        "resolve_repo_scan_target": resolve_repo_scan_target,
        "normalize_repo_scan_payload": normalize_repo_scan_payload,
        "run_repo_scan": run_repo_scan,
    }


@dataclass(frozen=True)
class RepoScanFacade:
    build_repo_intake_components: BuildRepoIntakeComponentsFn
    clone_repo: CloneRepoFn
    normalize_repo_scan_payload: NormalizeRepoScanPayloadFn
    repo_scan_workspace: RepoScanWorkspaceFactory
    resolve_repo_scan_target: ResolveRepoScanTargetFn
    run_repo_scan: RunRepoScanFacadeFn


repo_scan_facade = RepoScanFacade(
    build_repo_intake_components=build_repo_intake_components,
    clone_repo=clone_repo,
    normalize_repo_scan_payload=normalize_repo_scan_payload,
    repo_scan_workspace=repo_scan_workspace,
    resolve_repo_scan_target=resolve_repo_scan_target,
    run_repo_scan=_run_repo_scan,
)
