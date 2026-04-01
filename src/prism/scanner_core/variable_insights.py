"""Variable-insights staging seam extracted from scanner facade orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def collect_variable_insights_and_default_filter_findings(
    *,
    role_path: str,
    vars_seed_paths: list[str] | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    found_default_filters: list[dict],
    variables: dict,
    metadata: dict,
    marker_prefix: str,
    style_readme_path: str | None,
    policy_context: dict | None,
    ignore_unresolved_internal_underscore_references: bool,
    non_authoritative_test_evidence_max_file_bytes: int,
    non_authoritative_test_evidence_max_files_scanned: int,
    non_authoritative_test_evidence_max_total_bytes: int,
    build_variable_insights: Callable[..., list[dict]],
    attach_external_vars_context: Callable[..., None],
    collect_yaml_parse_failures: Callable[..., list[dict[str, object]]],
    extract_role_notes_from_comments: Callable[..., dict],
    build_undocumented_default_filters: Callable[..., list[dict]],
    extract_scanner_counters: Callable[..., dict[str, int | dict[str, int]]],
    build_display_variables: Callable[[dict, list[dict]], dict],
) -> tuple[list[dict], list[dict], dict]:
    """Collect variable insights, scanner counters, and secret-masked defaults."""
    variable_insights = build_variable_insights(
        role_path,
        seed_paths=vars_seed_paths,
        include_vars_main=include_vars_main,
        exclude_paths=exclude_path_patterns,
        style_readme_path=style_readme_path,
        policy_context=policy_context,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        non_authoritative_test_evidence_max_file_bytes=(
            non_authoritative_test_evidence_max_file_bytes
        ),
        non_authoritative_test_evidence_max_files_scanned=(
            non_authoritative_test_evidence_max_files_scanned
        ),
        non_authoritative_test_evidence_max_total_bytes=(
            non_authoritative_test_evidence_max_total_bytes
        ),
    )

    attach_external_vars_context(metadata=metadata, vars_seed_paths=vars_seed_paths)
    metadata["variable_insights"] = variable_insights
    metadata["yaml_parse_failures"] = collect_yaml_parse_failures(
        role_path,
        exclude_paths=exclude_path_patterns,
    )
    metadata["role_notes"] = extract_role_notes_from_comments(
        role_path,
        exclude_paths=exclude_path_patterns,
        marker_prefix=marker_prefix,
    )

    undocumented_default_filters = build_undocumented_default_filters(
        variable_insights=variable_insights,
        found_default_filters=found_default_filters,
    )
    metadata["scanner_counters"] = extract_scanner_counters(
        variable_insights,
        undocumented_default_filters,
        metadata.get("features") or {},
        metadata.get("yaml_parse_failures") or [],
    )
    display_variables = build_display_variables(variables, variable_insights)
    return variable_insights, undocumented_default_filters, display_variables


def attach_external_vars_context(
    *,
    metadata: dict,
    vars_seed_paths: list[str] | None,
) -> None:
    """Attach non-authoritative external variable context metadata when provided."""
    if not vars_seed_paths:
        return
    metadata["external_vars_context"] = {
        "paths": [str(path) for path in vars_seed_paths],
        "authoritative": False,
        "purpose": "required_variable_detection_hints",
    }


def build_undocumented_default_filters(
    *,
    variable_insights: list[dict],
    found_default_filters: list[dict],
    extract_default_target_var: Callable[[dict], str | None],
    looks_secret_name: Callable[[str], bool],
    resembles_password_like: Callable[[str], bool],
) -> list[dict]:
    """Return undocumented default() occurrences enriched with variable metadata."""
    inventory_names = {row["name"]: row for row in variable_insights}
    undocumented_default_filters: list[dict] = []
    for occurrence in found_default_filters:
        target_var = extract_default_target_var(occurrence)
        if not target_var:
            continue
        row = inventory_names.get(target_var)
        if row and not row.get("documented", False):
            enriched = dict(occurrence)
            enriched["target_var"] = target_var
            if row.get("secret") or (
                looks_secret_name(target_var)
                and resembles_password_like(enriched.get("args", ""))
            ):
                enriched["args"] = "<secret>"
                enriched["match"] = f"{target_var} | default(<secret>)"
            undocumented_default_filters.append(enriched)
    return undocumented_default_filters


def build_display_variables(variables: dict, variable_insights: list[dict]) -> dict:
    """Return role variables with secret values masked for rendering/output."""
    secret_names = {
        row["name"]
        for row in variable_insights
        if row.get("secret") and row["name"] in variables
    }
    return {
        key: ("<secret>" if key in secret_names else value)
        for key, value in variables.items()
    }


def build_variable_insights(
    role_path: str,
    *,
    seed_paths: list[str] | None,
    include_vars_main: bool,
    exclude_paths: list[str] | None,
    style_readme_path: str | None,
    policy_context: dict | None,
    ignore_unresolved_internal_underscore_references: bool,
    non_authoritative_test_evidence_max_file_bytes: int,
    non_authoritative_test_evidence_max_files_scanned: int,
    non_authoritative_test_evidence_max_total_bytes: int,
    load_role_variable_maps: Callable[..., tuple[dict, dict, dict, dict]],
    collect_variable_reference_context: Callable[..., dict],
    build_static_variable_rows: Callable[..., tuple[list[dict], dict[str, dict]]],
    populate_variable_rows: Callable[..., None],
    redact_secret_defaults: Callable[[list[dict]], None],
) -> list[dict]:
    """Build variable rows with inferred type/default/source details."""
    defaults_data, vars_data, defaults_sources, vars_sources = load_role_variable_maps(
        role_path,
        include_vars_main,
    )
    reference_context = collect_variable_reference_context(
        role_path=role_path,
        seed_paths=seed_paths,
        exclude_paths=exclude_paths,
        policy_context=policy_context,
    )

    rows, rows_by_name = build_static_variable_rows(
        role_root=Path(role_path),
        defaults_data=defaults_data,
        vars_data=vars_data,
        defaults_sources=defaults_sources,
        vars_sources=vars_sources,
    )
    populate_variable_rows(
        role_path=role_path,
        rows=rows,
        rows_by_name=rows_by_name,
        exclude_paths=exclude_paths,
        reference_context=reference_context,
        style_readme_path=style_readme_path,
        policy_context=policy_context,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        non_authoritative_test_evidence_max_file_bytes=(
            non_authoritative_test_evidence_max_file_bytes
        ),
        non_authoritative_test_evidence_max_files_scanned=(
            non_authoritative_test_evidence_max_files_scanned
        ),
        non_authoritative_test_evidence_max_total_bytes=(
            non_authoritative_test_evidence_max_total_bytes
        ),
    )

    redact_secret_defaults(rows)
    return rows
