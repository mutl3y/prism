"""Scan-context and output-payload shaping helpers for scanner orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeAlias, TypedDict


class ScanContext(TypedDict):
    """Internal scan context consumed by output payload shaping."""

    display_variables: dict[str, Any]
    metadata: dict[str, Any]


class ScanBaseContext(TypedDict):
    """Typed return contract for _collect_scan_base_context.

    Stabilizes the internal seam between base-context collection and the
    prepare-scan-context orchestration step, including all policy-enforcement outputs.
    """

    rp: str
    role_name: str
    description: str
    marker_prefix: str
    variables: dict[str, Any]
    found: list[Any]
    metadata: dict[str, Any]
    requirements_display: list[Any]


class RunScanOutputPayload(TypedDict):
    """Typed seam payload between run_scan orchestration and output rendering."""

    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: dict[str, Any]


class EmitScanOutputsArgs(TypedDict):
    """Argument bundle for _emit_scan_outputs to reduce caller argument-drift risk."""

    output: str
    output_format: str
    concise_readme: bool
    scanner_report_output: str | None
    include_scanner_report_link: bool
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: dict[str, Any]
    template: str | None
    dry_run: bool
    runbook_output: str | None
    runbook_csv_output: str | None


class ScanReportSidecarArgs(TypedDict):
    """Argument bundle for _write_concise_scanner_report_if_enabled.

    Prevents argument-drift between _emit_scan_outputs and the sidecar emission
    helper.
    """

    concise_readme: bool
    scanner_report_output: str | None
    out_path: Path
    include_scanner_report_link: bool
    role_name: str
    description: str
    display_variables: dict[str, Any]
    requirements_display: list[Any]
    undocumented_default_filters: list[Any]
    metadata: dict[str, Any]
    dry_run: bool


class RunbookSidecarArgs(TypedDict):
    """Argument bundle for _write_optional_runbook_outputs.

    Bundles the data fields so the call site in _emit_scan_outputs is a single
    structured object rather than scattered keyword arguments.
    """

    runbook_output: str | None
    runbook_csv_output: str | None
    role_name: str
    metadata: dict[str, Any]


PreparedScanContext: TypeAlias = tuple[
    str,
    str,
    str,
    list[Any],
    list[Any],
    ScanContext,
]


def finalize_scan_context_payload(
    *,
    rp: str,
    role_name: str,
    description: str,
    requirements_display: list[Any],
    undocumented_default_filters: list[dict[str, Any]],
    display_variables: dict[str, Any],
    metadata: dict[str, Any],
) -> PreparedScanContext:
    """Return normalized context payload used by run_scan output emission."""
    return (
        rp,
        role_name,
        description,
        requirements_display,
        undocumented_default_filters,
        {
            "display_variables": display_variables,
            "metadata": metadata,
        },
    )


def build_scan_output_payload(
    *,
    role_name: str,
    description: str,
    display_variables: dict[str, Any],
    requirements_display: list[Any],
    undocumented_default_filters: list[Any],
    metadata: dict[str, Any],
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


def prepare_run_scan_payload(
    *,
    prepared_scan_context: PreparedScanContext,
) -> RunScanOutputPayload:
    """Shape prepared scan context into the output payload consumed by run_scan."""
    (
        _rp,
        role_name,
        description,
        requirements_display,
        undocumented_default_filters,
        scan_context,
    ) = prepared_scan_context
    return {
        "role_name": role_name,
        "description": description,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "display_variables": scan_context["display_variables"],
        "metadata": scan_context["metadata"],
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
    """Build the typed argument bundle for _write_concise_scanner_report_if_enabled."""
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
    """Build the typed argument bundle for _emit_scan_outputs from run_scan inputs."""
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


def build_runbook_sidecar_args(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    payload: RunScanOutputPayload,
) -> RunbookSidecarArgs:
    """Build the typed argument bundle for _write_optional_runbook_outputs."""
    return {
        "runbook_output": runbook_output,
        "runbook_csv_output": runbook_csv_output,
        "role_name": payload["role_name"],
        "metadata": payload["metadata"],
    }
