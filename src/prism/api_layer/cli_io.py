"""CLI I/O facade for the fsrc package layer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import prism.scanner_io as scanner_io
from prism.scanner_io.output import write_role_scan_output as _write_role_scan_output

if TYPE_CHECKING:
    pass


def write_role_scan_output(
    payload: dict,
    output: str,
    output_format: str = "markdown",
    dry_run: bool = False,
) -> str | None:
    """Facade for scanner_io.output.write_role_scan_output."""
    return _write_role_scan_output(
        payload,
        output=output,
        output_format=output_format,
        dry_run=dry_run,
    )


def render_collection_markdown(payload: dict) -> str:
    """Facade for scanner_io.render_collection_markdown."""
    return scanner_io.render_collection_markdown(payload)


def resolve_output_path(output: str | None, format_: str) -> Path:
    """Facade for scanner_io.resolve_output_path."""
    return scanner_io.resolve_output_path(output, format_)  # type: ignore[arg-type]


def write_output(output_path: Path, rendered: str) -> str:
    """Facade for scanner_io.write_output."""
    return scanner_io.write_output(output_path, rendered)


def format_collection_summary(payload: dict) -> str:
    """Facade for scanner_io.format_collection_summary."""
    return scanner_io.format_collection_summary(payload)
