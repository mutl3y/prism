"""Runbook and report processing helpers for scanner output.

This module provides thin wrapper interfaces to runbook and scanner report
generation, delegating actual implementation to submodules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

# Import public interfaces from submodules
from .scanner_report import (
    build_scanner_report_markdown as _report_build_markdown,
    classify_provenance_issue as _report_classify_provenance_issue,
    is_unresolved_noise_category as _report_is_unresolved_noise_category,
)
from .runbook import (
    _build_runbook_rows as _runbook_build_rows,
    render_runbook as _runbook_render,
    render_runbook_csv as _runbook_render_csv,
)
from .scan_metrics import (
    extract_scanner_counters as _scan_metrics_extract_scanner_counters,
)
from .scan_context import (
    RunScanOutputPayload as _RunScanOutputPayload,
    ScanReportSidecarArgs as _ScanReportSidecarArgs,
    RunbookSidecarArgs as _RunbookSidecarArgs,
    build_scan_report_sidecar_args as _scan_context_build_scan_report_sidecar_args,
    build_runbook_sidecar_args as _scan_context_build_runbook_sidecar_args,
)
from .requirements import (
    build_requirements_display as _requirements_build_requirements_display,
)
from .scan_output_emission import (
    write_concise_scanner_report_if_enabled as _scan_output_write_concise_scanner_report_if_enabled,
)


def build_scanner_report_markdown(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
    render_section_body=None,
) -> str:
    """Render a scanner-focused markdown sidecar report."""
    return _report_build_markdown(
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata,
        render_section_body=render_section_body,
    )


def extract_scanner_counters(
    variable_insights: list[dict],
    default_filters: list[dict],
    features: dict | None = None,
    parse_failures: list[dict[str, object]] | None = None,
) -> dict[str, int | dict[str, int]]:
    """Summarize scanner findings by certainty and variable category."""
    return _scan_metrics_extract_scanner_counters(
        variable_insights,
        default_filters,
        features,
        parse_failures,
    )


def classify_provenance_issue(row: dict) -> str | None:
    """Return a stable provenance category label for unresolved/ambiguous rows."""
    return _report_classify_provenance_issue(row)


def is_unresolved_noise_category(category: str | None) -> bool:
    """Return True if the category participates in unresolved-noise metrics."""
    return _report_is_unresolved_noise_category(category)


def render_runbook(
    role_name: str,
    metadata: dict | None = None,
    template: str | None = None,
) -> str:
    """Render a standalone runbook markdown document for a role."""
    return _runbook_render(role_name=role_name, metadata=metadata, template=template)


def build_runbook_rows(metadata: dict | None) -> list[tuple[str, str, str]]:
    """Build normalized runbook rows: (file, task_name, step)."""
    return _runbook_build_rows(metadata)


def render_runbook_csv(metadata: dict | None = None) -> str:
    """Render runbook rows to CSV with columns: file, task_name, step."""
    return _runbook_render_csv(metadata)


def build_requirements_display(
    *,
    requirements: list,
    meta: dict,
    features: dict,
    include_collection_checks: bool = True,
) -> tuple[list[str], list[str]]:
    """Build rendered requirements lines and collection compliance notes."""
    return _requirements_build_requirements_display(
        requirements=requirements,
        meta=meta,
        features=features,
        include_collection_checks=include_collection_checks,
    )


def write_concise_scanner_report_if_enabled(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    role_name: str,
    description: str,
    display_variables: dict,
    requirements_display: list,
    undocumented_default_filters: list,
    metadata: dict,
    dry_run: bool,
    build_scanner_report_markdown_fn=None,
) -> Path | None:
    """Write scanner sidecar report when concise mode is enabled."""
    if build_scanner_report_markdown_fn is None:
        build_scanner_report_markdown_fn = build_scanner_report_markdown
    
    return _scan_output_write_concise_scanner_report_if_enabled(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        role_name=role_name,
        description=description,
        display_variables=display_variables,
        requirements_display=requirements_display,
        undocumented_default_filters=undocumented_default_filters,
        metadata=metadata,
        dry_run=dry_run,
        build_scanner_report_markdown=build_scanner_report_markdown_fn,
    )


def build_scan_report_sidecar_args(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    payload: _RunScanOutputPayload,
    dry_run: bool,
) -> _ScanReportSidecarArgs:
    """Build the typed argument bundle for write_concise_scanner_report_if_enabled."""
    return _scan_context_build_scan_report_sidecar_args(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        payload=payload,
        dry_run=dry_run,
    )


def build_runbook_sidecar_args(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    payload: _RunScanOutputPayload,
) -> _RunbookSidecarArgs:
    """Build the typed argument bundle for write_optional_runbook_outputs."""
    return _scan_context_build_runbook_sidecar_args(
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        payload=payload,
    )
