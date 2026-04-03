"""Scan output sidecar orchestration helpers.

This module isolates scanner-report and runbook sidecar path shaping/writing
from the main scanner orchestration flow.
"""

from __future__ import annotations

from typing import Any, Callable

from .emit_output import (
    build_output_emission_context as _build_output_emission_context,
    build_scanner_report_output_path as build_scanner_report_output_path,
    orchestrate_output_emission as _orchestrate_output_emission,
    write_concise_scanner_report_if_enabled as write_concise_scanner_report_if_enabled,
    write_optional_runbook_outputs as write_optional_runbook_outputs,
)
from .scan_output_primary import render_primary_scan_output
from ..scanner_data.contracts_output import (
    EmitScanOutputsArgs,
    RunScanOutputPayload,
)


__all__ = [
    "build_scanner_report_output_path",
    "write_concise_scanner_report_if_enabled",
    "write_optional_runbook_outputs",
    "emit_scan_outputs",
]


def _build_scan_output_payload(args: EmitScanOutputsArgs) -> RunScanOutputPayload:
    return {
        "role_name": args["role_name"],
        "description": args["description"],
        "display_variables": args["display_variables"],
        "requirements_display": args["requirements_display"],
        "undocumented_default_filters": args["undocumented_default_filters"],
        "metadata": args["metadata"],
    }


def emit_scan_outputs(
    args: EmitScanOutputsArgs,
    *,
    build_scanner_report_markdown: Callable[..., str],
    render_and_write_output: Callable[..., str | bytes],
    render_runbook_fn: Callable[[str, dict[str, Any] | None], str],
    render_runbook_csv_fn: Callable[[dict[str, Any] | None], str],
) -> str | bytes:
    """Adapt legacy emit-scan-output calls to the canonical emit_output path."""
    output_payload = _build_scan_output_payload(args)
    emission_args = _build_output_emission_context(
        output_payload=output_payload,
        output=args["output"],
        output_format=args["output_format"],
        template=args["template"],
        dry_run=args["dry_run"],
        concise_readme=args["concise_readme"],
        scanner_report_output=args["scanner_report_output"],
        include_scanner_report_link=args["include_scanner_report_link"],
        runbook_output=args["runbook_output"],
        runbook_csv_output=args["runbook_csv_output"],
    )

    return _orchestrate_output_emission(
        args=emission_args,
        render_and_write=lambda **kwargs: render_primary_scan_output(
            out_path=kwargs["out_path"],
            output_format=kwargs["output_format"],
            template=kwargs["template"],
            dry_run=kwargs["dry_run"],
            output_payload={
                **output_payload,
                "metadata": kwargs.get("metadata", output_payload["metadata"]),
            },
            render_and_write_scan_output=render_and_write_output,
        ),
        render_scanner_report=build_scanner_report_markdown,
        render_runbook=render_runbook_fn,
        render_runbook_csv=render_runbook_csv_fn,
    )
