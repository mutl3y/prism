"""Facade helper seams extracted from scanner module.

These helpers keep scanner.py thin while preserving behavior via explicit
dependency injection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from prism.scanner_data.contracts_output import RunScanOutputPayload
from prism.scanner_data.contracts_request import PolicyContext


def orchestrate_scan_payload(
    *,
    role_path: str,
    scan_options: dict[str, Any],
    di_container_cls: type,
    scanner_context_cls: type,
    build_run_scan_options_fn: Callable[..., dict[str, Any]],
    prepare_scan_context_fn: Callable[..., dict[str, Any]],
) -> RunScanOutputPayload:
    """Execute a scan via ScannerContext and return the in-memory payload."""
    container = di_container_cls(role_path=role_path, scan_options=scan_options)
    context = scanner_context_cls(
        di=container,
        role_path=role_path,
        scan_options=scan_options,
        build_run_scan_options_fn=build_run_scan_options_fn,
        prepare_scan_context_fn=prepare_scan_context_fn,
    )
    return cast(RunScanOutputPayload, context.orchestrate_scan())


def execute_scan_with_context(
    *,
    role_path: str,
    scan_options: dict[str, Any],
    output: str,
    output_format: str,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    template: str | None,
    dry_run: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    di_container_cls: type,
    scanner_context_cls: type,
    build_run_scan_options_fn: Callable[..., dict[str, Any]],
    prepare_scan_context_fn: Callable[..., dict[str, Any]],
    build_emit_scan_outputs_args_fn: Callable[..., dict[str, Any]],
    emit_scan_outputs_fn: Callable[[dict[str, Any]], str | bytes],
) -> str | bytes:
    """Execute a scan via ScannerContext and forward results to output emission."""
    payload = orchestrate_scan_payload(
        role_path=role_path,
        scan_options=scan_options,
        di_container_cls=di_container_cls,
        scanner_context_cls=scanner_context_cls,
        build_run_scan_options_fn=build_run_scan_options_fn,
        prepare_scan_context_fn=prepare_scan_context_fn,
    )
    emit_args = build_emit_scan_outputs_args_fn(
        output=output,
        output_format=output_format,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_scanner_report_link=include_scanner_report_link,
        payload=payload,
        template=template,
        dry_run=dry_run,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
    )
    return emit_scan_outputs_fn(emit_args)


def collect_role_contents(
    *,
    role_path: str,
    exclude_paths: list[str] | None,
    is_path_excluded: Callable[[Path, Path, list[str] | None], bool],
    load_meta: Callable[..., dict],
    extract_role_features: Callable[..., dict],
) -> dict:
    """Collect lists of files from common role subdirectories."""
    rp = Path(role_path)
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


def collect_scan_artifacts(
    *,
    role_path: str,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
    marker_prefix: str,
    load_variables: Callable[[str, bool, list[str] | None], dict],
    load_requirements: Callable[[str], list],
    scan_for_default_filters: Callable[[str, list[str] | None], list[dict]],
    collect_role_contents: Callable[[str, list[str] | None], dict],
    collect_molecule_scenarios: Callable[[str, list[str] | None], list],
    collect_unconstrained_dynamic_task_includes: Callable[
        [str, list[str] | None], list
    ],
    collect_unconstrained_dynamic_role_includes: Callable[
        [str, list[str] | None], list
    ],
    collect_task_handler_catalog: Callable[
        [str, list[str] | None, str], tuple[list, list]
    ],
) -> tuple[dict, list, list[dict], dict]:
    """Collect scan-time variables, requirements, filter findings, and metadata."""
    variables = load_variables(role_path, include_vars_main, exclude_path_patterns)
    requirements = load_requirements(role_path)
    found = scan_for_default_filters(role_path, exclude_path_patterns)
    metadata = collect_role_contents(role_path, exclude_path_patterns)
    metadata["molecule_scenarios"] = collect_molecule_scenarios(
        role_path,
        exclude_path_patterns,
    )
    metadata["marker_prefix"] = marker_prefix
    metadata["detailed_catalog"] = bool(detailed_catalog)
    metadata["unconstrained_dynamic_task_includes"] = (
        collect_unconstrained_dynamic_task_includes(role_path, exclude_path_patterns)
    )
    metadata["unconstrained_dynamic_role_includes"] = (
        collect_unconstrained_dynamic_role_includes(role_path, exclude_path_patterns)
    )
    if detailed_catalog:
        task_catalog, handler_catalog = collect_task_handler_catalog(
            role_path,
            exclude_path_patterns,
            marker_prefix,
        )
        metadata["task_catalog"] = task_catalog
        metadata["handler_catalog"] = handler_catalog
    return variables, requirements, found, metadata


def apply_style_and_comparison_metadata(
    *,
    metadata: dict,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
    role_path: str,
    exclude_path_patterns: list[str] | None,
    resolve_default_style_guide_source: Callable[[str | None], str],
    parse_style_readme: Callable[..., dict],
    build_comparison_report: Callable[[str, str, list[str] | None], dict],
    policy_context: PolicyContext | None = None,
) -> None:
    """Attach style-guide and optional baseline comparison metadata."""
    effective_style_readme_path = style_readme_path
    if not effective_style_readme_path and style_source_path:
        effective_style_readme_path = style_source_path
    if style_guide_skeleton and not effective_style_readme_path:
        effective_style_readme_path = resolve_default_style_guide_source(
            style_source_path
        )

    if effective_style_readme_path:
        style_path = Path(effective_style_readme_path)
        if not style_path.is_file():
            raise FileNotFoundError(
                f"style README not found: {effective_style_readme_path}"
            )
        section_aliases = None
        if policy_context:
            context_aliases = policy_context.get("section_aliases")
            if isinstance(context_aliases, dict):
                section_aliases = context_aliases
        if section_aliases is None:
            metadata["style_guide"] = parse_style_readme(str(style_path))
        else:
            metadata["style_guide"] = parse_style_readme(
                str(style_path),
                section_aliases=section_aliases,
            )
    if style_guide_skeleton:
        metadata["style_guide_skeleton"] = True
    if compare_role_path:
        compare_path = Path(compare_role_path)
        if not compare_path.is_dir():
            raise FileNotFoundError(
                f"comparison role path not found: {compare_role_path}"
            )
        metadata["comparison"] = build_comparison_report(
            role_path,
            compare_role_path,
            exclude_path_patterns,
        )
