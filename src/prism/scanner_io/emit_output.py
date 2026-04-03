"""Output emission and orchestration helpers.

This module centralizes output rendering orchestration, including primary output
rendering and optional sidecar generation (scanner reports, runbooks).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, cast

from .output import resolve_output_path, write_output
from ..scanner_data.contracts import RunScanOutputPayload, ScanMetadata


def build_scanner_report_output_path(
    *,
    scanner_report_output: str | None,
    out_path: Path,
) -> Path:
    """Return the scanner sidecar path from explicit output or default suffix."""
    if scanner_report_output:
        return Path(scanner_report_output)
    return out_path.with_suffix(".scan-report.md")


def write_concise_scanner_report_if_enabled(
    *,
    concise_readme: bool,
    scanner_report_output: str | None,
    out_path: Path,
    include_scanner_report_link: bool,
    role_name: str,
    description: str,
    display_variables: dict[str, Any],
    requirements_display: list[Any],
    undocumented_default_filters: list[Any],
    metadata: ScanMetadata,
    dry_run: bool,
    build_scanner_report_markdown: Callable[..., str],
) -> Path | None:
    """Write scanner sidecar report when concise mode is enabled."""
    if not concise_readme:
        return None

    scanner_report_path = build_scanner_report_output_path(
        scanner_report_output=scanner_report_output,
        out_path=out_path,
    )
    sidecar_metadata: ScanMetadata = cast(ScanMetadata, dict(metadata))
    sidecar_metadata["concise_readme"] = True
    sidecar_metadata["include_scanner_report_link"] = include_scanner_report_link

    if dry_run:
        return scanner_report_path

    scanner_report_path.parent.mkdir(parents=True, exist_ok=True)
    scanner_report = build_scanner_report_markdown(
        role_name=role_name,
        description=description,
        variables=display_variables,
        requirements=requirements_display,
        default_filters=undocumented_default_filters,
        metadata=sidecar_metadata,
    )
    scanner_report_path.write_text(scanner_report, encoding="utf-8")
    return scanner_report_path


def write_optional_runbook_outputs(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    role_name: str,
    metadata: ScanMetadata,
    render_runbook: Callable[[str, dict[str, Any] | None], str],
    render_runbook_csv: Callable[[dict[str, Any] | None], str],
) -> None:
    """Write standalone runbook outputs when requested."""
    if runbook_output:
        rb_path = Path(runbook_output)
        rb_path.parent.mkdir(parents=True, exist_ok=True)
        render_runbook_any = cast(Any, render_runbook)
        try:
            rb_content = render_runbook_any(role_name=role_name, metadata=metadata)
        except TypeError:
            rb_content = render_runbook(role_name, metadata)
        rb_path.write_text(rb_content, encoding="utf-8")
    if runbook_csv_output:
        rb_csv_path = Path(runbook_csv_output)
        rb_csv_path.parent.mkdir(parents=True, exist_ok=True)
        rb_csv_content = render_runbook_csv(metadata)
        rb_csv_path.write_text(rb_csv_content, encoding="utf-8")


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
        metadata=metadata,
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
    role_name: str | None = None,
    description: str | None = None,
    display_variables: dict[str, Any] | None = None,
    requirements_display: list[Any] | None = None,
    undocumented_default_filters: list[Any] | None = None,
) -> Path | None:
    """Emit scanner sidecar report when concise mode is enabled."""
    return write_concise_scanner_report_if_enabled(
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        out_path=out_path,
        include_scanner_report_link=include_scanner_report_link,
        role_name=role_name or cast(str, metadata.get("role_name", "")),
        description=description or cast(str, metadata.get("description", "")),
        display_variables=display_variables
        or cast(dict[str, Any], metadata.get("display_variables", {})),
        requirements_display=requirements_display
        or cast(list[Any], metadata.get("requirements_display", [])),
        undocumented_default_filters=undocumented_default_filters
        or cast(list[Any], metadata.get("undocumented_default_filters", [])),
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
    role_name: str | None = None,
) -> None:
    """Emit runbook sidecar outputs when requested."""
    write_optional_runbook_outputs(
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        role_name=role_name or cast(str, metadata.get("role_name", "")),
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
    metadata: ScanMetadata = cast(ScanMetadata, dict(args["metadata"]))

    if not args["dry_run"]:
        out_path.parent.mkdir(parents=True, exist_ok=True)

    if args["concise_readme"]:
        scanner_report_path = emit_scanner_report_sidecar(
            concise_readme=args["concise_readme"],
            scanner_report_output=args["scanner_report_output"],
            out_path=out_path,
            include_scanner_report_link=args["include_scanner_report_link"],
            metadata=metadata,
            dry_run=args["dry_run"],
            render_scanner_report=render_scanner_report,
            role_name=args["role_name"],
            description=args["description"],
            display_variables=args["display_variables"],
            requirements_display=args["requirements_display"],
            undocumented_default_filters=args["undocumented_default_filters"],
        )
        metadata["concise_readme"] = True
        metadata["include_scanner_report_link"] = args["include_scanner_report_link"]
        if scanner_report_path is not None and not args["dry_run"]:
            metadata["scanner_report_relpath"] = os.path.relpath(
                scanner_report_path,
                out_path.parent,
            )

    result = emit_primary_output(
        out_path=out_path,
        output_format=args["output_format"],
        template=args["template"],
        dry_run=args["dry_run"],
        metadata=metadata,
        render_and_write=lambda **kw: render_and_write(
            out_path=kw["out_path"],
            output_format=kw["output_format"],
            role_name=args["role_name"],
            description=args["description"],
            display_variables=args["display_variables"],
            requirements_display=args["requirements_display"],
            undocumented_default_filters=args["undocumented_default_filters"],
            metadata=metadata,
            template=kw["template"],
            dry_run=kw["dry_run"],
        ),
    )

    if args["dry_run"]:
        return result

    if args["runbook_output"] or args["runbook_csv_output"]:
        emit_runbook_sidecars(
            runbook_output=args["runbook_output"],
            runbook_csv_output=args["runbook_csv_output"],
            metadata=metadata,
            render_runbook=render_runbook,
            render_runbook_csv=render_runbook_csv,
            role_name=args["role_name"],
        )

    return result
