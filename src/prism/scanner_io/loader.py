"""YAML loading and file discovery helpers for scanner I/O."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Callable, TypeGuard, cast

import yaml

from prism.errors import PrismRuntimeError, category_for_code

if TYPE_CHECKING:
    from prism.scanner_data.contracts_request import (
        PreparedYAMLParsingPolicy,
        YamlParseFailure,
    )


logger = logging.getLogger(__name__)


def build_yaml_load_error(path: Path, exc: Exception) -> PrismRuntimeError:
    return PrismRuntimeError(
        code="yaml_load_error",
        category=category_for_code("yaml_load_error"),
        message=f"{path}: {exc}",
        detail={
            "path": str(path),
            "error_type": type(exc).__name__,
        },
    )


def _is_yaml_parse_failure(value: object) -> TypeGuard[YamlParseFailure]:
    if not isinstance(value, dict):
        return False
    file_value = value.get("file")
    line_value = value.get("line")
    column_value = value.get("column")
    error_value = value.get("error")
    return (
        isinstance(file_value, str)
        and (line_value is None or isinstance(line_value, int))
        and (column_value is None or isinstance(column_value, int))
        and isinstance(error_value, str)
    )


def _resolve_plugin_registry(di: object | None = None):
    """Extract registry from DI without bootstrap fallback.

    Loader standalone contract: returns None when no DI registry is available.
    Does NOT fall back to bootstrap singleton, unlike defaults._resolve_registry.
    """
    from prism.scanner_plugins.defaults import _get_registry_from_di

    registry = _get_registry_from_di(di)
    if registry is not None:
        logger.debug(
            "YAML parsing policy resolution: using DI.plugin_registry override"
        )
        return registry
    logger.debug("YAML parsing policy resolution: no DI registry available")
    return None


def _resolve_policy_with_registry(resolver, di: object | None = None):
    registry = _resolve_plugin_registry(di)
    if registry is None:
        logger.debug(
            "YAML parsing policy resolution: invoking resolver without registry override"
        )
        return resolver(di)
    logger.debug(
        "YAML parsing policy resolution: invoking resolver with registry override"
    )
    return resolver(di, registry=registry)


def _get_yaml_parsing_policy(di: object | None = None) -> PreparedYAMLParsingPolicy:
    """Resolve YAML parsing policy from prepared bundle or registry fallback.

    Returns PreparedYAMLParsingPolicy with 'parse_yaml_candidate' and 'load_yaml_file'
    callable members.
    """
    from prism.scanner_core.di_helpers import get_prepared_policy_or_none

    policy = get_prepared_policy_or_none(di, "yaml_parsing")
    if policy is not None:
        logger.debug(
            "YAML parsing policy resolution: using prepared_policy_bundle.yaml_parsing"
        )
        return cast("PreparedYAMLParsingPolicy", policy)

    # NOTE: Intentional dual-path — soft fallback to registry-resolved default.
    # Loader runs in discovery paths that execute before a prepared_policy_bundle
    # is threaded through (e.g. standalone file-load helpers, pre-scan discovery).
    # Unlike other policy getters, this path does NOT raise on a missing bundle.
    from prism.scanner_plugins.defaults import (
        resolve_yaml_parsing_policy_plugin as _resolve_yaml_plugin,
    )

    return _resolve_policy_with_registry(_resolve_yaml_plugin, di)


def _role_relative_candidate_path(path: Path, role_root: Path) -> str | None:
    """Return a lexical role-relative path when the candidate lives under the role."""
    try:
        return path.relative_to(role_root).as_posix()
    except ValueError:
        return None


def format_candidate_failure_path(candidate: Path, role_root: Path) -> str:
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
) -> YamlParseFailure | None:
    """Parse one YAML candidate and return a failure payload when parsing fails.

    Returns None on successful parse, or a YamlParseFailure payload on parse
    failure. The payload preserves the existing four-key mapping and current
    error-string prefixes.
    """
    policy = _get_yaml_parsing_policy(di)
    parse_fn = getattr(policy, "parse_yaml_candidate", None)
    if callable(parse_fn):
        parsed_failure = parse_fn(candidate, role_root)
        if parsed_failure is None or _is_yaml_parse_failure(parsed_failure):
            return parsed_failure

    try:
        text = candidate.read_text(encoding="utf-8")
        yaml.safe_load(text)
        return None
    except OSError as exc:
        logger.warning(
            "parse_yaml_candidate: IO error (%s) for %s",
            type(exc).__name__,
            candidate,
            exc_info=True,
        )
        return {
            "file": format_candidate_failure_path(candidate, role_root),
            "line": None,
            "column": None,
            "error": f"io_error ({type(exc).__name__}): {exc}",
        }
    except UnicodeDecodeError as exc:
        logger.warning(
            "parse_yaml_candidate: encoding error for %s", candidate, exc_info=True
        )
        return {
            "file": format_candidate_failure_path(candidate, role_root),
            "line": None,
            "column": None,
            "error": f"encoding_error: {exc}",
        }
    except yaml.YAMLError as exc:
        logger.warning(
            "parse_yaml_candidate: YAML parse error (%s) for %s",
            type(exc).__name__,
            candidate,
            exc_info=True,
        )
        mark = getattr(exc, "problem_mark", None)
        line = int(mark.line) + 1 if mark is not None else None
        column = int(mark.column) + 1 if mark is not None else None
        problem = str(getattr(exc, "problem", "") or "").strip()
        if not problem:
            problem = str(exc).splitlines()[0].strip()
        return {
            "file": format_candidate_failure_path(candidate, role_root),
            "line": line,
            "column": column,
            "error": f"yaml_error ({type(exc).__name__}): {problem}",
        }
    except ValueError as exc:
        logger.warning(
            "parse_yaml_candidate: value error for %s", candidate, exc_info=True
        )
        return {
            "file": format_candidate_failure_path(candidate, role_root),
            "line": None,
            "column": None,
            "error": f"value_error: {exc}",
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
) -> list[YamlParseFailure]:
    """Collect YAML parse failures with file/line context across a role tree."""
    role_root = Path(role_path).resolve()
    failures: list[YamlParseFailure] = []

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
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        logger.warning("load_yaml_file failed for %s", path, exc_info=True)
        raise build_yaml_load_error(path, exc) from exc
