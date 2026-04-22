"""Role quality comparison facade helpers with injectable dependencies.

Only the three role-comparison primitives are ported here.
Scanner execution facades (orchestrate_scan_payload, execute_scan_with_context)
live in scanner_kernel territory and are not duplicated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def collect_role_contents(
    *,
    role_path: str,
    exclude_paths: list[str] | None,
    is_path_excluded: Callable[[Path, Path, list[str] | None], bool],
    load_meta: Callable[..., dict],
    extract_role_features: Callable[..., dict],
) -> dict:
    """Collect lists of files from common role subdirectories."""
    rp = Path(role_path).resolve()
    result: dict = {}
    for name in (
        "handlers",
        "tasks",
        "templates",
        "files",
        "tests",
        "defaults",
        "vars",
    ):
        subdir = rp / name
        entries: list[str] = []
        if subdir.exists() and subdir.is_dir():
            for path in sorted(subdir.rglob("*")):
                if path.is_file():
                    if is_path_excluded(path, rp.resolve(), exclude_paths):
                        continue
                    entries.append(str(path.relative_to(rp)))
        result[name] = entries
    meta_warnings: list[str] = []
    try:
        result["meta"] = load_meta(role_path, warning_collector=meta_warnings)
    except Exception as exc:
        result["meta"] = {}
        meta_warnings.append(f"ROLE_METADATA_LOAD_FAILED: {exc}")
    if meta_warnings:
        result["meta_load_warnings"] = meta_warnings
    result["features"] = extract_role_features(role_path, exclude_paths=exclude_paths)
    return result


def compute_quality_metrics(
    *,
    role_path: str,
    exclude_paths: list[str] | None,
    collect_role_contents: Callable[[str, list[str] | None], dict],
    load_variables: Callable[..., dict],
    scan_for_default_filters: Callable[[str, list[str] | None], list],
) -> dict:
    """Compute lightweight role quality metrics for comparison output."""
    contents = collect_role_contents(role_path, exclude_paths)
    features = contents.get("features", {}) if isinstance(contents, dict) else {}
    variables = load_variables(role_path=role_path, exclude_paths=exclude_paths)

    present_dirs = 0
    for section in (
        "tasks",
        "defaults",
        "vars",
        "handlers",
        "templates",
        "files",
        "tests",
    ):
        if contents.get(section):
            present_dirs += 1

    defaults_hits = len(scan_for_default_filters(role_path, exclude_paths))
    tasks_scanned = int(features.get("tasks_scanned", 0) or 0)
    unique_modules_raw = str(features.get("unique_modules", "none"))
    unique_modules = (
        0
        if unique_modules_raw == "none"
        else len([item for item in unique_modules_raw.split(",") if item.strip()])
    )

    score = (
        present_dirs * 10
        + min(len(variables), 20)
        + min(tasks_scanned, 20)
        + min(unique_modules * 3, 15)
        + min(defaults_hits, 10)
    )
    score = max(0, min(100, score))

    return {
        "score": score,
        "present_dirs": present_dirs,
        "variable_count": len(variables),
        "task_count": tasks_scanned,
        "module_count": unique_modules,
        "default_filter_count": defaults_hits,
    }


def build_comparison_report(
    *,
    target_role_path: str,
    baseline_role_path: str,
    exclude_paths: list[str] | None,
    compute_quality_metrics: Callable[[str, list[str] | None], dict],
) -> dict:
    """Build a compact comparison between a target role and baseline role."""
    target = compute_quality_metrics(target_role_path, exclude_paths)
    baseline = compute_quality_metrics(baseline_role_path, exclude_paths)

    return {
        "baseline_path": str(Path(baseline_role_path).resolve()),
        "target_score": target["score"],
        "baseline_score": baseline["score"],
        "score_delta": target["score"] - baseline["score"],
        "metrics": {
            "present_dirs": {
                "target": target["present_dirs"],
                "baseline": baseline["present_dirs"],
                "delta": target["present_dirs"] - baseline["present_dirs"],
            },
            "variable_count": {
                "target": target["variable_count"],
                "baseline": baseline["variable_count"],
                "delta": target["variable_count"] - baseline["variable_count"],
            },
            "task_count": {
                "target": target["task_count"],
                "baseline": baseline["task_count"],
                "delta": target["task_count"] - baseline["task_count"],
            },
            "module_count": {
                "target": target["module_count"],
                "baseline": baseline["module_count"],
                "delta": target["module_count"] - baseline["module_count"],
            },
            "default_filter_count": {
                "target": target["default_filter_count"],
                "baseline": baseline["default_filter_count"],
                "delta": target["default_filter_count"]
                - baseline["default_filter_count"],
            },
        },
    }
