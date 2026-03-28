"""Output emission and orchestration helpers.

This module centralizes output rendering orchestration, including primary output
rendering and optional sidecar generation (scanner reports, runbooks).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from .output import resolve_output_path, write_output
from .scan_context import (
    RunScanOutputPayload,
    ScanMetadata,
)
from .scan_output_emission import (
    build_scanner_report_output_path,
    write_concise_scanner_report_if_enabled,
    write_optional_runbook_outputs,
)


def resolve_output_file_path(
    out_path: Path,
    output_format: str,
) -> Path:
    """Return normalized output path for the requested format."""
    return resolve_output_path(str(out_path), output_format)


def write_output_file(path: Path, content: str | bytes) -> str:
    """Write content to disk and return absolute path as string."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_output(path, content)


def resolve_scanner_report_path(
    *,
    scanner_report_output: str | None,
    out_path: Path,
) -> Path:
    """Return the scanner sidecar path from explicit output or default suffix."""
    return build_scanner_report_output_path(
        scanner_report_output=scanner_report_output,
        out_path=out_path,
    )


def emit_primary_output(
    *,
    out_path: Path,
    output_format: str,
    template: str | None,
    dry_run: bool,
    metadata: dict,
    render_and_write: Callable[..., str | bytes],
) -> str | bytes:
    """Emit primary scan output in the specified format.

    Args:
        out_path: Output file path.
        output_format: Format like md, json, html, pdf.
        template: Optional Jinja2 template path.
        dry_run: If True, skip actual file writes.
        metadata: Scan metadata payload.
        render_and_write: Callable to render and write output.

    Returns:
        Output content as string or bytes.
    """
    return render_and_write(
        out_path=out_path,
        output_format=output_format,
        template=template,
        dry_run=dry_run,
    )


def emit_scanner_report_sidecar(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    metadata: ScanMetadata,
    dry_run: bool,
    render_scanner_report: Callable[..., str],
) -> Path | None:
    """Emit scanner sidecar report when concise mode is enabled.

    Args:
        concise_readme: Enable concise README with separate report.
        scanner_report_output: Explicit report output path.
        out_path: Primary output path (used to compute default report path).
        include_scanner_report_link: Add link to report in metadata.
        metadata: Scan metadata (updated in-place with concise flags).
        dry_run: If True, skip actual file writes.
        render_scanner_report: Callable to render scanner report markdown.

    Returns:
        Report file path, or None if not enabled.
    """
    return write_concise_scanner_report_if_enabled(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        role_name=cast(str, metadata.get("role_name", "")),
        description=cast(str, metadata.get("description", "")),
        display_variables=cast(dict, metadata.get("display_variables", {})),
        requirements_display=cast(list, metadata.get("requirements_display", [])),
        undocumented_default_filters=cast(
            list, metadata.get("undocumented_default_filters", [])
        ),
        metadata=metadata,
        dry_run=dry_run,
        build_scanner_report_markdown=render_scanner_report,
    )


def emit_runbook_sidecars(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    metadata: ScanMetadata,
    render_runbook: Callable[[str, dict | None], str],
    render_runbook_csv: Callable[[dict | None], str],
) -> None:
    """Emit runbook sidecar outputs when requested.

    Args:
        runbook_output: Path to write runbook markdown, or None to skip.
        runbook_csv_output: Path to write runbook CSV, or None to skip.
        metadata: Scan metadata including task catalog.
        render_runbook: Callable to render runbook markdown.
        render_runbook_csv: Callable to render runbook CSV.
    """
    write_optional_runbook_outputs(
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        role_name=cast(str, metadata.get("role_name", "")),
        metadata=metadata,
        render_runbook=render_runbook,
        render_runbook_csv=render_runbook_csv,
    )


