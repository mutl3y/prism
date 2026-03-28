"""Compatibility shim for runbook/report rendering helpers."""

from __future__ import annotations

from .render_reports import (
    build_requirements_display,
    build_runbook_rows,
    build_runbook_sidecar_args,
    build_scan_report_sidecar_args,
    build_scanner_report_markdown,
    classify_provenance_issue,
    extract_scanner_counters,
    is_unresolved_noise_category,
    render_runbook,
    render_runbook_csv,
    write_concise_scanner_report_if_enabled,
)

__all__ = [
    "build_requirements_display",
    "build_runbook_rows",
    "build_runbook_sidecar_args",
    "build_scan_report_sidecar_args",
    "build_scanner_report_markdown",
    "classify_provenance_issue",
    "extract_scanner_counters",
    "is_unresolved_noise_category",
    "render_runbook",
    "render_runbook_csv",
    "write_concise_scanner_report_if_enabled",
]
