"""Scan output sidecar orchestration helpers.

This module isolates scanner-report and runbook sidecar path shaping/writing
from the main scanner orchestration flow.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from .output import resolve_output_path
from .scan_context import (
    EmitScanOutputsArgs,
    build_scan_output_payload,
    build_scan_report_sidecar_args,
    build_runbook_sidecar_args,
)
from .scan_output_primary import render_primary_scan_output


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
    display_variables: dict,
    requirements_display: list,
    undocumented_default_filters: list,
    metadata: dict,
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
    metadata["concise_readme"] = True
    metadata["include_scanner_report_link"] = include_scanner_report_link

    if dry_run:
        return scanner_report_path

    scanner_report_path.parent.mkdir(parents=True, exist_ok=True)
    scanner_report = build_scanner_report_markdown(
        role_name=role_name,
        description=description,
        variables=display_variables,
        requirements=requirements_display,
        default_filters=undocumented_default_filters,
        metadata=metadata,
    )
    scanner_report_path.write_text(scanner_report, encoding="utf-8")
    metadata["scanner_report_relpath"] = os.path.relpath(
        scanner_report_path,
        out_path.parent,
    )
    return scanner_report_path


def write_optional_runbook_outputs(
    *,
    runbook_output: str | None,
    runbook_csv_output: str | None,
    role_name: str,
    metadata: dict,
    render_runbook: Callable[[str, dict], str],
    render_runbook_csv: Callable[[dict], str],
) -> None:
    """Write standalone runbook outputs when requested."""
    if runbook_output:
        rb_path = Path(runbook_output)
        rb_path.parent.mkdir(parents=True, exist_ok=True)
        rb_content = render_runbook(role_name, metadata)
        rb_path.write_text(rb_content, encoding="utf-8")
    if runbook_csv_output:
        rb_csv_path = Path(runbook_csv_output)
        rb_csv_path.parent.mkdir(parents=True, exist_ok=True)
        rb_csv_content = render_runbook_csv(metadata)
        rb_csv_path.write_text(rb_csv_content, encoding="utf-8")


def emit_scan_outputs(
    args: EmitScanOutputsArgs,
    *,
    build_scanner_report_markdown: Callable,
    render_and_write_output: Callable,
    render_runbook_fn: Callable,
    render_runbook_csv_fn: Callable,
) -> str:
    """Orchestrate primary output rendering with optional scanner-report and runbook sidecars.

    This coordinator is extracted from scanner.py to make the orchestration
    independently testable.  All scanner-specific callables are injected so
    scan_output_emission.py remains free of scanner.py imports.
    """
    out_path = resolve_output_path(args["output"], args["output_format"])
    output_payload = build_scan_output_payload(
        role_name=args["role_name"],
        description=args["description"],
        display_variables=args["display_variables"],
        requirements_display=args["requirements_display"],
        undocumented_default_filters=args["undocumented_default_filters"],
        metadata=args["metadata"],
    )
    write_concise_scanner_report_if_enabled(
        **build_scan_report_sidecar_args(
            concise_readme=args["concise_readme"],
            scanner_report_output=args["scanner_report_output"],
            out_path=out_path,
            include_scanner_report_link=args["include_scanner_report_link"],
            payload=output_payload,
            dry_run=args["dry_run"],
        ),
        build_scanner_report_markdown=build_scanner_report_markdown,
    )
    result = render_primary_scan_output(
        out_path=out_path,
        output_format=args["output_format"],
        template=args["template"],
        dry_run=args["dry_run"],
        output_payload=output_payload,
        render_and_write_scan_output=render_and_write_output,
    )
    if isinstance(result, bytes):
        result = result.decode("utf-8", errors="replace")
    if args["dry_run"]:
        return result
    write_optional_runbook_outputs(
        **build_runbook_sidecar_args(
            runbook_output=args["runbook_output"],
            runbook_csv_output=args["runbook_csv_output"],
            payload=output_payload,
        ),
        render_runbook=render_runbook_fn,
        render_runbook_csv=render_runbook_csv_fn,
    )
    return result
