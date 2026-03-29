"""Output emission and orchestration helpers.

This module centralizes output rendering orchestration, including primary output
rendering and optional sidecar generation (scanner reports, runbooks).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from .output import resolve_output_path, write_output
from .scan_output_emission import (
    build_scanner_report_output_path,
    write_concise_scanner_report_if_enabled,
    write_optional_runbook_outputs,
)
from ..scanner_data.contracts import RunScanOutputPayload, ScanMetadata


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
    """Emit primary scan output in the specified format."""
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
    """Emit scanner sidecar report when concise mode is enabled."""
    return write_concise_scanner_report_if_enabled(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        role_name=cast(str, metadata.get("role_name", "")),
        description=cast(str, metadata.get("description", "")),
        display_variables=cast(dict[str, Any], metadata.get("display_variables", {})),
        requirements_display=cast(list[Any], metadata.get("requirements_display", [])),
        undocumented_default_filters=cast(
            list[Any], metadata.get("undocumented_default_filters", [])
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
    render_runbook: Callable[[str, dict[str, Any] | None], str],
    render_runbook_csv: Callable[[dict[str, Any] | None], str],
) -> None:
    """Emit runbook sidecar outputs when requested."""
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
    """Build a context dictionary for output emission orchestration."""
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
    render_runbook: Callable[[str, dict[str, Any] | None], str],
    render_runbook_csv: Callable[[dict[str, Any] | None], str],
) -> str | bytes:
    """Orchestrate coordinated output emission (primary + sidecars)."""
    out_path = resolve_output_file_path(Path(args["output"]), args["output_format"])

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

    if args["dry_run"]:
        return result

    if args["runbook_output"] or args["runbook_csv_output"]:
        emit_runbook_sidecars(
            runbook_output=args["runbook_output"],
            runbook_csv_output=args["runbook_csv_output"],
            metadata=args["metadata"],
            render_runbook=render_runbook,
            render_runbook_csv=render_runbook_csv,
        )

    return result
