"""Runtime scan-context orchestration seam for scanner facade delegation."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from prism.scanner_data.contracts_output import (
    EmitScanOutputsArgs,
    RunbookSidecarArgs,
    RunScanOutputPayload,
    ScanReportSidecarArgs,
)
from prism.scanner_data.contracts_request import (
    PolicyContext,
    ScanBaseContext,
    ScanContextPayload,
    ScanMetadata,
    ScanOptionsDict,
)


def build_runtime_scan_state(
    *,
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
    include_task_parameters: bool,
    include_task_runbooks: bool,
    inline_task_runbooks: bool,
    include_collection_checks: bool,
    keep_unknown_style_sections: bool,
    adopt_heading_mode: str | None,
    vars_seed_paths: list[str] | None,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
    policy_config_path: str | None,
    fail_on_unconstrained_dynamic_includes: bool | None,
    fail_on_yaml_like_task_annotations: bool | None,
    ignore_unresolved_internal_underscore_references: bool | None,
    strict_phase_failures: bool,
    failure_policy: Any,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    load_pattern_policy_with_context: Callable[
        ..., tuple[dict[str, Any], PolicyContext]
    ],
    build_run_scan_options_fn: Callable[..., ScanOptionsDict],
    resolve_scan_request_for_runtime_fn: Callable[..., bool],
) -> tuple[dict[str, Any], PolicyContext, ScanOptionsDict]:
    """Resolve request-scoped policy and canonical scan options for one run."""
    loaded_policy, policy_context = load_pattern_policy_with_context(
        override_path=policy_config_path,
        search_root=role_path,
    )
    if failure_policy is not None and hasattr(failure_policy, "strict"):
        strict_phase_failures = bool(getattr(failure_policy, "strict"))

    scan_options = build_run_scan_options_fn(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        include_vars_main=include_vars_main,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=resolve_scan_request_for_runtime_fn(
            detailed_catalog=detailed_catalog,
            runbook_output=runbook_output,
            runbook_csv_output=runbook_csv_output,
        ),
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        include_collection_checks=include_collection_checks,
        keep_unknown_style_sections=keep_unknown_style_sections,
        adopt_heading_mode=adopt_heading_mode,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        policy_context=policy_context,
    )
    scan_options["strict_phase_failures"] = bool(strict_phase_failures)
    return loaded_policy, policy_context, scan_options


@contextmanager
def scan_policy_scope(
    *,
    loaded_policy: dict[str, Any],
    policy_context: PolicyContext,
    variable_policy_scope: Callable[..., Any],
    style_section_aliases_scope: Callable[..., Any],
    variable_guidance_keywords_scope: Callable[..., Any],
):
    """Apply request-scoped policy overrides used by one scanner execution."""
    with variable_policy_scope(loaded_policy), style_section_aliases_scope(
        dict(policy_context["section_aliases"])
    ), variable_guidance_keywords_scope(
        tuple(policy_context["variable_guidance_keywords"])
    ):
        yield


def prepare_scan_context(
    scan_options: ScanOptionsDict,
    *,
    scan_context_builder_cls: type,
    collect_scan_base_context: Callable[[dict[str, Any]], ScanBaseContext],
    load_ignore_unresolved_internal_underscore_references: Callable[
        [str, str | None, bool], bool
    ],
    load_non_authoritative_test_evidence_max_file_bytes: Callable[
        [str, str | None, int], int
    ],
    load_non_authoritative_test_evidence_max_files_scanned: Callable[
        [str, str | None, int], int
    ],
    load_non_authoritative_test_evidence_max_total_bytes: Callable[
        [str, str | None, int], int
    ],
    enrich_scan_context_with_insights: Callable[..., tuple[list[dict], dict]],
    finalize_scan_context_payload: Callable[..., ScanContextPayload],
    non_authoritative_test_evidence_max_file_bytes: int,
    non_authoritative_test_evidence_max_files_scanned: int,
    non_authoritative_test_evidence_max_total_bytes: int,
) -> ScanContextPayload:
    """Collect role metadata and scanner context required for rendering outputs."""
    builder = scan_context_builder_cls(
        collect_scan_base_context=collect_scan_base_context,
        load_ignore_unresolved_internal_underscore_references=(
            load_ignore_unresolved_internal_underscore_references
        ),
        load_non_authoritative_test_evidence_max_file_bytes=(
            load_non_authoritative_test_evidence_max_file_bytes
        ),
        load_non_authoritative_test_evidence_max_files_scanned=(
            load_non_authoritative_test_evidence_max_files_scanned
        ),
        load_non_authoritative_test_evidence_max_total_bytes=(
            load_non_authoritative_test_evidence_max_total_bytes
        ),
        enrich_scan_context_with_insights=enrich_scan_context_with_insights,
        finalize_scan_context_payload=finalize_scan_context_payload,
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
    return builder.build_scan_context(scan_options)


def collect_scan_base_context(
    scan_options: ScanOptionsDict,
    *,
    collect_scan_identity_and_artifacts: Callable[..., tuple[Any, ...]],
    apply_scan_metadata_configuration: Callable[..., list],
    apply_unconstrained_dynamic_include_policy: Callable[..., None],
    apply_yaml_like_task_annotation_policy: Callable[..., None],
) -> ScanBaseContext:
    """Collect baseline scan artifacts and configured metadata state."""
    (
        rp,
        meta,
        role_name,
        description,
        marker_prefix,
        variables,
        requirements,
        found,
        metadata,
    ) = collect_scan_identity_and_artifacts(
        role_path=scan_options["role_path"],
        role_name_override=scan_options["role_name_override"],
        readme_config_path=scan_options["readme_config_path"],
        include_vars_main=scan_options["include_vars_main"],
        exclude_path_patterns=scan_options["exclude_path_patterns"],
        detailed_catalog=scan_options["detailed_catalog"],
    )

    requirements_display = apply_scan_metadata_configuration(
        role_path=scan_options["role_path"],
        readme_config_path=scan_options["readme_config_path"],
        adopt_heading_mode=scan_options["adopt_heading_mode"],
        include_task_parameters=scan_options["include_task_parameters"],
        include_task_runbooks=scan_options["include_task_runbooks"],
        inline_task_runbooks=scan_options["inline_task_runbooks"],
        include_collection_checks=scan_options["include_collection_checks"],
        keep_unknown_style_sections=scan_options["keep_unknown_style_sections"],
        meta=meta,
        requirements=requirements,
        metadata=metadata,
    )

    apply_unconstrained_dynamic_include_policy(
        role_path=scan_options["role_path"],
        readme_config_path=scan_options["readme_config_path"],
        fail_on_unconstrained_dynamic_includes=scan_options[
            "fail_on_unconstrained_dynamic_includes"
        ],
        metadata=metadata,
    )
    apply_yaml_like_task_annotation_policy(
        role_path=scan_options["role_path"],
        readme_config_path=scan_options["readme_config_path"],
        fail_on_yaml_like_task_annotations=scan_options[
            "fail_on_yaml_like_task_annotations"
        ],
        metadata=metadata,
    )

    return {
        "rp": rp,
        "role_name": role_name,
        "description": description,
        "marker_prefix": marker_prefix,
        "variables": variables,
        "found": found,
        "metadata": metadata,
        "requirements_display": requirements_display,
    }


def apply_unconstrained_dynamic_include_policy(
    *,
    role_path: str,
    readme_config_path: str | None,
    fail_on_unconstrained_dynamic_includes: bool | None,
    metadata: dict,
    load_fail_on_unconstrained_dynamic_includes: Callable[
        [str, str | None, bool], bool
    ],
) -> None:
    """Apply and enforce unconstrained dynamic include scan policy."""
    # Intentionally allow malformed policy parsing RuntimeError to propagate.
    config_default = load_fail_on_unconstrained_dynamic_includes(
        role_path,
        readme_config_path,
        False,
    )
    effective_fail = (
        config_default
        if fail_on_unconstrained_dynamic_includes is None
        else bool(fail_on_unconstrained_dynamic_includes)
    )
    metadata["fail_on_unconstrained_dynamic_includes"] = effective_fail

    hazards = [
        *(metadata.get("unconstrained_dynamic_task_includes") or []),
        *(metadata.get("unconstrained_dynamic_role_includes") or []),
    ]
    if effective_fail and hazards:
        first = hazards[0] if isinstance(hazards[0], dict) else {}
        first_file = str(first.get("file") or "<unknown>")
        first_task = str(first.get("task") or "(unnamed task)")
        first_module = str(first.get("module") or "include")
        first_target = str(first.get("target") or "")
        raise RuntimeError(
            "Unconstrained dynamic includes detected "
            f"({len(hazards)} findings). "
            f"First finding: {first_file} / {first_task} / {first_module} -> {first_target}. "
            "Constrain with a simple when allow-list, disable via "
            "scan.fail_on_unconstrained_dynamic_includes in .prism.yml, "
            "or override at call time."
        )


def apply_yaml_like_task_annotation_policy(
    *,
    role_path: str,
    readme_config_path: str | None,
    fail_on_yaml_like_task_annotations: bool | None,
    metadata: dict,
    load_fail_on_yaml_like_task_annotations: Callable[[str, str | None, bool], bool],
) -> None:
    """Apply and enforce YAML-like task annotation strict-fail policy."""
    # Intentionally allow malformed policy parsing RuntimeError to propagate.
    config_default = load_fail_on_yaml_like_task_annotations(
        role_path,
        readme_config_path,
        False,
    )
    effective_fail = (
        config_default
        if fail_on_yaml_like_task_annotations is None
        else bool(fail_on_yaml_like_task_annotations)
    )
    metadata["fail_on_yaml_like_task_annotations"] = effective_fail

    features = metadata.get("features") or {}
    yaml_like_count = int(features.get("yaml_like_task_annotations") or 0)
    if effective_fail and yaml_like_count > 0:
        raise RuntimeError(
            "YAML-like task annotations detected "
            f"({yaml_like_count} findings). "
            "Use plain text or key=value payloads in marker comments, disable via "
            "scan.fail_on_yaml_like_task_annotations in .prism.yml, "
            "or override at call time."
        )


def finalize_scan_context_payload(
    *,
    rp: str,
    role_name: str,
    description: str,
    requirements_display: list,
    undocumented_default_filters: list[dict],
    display_variables: dict,
    metadata: ScanMetadata,
) -> ScanContextPayload:
    """Return normalized context payload used by run_scan output emission."""
    return ScanContextPayload(
        rp=rp,
        role_name=role_name,
        description=description,
        requirements_display=requirements_display,
        undocumented_default_filters=undocumented_default_filters,
        display_variables=display_variables,
        metadata=metadata,
    )


def collect_scan_identity_and_artifacts(
    *,
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
    resolve_scan_identity: Callable[[str, str | None], tuple[Any, Any, str, str]],
    load_readme_marker_prefix: Callable[..., str],
    collect_scan_artifacts: Callable[..., tuple[dict, list, list, ScanMetadata]],
) -> tuple[Any, Any, str, str, str, dict, list, list, ScanMetadata]:
    """Resolve scan identity and collect core role artifacts."""
    rp, meta, role_name, description = resolve_scan_identity(
        role_path,
        role_name_override,
    )
    marker_config_warnings: list[str] = []
    marker_prefix = load_readme_marker_prefix(
        role_path,
        readme_config_path,
        warning_collector=marker_config_warnings,
    )
    variables, requirements, found, metadata = collect_scan_artifacts(
        role_path=role_path,
        include_vars_main=include_vars_main,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=detailed_catalog,
        marker_prefix=marker_prefix,
    )
    if marker_config_warnings:
        metadata["readme_marker_config_warnings"] = marker_config_warnings
    return (
        rp,
        meta,
        role_name,
        description,
        marker_prefix,
        variables,
        requirements,
        found,
        metadata,
    )


def apply_scan_metadata_configuration(
    *,
    role_path: str,
    readme_config_path: str | None,
    adopt_heading_mode: str | None,
    include_task_parameters: bool,
    include_task_runbooks: bool,
    inline_task_runbooks: bool,
    include_collection_checks: bool,
    keep_unknown_style_sections: bool,
    meta: dict,
    requirements: list,
    metadata: ScanMetadata,
    build_requirements_display: Callable[..., tuple[list[str], list[str]]],
    load_readme_section_config: Callable[..., dict | None],
    apply_readme_section_config: Callable[[ScanMetadata, dict | None], None],
) -> list:
    """Apply scan options that shape metadata and requirements rendering."""
    metadata["include_task_parameters"] = bool(include_task_parameters)
    metadata["include_task_runbooks"] = bool(include_task_runbooks)
    metadata["inline_task_runbooks"] = bool(inline_task_runbooks)

    requirements_display, collection_compliance_notes = build_requirements_display(
        requirements=requirements,
        meta=meta,
        features=metadata.get("features") or {},
        include_collection_checks=include_collection_checks,
    )
    metadata["collection_compliance_notes"] = collection_compliance_notes
    metadata["keep_unknown_style_sections"] = keep_unknown_style_sections

    readme_section_config_warnings: list[str] = []
    readme_section_config = load_readme_section_config(
        role_path,
        config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
        strict=False,
        warning_collector=readme_section_config_warnings,
    )
    if readme_section_config_warnings:
        metadata["readme_section_config_warnings"] = readme_section_config_warnings
    apply_readme_section_config(metadata, readme_section_config)
    return requirements_display


def enrich_scan_context_with_insights(
    *,
    role_path: str,
    role_name: str,
    description: str,
    vars_seed_paths: list[str] | None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    marker_prefix: str,
    found: list,
    variables: dict,
    metadata: ScanMetadata,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
    ignore_unresolved_internal_underscore_references: bool,
    non_authoritative_test_evidence_max_file_bytes: int,
    non_authoritative_test_evidence_max_files_scanned: int,
    non_authoritative_test_evidence_max_total_bytes: int,
    collect_variable_insights_and_default_filter_findings: Callable[
        ..., tuple[list[dict], list[dict], dict]
    ],
    build_doc_insights: Callable[..., dict],
    apply_style_and_comparison_metadata: Callable[..., None],
    policy_context: PolicyContext | None = None,
) -> tuple[list[dict], dict]:
    """Add variable/doc/style insights to scan metadata and display payloads."""
    variable_insights, undocumented_default_filters, display_variables = (
        collect_variable_insights_and_default_filter_findings(
            role_path=role_path,
            vars_seed_paths=vars_seed_paths,
            include_vars_main=include_vars_main,
            exclude_path_patterns=exclude_path_patterns,
            found_default_filters=found,
            variables=variables,
            metadata=metadata,
            marker_prefix=marker_prefix,
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
    )
    metadata["doc_insights"] = build_doc_insights(
        role_name=role_name,
        description=description,
        metadata=metadata,
        variables=variables,
        variable_insights=variable_insights,
    )
    apply_style_and_comparison_metadata(
        metadata=metadata,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        role_path=role_path,
        exclude_path_patterns=exclude_path_patterns,
        policy_context=policy_context,
    )
    return undocumented_default_filters, display_variables


def build_scan_output_payload(
    *,
    role_name: str,
    description: str,
    display_variables: dict,
    requirements_display: list,
    undocumented_default_filters: list,
    metadata: dict,
) -> RunScanOutputPayload:
    """Build the shared payload used for scanner report and primary output rendering."""
    return {
        "role_name": role_name,
        "description": description,
        "display_variables": display_variables,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "metadata": metadata,
    }


def build_emit_scan_outputs_args(
    *,
    output: str,
    output_format: str,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    payload: RunScanOutputPayload,
    template: str | None,
    dry_run: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> EmitScanOutputsArgs:
    """Build the typed argument bundle for emit_scan_outputs."""
    return {
        "output": output,
        "output_format": output_format,
        "concise_readme": concise_readme,
        "scanner_report_output": scanner_report_output,
        "include_scanner_report_link": include_scanner_report_link,
        "role_name": payload["role_name"],
        "description": payload["description"],
        "display_variables": payload["display_variables"],
        "requirements_display": payload["requirements_display"],
        "undocumented_default_filters": payload["undocumented_default_filters"],
        "metadata": payload["metadata"],
        "template": template,
        "dry_run": dry_run,
        "runbook_output": runbook_output,
        "runbook_csv_output": runbook_csv_output,
    }


def build_scan_report_sidecar_args(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    payload: RunScanOutputPayload,
    dry_run: bool,
) -> ScanReportSidecarArgs:
    """Build the typed argument bundle for scanner report sidecar emission."""
    return {
        "concise_readme": concise_readme,
        "scanner_report_output": scanner_report_output,
        "out_path": out_path,
        "include_scanner_report_link": include_scanner_report_link,
        "role_name": payload["role_name"],
        "description": payload["description"],
        "display_variables": payload["display_variables"],
        "requirements_display": payload["requirements_display"],
        "undocumented_default_filters": payload["undocumented_default_filters"],
        "metadata": payload["metadata"],
        "dry_run": dry_run,
    }


def build_runbook_sidecar_args(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    payload: RunScanOutputPayload,
) -> RunbookSidecarArgs:
    """Build the typed argument bundle for optional runbook sidecar emission."""
    return {
        "runbook_output": runbook_output,
        "runbook_csv_output": runbook_csv_output,
        "role_name": payload["role_name"],
        "metadata": payload["metadata"],
    }


def render_primary_scan_output(
    *,
    out_path: Path,
    output_format: str,
    template: str | None,
    dry_run: bool,
    output_payload: RunScanOutputPayload,
    render_primary_scan_output_fn: Callable[..., str | bytes],
    render_and_write_scan_output: Callable[..., str | bytes],
) -> str | bytes:
    """Render and optionally write the primary scan output."""
    return render_primary_scan_output_fn(
        out_path=out_path,
        output_format=output_format,
        template=template,
        dry_run=dry_run,
        output_payload=output_payload,
        render_and_write_scan_output=render_and_write_scan_output,
    )


def emit_scan_outputs(
    args: EmitScanOutputsArgs,
    *,
    emit_scan_outputs_fn: Callable[..., str | bytes],
    build_scanner_report_markdown: Callable[..., str],
    render_and_write_scan_output: Callable[..., str | bytes],
    render_runbook: Callable[..., str],
    render_runbook_csv: Callable[..., str],
) -> str | bytes:
    """Render primary outputs and optional sidecars for a scanner run."""
    return emit_scan_outputs_fn(
        args,
        build_scanner_report_markdown=build_scanner_report_markdown,
        render_and_write_output=render_and_write_scan_output,
        render_runbook_fn=render_runbook,
        render_runbook_csv_fn=render_runbook_csv,
    )
