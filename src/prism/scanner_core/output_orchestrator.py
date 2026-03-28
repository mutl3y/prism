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

import os
from pathlib import Path
from typing import Any

from .di import DIContainer
from ..scanner_data.contracts import RunScanOutputPayload
from ..scanner_io import (
    render_final_output,
    resolve_output_path,
    write_output,
)
from ..scanner_readme import render_readme
from ..scanner_analysis import build_scanner_report_markdown
from ..scanner_analysis import render_runbook, render_runbook_csv


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
        # Extract configuration from options
        output_format = self._options.get("output_format", "md")
        concise_readme = self._options.get("concise_readme", False)
        template = self._options.get("template")
        scanner_report_output = self._options.get("scanner_report_output")
        include_scanner_report_link = self._options.get(
            "include_scanner_report_link", False
        )
        runbook_output = self._options.get("runbook_output")
        runbook_csv_output = self._options.get("runbook_csv_output")

        # Create new metadata dict with output configuration (don't mutate payload)
        updated_metadata = {
            **payload["metadata"],
            "concise_readme": concise_readme,
            "include_scanner_report_link": include_scanner_report_link,
        }

        # Resolve and normalize output path
        out_path = resolve_output_path(self._output_path, output_format)

        # Handle scanner-report sidecar only in write mode
        if concise_readme and not dry_run:
            _write_concise_scanner_report_if_enabled(
                concise_readme=concise_readme,
                scanner_report_output=scanner_report_output,
                out_path=out_path,
                include_scanner_report_link=include_scanner_report_link,
                role_name=payload["role_name"],
                description=payload["description"],
                display_variables=payload["display_variables"],
                requirements_display=payload["requirements_display"],
                undocumented_default_filters=payload["undocumented_default_filters"],
                metadata=updated_metadata,
                dry_run=False,
            )

        # Handle runbook sidecars only in write mode
        if not dry_run and (runbook_output or runbook_csv_output):
            self.emit_runbook_sidecars(
                runbook_output or "",
                runbook_csv_output or "",
                role_name=payload["role_name"],
                metadata=updated_metadata,
            )

        # Render primary output
        rendered = ""
        if output_format != "json":
            rendered = render_readme(
                output=str(out_path),
                role_name=payload["role_name"],
                description=payload["description"],
                variables=payload["display_variables"],
                requirements=payload["requirements_display"],
                default_filters=payload["undocumented_default_filters"],
                template=template,
                metadata=updated_metadata,
                write=False,
            )

        # Render final output in requested format
        final_content = render_final_output(
            markdown_content=rendered,
            output_format=output_format,
            title=payload["role_name"],
            payload={
                "role_name": payload["role_name"],
                "description": payload["description"],
                "variables": payload["display_variables"],
                "requirements": payload["requirements_display"],
                "default_filters": payload["undocumented_default_filters"],
                "metadata": updated_metadata,
            },
        )

        # Write output unless dry-run is enabled
        if dry_run:
            return final_content

        # Create output directory if needed
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file and return the path
        return write_output(out_path, final_content)

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


# ============================================================================
# Helper Functions
# ============================================================================


def _write_concise_scanner_report_if_enabled(
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
    metadata: dict[str, Any],
    dry_run: bool,
) -> Path | None:
    """Write scanner sidecar report when concise mode is enabled.

    Args:
        concise_readme: Whether concise mode is enabled.
        scanner_report_output: Explicit output path for scanner report.
        out_path: Main output path (used for relative path calculation).
        include_scanner_report_link: Whether to link to report from README.
        role_name: Role name.
        description: Role description.
        display_variables: Rendered variable list.
        requirements_display: Rendered requirements list.
        undocumented_default_filters: Default filters without documentation.
        metadata: Scan metadata (mutated in-place).
        dry_run: If True, don't write files.

    Returns:
        Path to scanner report if written, else None.
    """
    if not concise_readme:
        return None

    # Determine scanner report path
    if scanner_report_output:
        scanner_report_path = Path(scanner_report_output)
    else:
        scanner_report_path = out_path.with_suffix(".scan-report.md")

    if dry_run:
        return scanner_report_path

    # Create parent directory
    scanner_report_path.parent.mkdir(parents=True, exist_ok=True)

    # Render scanner report
    scanner_report = build_scanner_report_markdown(
        role_name=role_name,
        description=description,
        variables=display_variables,
        requirements=requirements_display,
        default_filters=undocumented_default_filters,
        metadata=metadata,
        render_section_body=lambda *_args, **_kwargs: "",
    )

    # Write scanner report
    scanner_report_path.write_text(scanner_report, encoding="utf-8")

    # Update metadata with relative path
    metadata["scanner_report_relpath"] = os.path.relpath(
        scanner_report_path,
        out_path.parent,
    )

    return scanner_report_path