def build_output_emission_context(
    *,
    output_payload: RunScanOutputPayload,
    output: str,
    output_format: str,
    template: str | None,
    dry_run: bool,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_scanner_report_link: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> dict[str, Any]:
    """Build a context dictionary for output emission orchestration.

    This bundles all parameters needed for coordinated output rendering
    and sidecar generation.
    """
    return {
        "role_name": output_payload["role_name"],
        "description": output_payload["description"],
        "display_variables": output_payload["display_variables"],
        "requirements_display": output_payload["requirements_display"],
        "undocumented_default_filters": output_payload["undocumented_default_filters"],
        "metadata": output_payload["metadata"],
        "output": output,
        "output_format": output_format,
        "template": template,
        "dry_run": dry_run,
        "concise_readme": concise_readme,
        "scanner_report_output": scanner_report_output,
        "include_scanner_report_link": include_scanner_report_link,
        "runbook_output": runbook_output,
        "runbook_csv_output": runbook_csv_output,
    }


def orchestrate_output_emission(
    *,
    args: dict[str, Any],
    render_and_write: Callable[..., str | bytes],
    render_scanner_report: Callable[..., str],
    render_runbook: Callable[[str, dict | None], str],
    render_runbook_csv: Callable[[dict | None], str],
) -> str | bytes:
    """Orchestrate coordinated output emission (primary + sidecars).

    This function sequences the emission of primary output and optional
    sidecar files (scanner report, runbooks) in the correct order.

    Args:
        args: Dictionary with output emission parameters:
            - role_name: Role name
            - description: Role description
            - display_variables: Variables to display
            - requirements_display: Requirements list
            - undocumented_default_filters: Default filters found
            - metadata: Scan metadata
            - output: Output file path
            - output_format: Output format (md, json, html, pdf)
            - template: Optional template path
            - dry_run: Skip actual file writes if True
            - concise_readme: Enable concise mode with sidecar report
            - scanner_report_output: Explicit report output path
            - include_scanner_report_link: Add report link to metadata
            - runbook_output: Runbook output path
            - runbook_csv_output: Runbook CSV output path
        render_and_write: Callable to render primary output.
        render_scanner_report: Callable to render scanner report.
        render_runbook: Callable to render runbook markdown.
        render_runbook_csv: Callable to render runbook CSV.

    Returns:
        Primary output content as string or bytes.
    """
    out_path = resolve_output_file_path(Path(args["output"]), args["output_format"])

    # Emit scanner report sidecar if enabled
    if args["concise_readme"]:
        emit_scanner_report_sidecar(
            concise_readme=args["concise_readme"],
            scanner_report_output=args["scanner_report_output"],
            out_path=out_path,
            include_scanner_report_link=args["include_scanner_report_link"],
            metadata=args["metadata"],
            dry_run=args["dry_run"],
            render_scanner_report=render_scanner_report,
        )

    # Emit primary output
    result = emit_primary_output(
        out_path=out_path,
        output_format=args["output_format"],
        template=args["template"],
        dry_run=args["dry_run"],
        metadata=args["metadata"],
        render_and_write=lambda **kw: render_and_write(
            out_path=kw["out_path"],
            output_format=kw["output_format"],
            role_name=args["role_name"],
            description=args["description"],
            display_variables=args["display_variables"],
            requirements_display=args["requirements_display"],
            undocumented_default_filters=args["undocumented_default_filters"],
            metadata=args["metadata"],
            template=kw["template"],
            dry_run=kw["dry_run"],
        ),
    )
    if isinstance(result, bytes):
        result = result.decode("utf-8", errors="replace")

    # Skip runbook sidecars in dry-run mode
    if args["dry_run"]:
        return result

    # Emit runbook sidecars if requested
    if args["runbook_output"] or args["runbook_csv_output"]:
        emit_runbook_sidecars(
            runbook_output=args["runbook_output"],
            runbook_csv_output=args["runbook_csv_output"],
            metadata=args["metadata"],
            render_runbook=render_runbook,
            render_runbook_csv=render_runbook_csv,
        )

    return result
