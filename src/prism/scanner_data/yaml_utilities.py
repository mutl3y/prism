"""Pure YAML utility functions and helpers (data layer)."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Callable, TypeGuard, TypeVar

import yaml

if TYPE_CHECKING:
    from prism.scanner_data.contracts_request import YamlParseFailure


logger = logging.getLogger(__name__)

_InputT = TypeVar("_InputT")
_ResultT = TypeVar("_ResultT")

# Keep the parallel path parked behind a conservative threshold for now.
# The current benchmarked workloads regressed at 24- and 100-file batches on
# this machine, so current scans stay sequential by default. Retain this as a
# future-expansion seam for materially larger workloads, and only lower the
# gate when a workload-shaped benchmark proves a better cutoff.
_PARALLEL_YAML_BATCH_THRESHOLD = 128


def _is_yaml_parse_failure(value: object) -> TypeGuard[YamlParseFailure]:
    """Validate that a value matches the YamlParseFailure structure."""
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


def _recommended_parallel_workers(item_count: int) -> int:
    """Keep present-day YAML batches sequential until larger workloads justify a pool.

    The ordered-parallel loader path is intentionally retained for future
    repo-scale expansion, but current benchmarked batches regress on this
    machine unless the fan-out is materially larger.
    """
    if item_count < _PARALLEL_YAML_BATCH_THRESHOLD:
        return 1
    cpu_count = os.cpu_count() or 1
    return min(item_count, cpu_count + 4, 32)


def _ordered_parallel_map(
    items: list[_InputT],
    worker: Callable[[_InputT], _ResultT],
) -> list[_ResultT]:
    """Preserve input order while keeping the parallel path available for later.

    This helper is intentionally not dead code: current scans fall back to the
    sequential branch below the threshold, while larger future YAML batches can
    reuse the same ordering-preserving seam without reintroducing the helper.
    """
    max_workers = _recommended_parallel_workers(len(items))
    if max_workers <= 1:
        return [worker(item) for item in items]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(worker, items))


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
    # Import policy resolver here to avoid circular imports at module level
    from prism.scanner_io.loader import _get_yaml_parsing_policy

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
    candidates = list(
        iter_yaml_candidates_fn(
            role_root,
            exclude_paths,
        )
    )

    def _parse_candidate(candidate: Path) -> YamlParseFailure | None:
        return parse_yaml_candidate(candidate, role_root, di=di)

    failures = _ordered_parallel_map(candidates, _parse_candidate)

    return [failure for failure in failures if failure is not None]
