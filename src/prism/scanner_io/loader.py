"""YAML loading and file discovery helpers for scanner I/O."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import yaml

from prism.scanner_data.di_helpers import get_prepared_policy_or_none


def _resolve_plugin_registry(di: object | None = None):
    if di is None:
        return None
    registry = getattr(di, "plugin_registry", None)
    if registry is not None:
        return registry
    scan_options = getattr(di, "scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options.get("plugin_registry")
    return None


def _resolve_policy_with_registry(resolver, di: object | None = None):
    registry = _resolve_plugin_registry(di)
    if registry is None:
        return resolver(di)
    try:
        return resolver(di, registry=registry)
    except TypeError:
        return resolver(di)


def _get_yaml_parsing_policy(di: object | None = None):
    policy = get_prepared_policy_or_none(di, "yaml_parsing")
    if policy is not None:
        return policy

    # NOTE: Intentional dual-path — soft fallback to registry-resolved default.
    # Loader runs in discovery paths that execute before a prepared_policy_bundle
    # is threaded through (e.g. standalone file-load helpers, pre-scan discovery).
    # Unlike other policy getters, this path does NOT raise on a missing bundle.
    # See FIND-04 in docs/plan/fsrc-gilfoyle-review-20260422/findings.yaml.
    from prism.scanner_plugins.defaults import resolve_yaml_parsing_policy_plugin

    return _resolve_policy_with_registry(resolve_yaml_parsing_policy_plugin, di)


def _role_relative_candidate_path(path: Path, role_root: Path) -> str | None:
    """Return a lexical role-relative path when the candidate lives under the role."""
    try:
        return path.relative_to(role_root).as_posix()
    except ValueError:
        return None


def _format_candidate_failure_path(candidate: Path, role_root: Path) -> str:
    """Return a stable failure-path string without crashing on outside-root symlinks."""
    relpath = _role_relative_candidate_path(candidate, role_root)
    if relpath is not None:
        return relpath
    return candidate.resolve().as_posix()


def iter_role_yaml_candidates(
    role_root: Path,
    *,
    exclude_paths: list[str] | None,
    ignored_dirs: set[str],
    is_relpath_excluded_fn: Callable[[str, list[str] | None], bool],
    is_path_excluded_fn: Callable[[Path, Path, list[str] | None], bool],
):
    """Yield role-local YAML files while honoring ignored and excluded paths."""
    for root, dirs, files in os.walk(str(role_root)):
        dirs[:] = [
            d
            for d in dirs
            if d not in ignored_dirs
            and not is_relpath_excluded_fn(
                _role_relative_candidate_path(Path(root) / d, role_root) or d,
                exclude_paths,
            )
        ]
        for fname in sorted(files):
            candidate = Path(root) / fname
            if candidate.suffix.lower() not in {".yml", ".yaml"}:
                continue
            if is_path_excluded_fn(candidate, role_root, exclude_paths):
                continue
            yield candidate


def parse_yaml_candidate(
    candidate: Path,
    role_root: Path,
    *,
    di: object | None = None,
) -> dict[str, object] | None:
    """Parse one YAML candidate and return a failure payload when parsing fails."""
    policy = _get_yaml_parsing_policy(di)
    parse_fn = getattr(policy, "parse_yaml_candidate", None)
    if callable(parse_fn):
        parsed_failure = parse_fn(candidate, role_root)
        if isinstance(parsed_failure, dict) or parsed_failure is None:
            return parsed_failure

    try:
        text = candidate.read_text(encoding="utf-8")
        yaml.safe_load(text)
        return None
    except (OSError, UnicodeDecodeError) as exc:
        return {
            "file": _format_candidate_failure_path(candidate, role_root),
            "line": None,
            "column": None,
            "error": f"read_error: {exc}",
        }
    except (yaml.YAMLError, ValueError) as exc:
        mark = getattr(exc, "problem_mark", None)
        line = int(mark.line) + 1 if mark is not None else None
        column = int(mark.column) + 1 if mark is not None else None
        problem = str(getattr(exc, "problem", "") or "").strip()
        if not problem:
            problem = str(exc).splitlines()[0].strip()
        return {
            "file": _format_candidate_failure_path(candidate, role_root),
            "line": line,
            "column": column,
            "error": problem,
        }


def map_argument_spec_type(spec_type: object) -> str:
    """Map argument-spec type labels into scanner variable type labels."""
    if not isinstance(spec_type, str):
        return "documented"
    normalized = spec_type.strip().lower()
    if normalized in {"str", "raw", "path", "bytes", "bits"}:
        return "string"
    if normalized in {"int"}:
        return "int"
    if normalized in {"bool"}:
        return "bool"
    if normalized in {"dict"}:
        return "dict"
    if normalized in {"list"}:
        return "list"
    if normalized in {"float"}:
        return "string"
    return "documented"


def collect_yaml_parse_failures(
    role_path: str,
    exclude_paths: list[str] | None,
    iter_yaml_candidates_fn: Callable[[Path, list[str] | None], list[Path]],
    *,
    di: object | None = None,
) -> list[dict[str, object]]:
    """Collect YAML parse failures with file/line context across a role tree."""
    role_root = Path(role_path).resolve()
    failures: list[dict[str, object]] = []

    for candidate in iter_yaml_candidates_fn(
        role_root,
        exclude_paths,
    ):
        failure = parse_yaml_candidate(candidate, role_root, di=di)
        if failure is not None:
            failures.append(failure)

    return failures


def load_yaml_file(path: Path, *, di: object | None = None) -> object:
    """Load and parse a YAML file safely."""
    policy = _get_yaml_parsing_policy(di)
    load_fn = getattr(policy, "load_yaml_file", None)
    if callable(load_fn):
        return load_fn(path)

    try:
        text = path.read_text(encoding="utf-8")
        return yaml.safe_load(text)
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
        return None
