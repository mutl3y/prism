"""OutputOrchestrator - orchestrator for rendering and emitting scan outputs.

This module consolidates output-related logic currently spread across:
- scan_output_primary.py — primary output format handling
- scan_output_emission.py — orchestration of rendering and writing
- output.py — format primitives and path resolution
- render_readme.py — README composition and formatting
- scanner_report.py — scanner-report YAML generation and rendering
- runbook.py — runbook markdown and CSV generation

The OutputOrchestrator class provides a cohesive interface for:
- Rendering primary outputs (README, JSON, HTML, PDF)
- Generating sidecar files (scanner-report, runbook)
- Resolving and normalizing output paths
- Supporting dry-run mode (render without writing files)
- Mutating metadata with output configuration
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .di import DIContainer
from ..scanner_data.contracts_output import RunScanOutputPayload
from ..scanner_io.emit_output import (
    build_output_emission_context as _build_output_emission_context,
    orchestrate_output_emission as _orchestrate_output_emission,
)
from ..scanner_io.scan_output_primary import (
    render_and_write_scan_output as _render_and_write_scan_output,
)
from ..scanner_io import render_final_output, write_output
from ..scanner_analysis import build_scanner_report_markdown
from ..scanner_analysis import render_runbook, render_runbook_csv
from ..scanner_readme import render_guide_section_body, render_readme


class OutputOrchestrator:
    """Orchestrator for rendering and emitting scan outputs.

    Consolidates:
    - Primary output rendering (README, JSON, HTML, PDF formats)
    - Sidecar file generation (scanner-report, runbook markdown/CSV)
    - Output path resolution and normalization
    - Dry-run mode (render without writing)
    - Metadata mutation (scanner_report_relpath, concise_readme flag)

    Uses immutable TypedDict contracts for payloads.
    Handles all file I/O; no side effects outside this class.
    """

    def __init__(
        self,
        di: DIContainer,
        output_path: str,
        options: dict[str, Any],
    ) -> None:
        """Initialize orchestrator with output configuration.

        Args:
            di: Dependency Injection container for orchestration.
            output_path: Output file path for primary output.
            options: Scan configuration dict containing:
                - output_format: Output format (md, json, html, pdf)
                - concise_readme: Whether to emit concise README mode
                - template: Optional template override path
                - scanner_report_output: Optional scanner-report output path
                - include_scanner_report_link: Link to scanner report
                - runbook_output: Optional runbook output path
                - runbook_csv_output: Optional runbook CSV output path
        """
        if not output_path:
            raise ValueError("output_path must not be empty")
        if options is None:
            raise ValueError("options must not be None")

        self._di = di
        self._output_path = output_path
        self._options = options

    def render_and_emit(
        self,
        payload: RunScanOutputPayload,
        dry_run: bool = False,
    ) -> str | bytes:
        """Render primary output and emit sidecars.

        Renders the primary output based on output_format from options.
        Generates sidecar files if configured. Creates new payload with updated metadata
        (does not mutate input payload).

        Args:
            payload: Complete scan results from discovery and features (immutable contract).
            dry_run: If True, render but don't write files.

        Returns:
            Rendered output content as string or bytes (primary output).

        **Immutability Note:**
        - Input payload is treated as immutable; no direct mutations
        - Updated metadata is passed via kwargs to render functions
        - New payload structures created as needed (immutable construction)
        """
        output_format = self._options.get("output_format", "md")
        concise_readme = self._options.get("concise_readme", False)
        template = self._options.get("template")
        scanner_report_output = self._options.get("scanner_report_output")
        include_scanner_report_link = self._options.get(
            "include_scanner_report_link", False
        )
        runbook_output = self._options.get("runbook_output")
        runbook_csv_output = self._options.get("runbook_csv_output")

        output_payload = {
            **payload,
            "metadata": dict(payload["metadata"]),
        }
        emission_args = _build_output_emission_context(
            output_payload=output_payload,
            output=self._output_path,
            output_format=output_format,
            template=template,
            dry_run=dry_run,
            concise_readme=concise_readme,
            scanner_report_output=scanner_report_output,
            include_scanner_report_link=include_scanner_report_link,
            runbook_output=runbook_output,
            runbook_csv_output=runbook_csv_output,
        )

        return _orchestrate_output_emission(
            args=emission_args,
            render_and_write=lambda **kwargs: _render_and_write_scan_output(
                out_path=kwargs["out_path"],
                output_format=kwargs["output_format"],
                role_name=output_payload["role_name"],
                description=output_payload["description"],
                display_variables=output_payload["display_variables"],
                requirements_display=output_payload["requirements_display"],
                undocumented_default_filters=output_payload[
                    "undocumented_default_filters"
                ],
                metadata=emission_args["metadata"],
                template=kwargs["template"],
                dry_run=kwargs["dry_run"],
                render_readme=render_readme,
                render_final_output=render_final_output,
                write_output=write_output,
            ),
            render_scanner_report=lambda **kwargs: build_scanner_report_markdown(
                render_section_body=render_guide_section_body,
                **kwargs,
            ),
            render_runbook=render_runbook,
            render_runbook_csv=render_runbook_csv,
        )

    def emit_runbook_sidecars(
        self,
        md_path: str,
        csv_path: str,
        *,
        role_name: str = "role",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """Emit runbook markdown and CSV sidecars to specified paths.

        Args:
            md_path: Path for runbook markdown file.
            csv_path: Path for runbook CSV file.

        Returns:
            Dict mapping file path → bytes written.
        """
        result: dict[str, int] = {}

        sidecar_metadata: dict[str, Any] = metadata or {}

        # Write markdown runbook if path provided
        if md_path:
            md_path_obj = Path(md_path)
            md_path_obj.parent.mkdir(parents=True, exist_ok=True)
            rb_content = render_runbook(
                role_name=role_name,
                metadata=sidecar_metadata,
            )
            md_path_obj.write_text(rb_content, encoding="utf-8")
            result[md_path] = len(rb_content.encode("utf-8"))

        # Write CSV runbook if path provided
        if csv_path:
            csv_path_obj = Path(csv_path)
            csv_path_obj.parent.mkdir(parents=True, exist_ok=True)
            rb_csv_content = render_runbook_csv(sidecar_metadata)
            csv_path_obj.write_text(rb_csv_content, encoding="utf-8")
            result[csv_path] = len(rb_csv_content.encode("utf-8"))

        return result
