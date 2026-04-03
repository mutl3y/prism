"""Primary scan output rendering/write orchestration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .output import build_final_output_payload
from ..scanner_data.contracts_output import RunScanOutputPayload


def render_and_write_scan_output(
    *,
    out_path: Path,
    output_format: str,
    role_name: str,
    description: str,
    display_variables: dict[str, Any],
    requirements_display: list[Any],
    undocumented_default_filters: list[dict[str, Any]],
    metadata: dict[str, Any],
    template: str | None,
    dry_run: bool,
    render_readme: Callable[..., str],
    render_final_output: Callable[..., str | bytes],
    write_output: Callable[[Path, str | bytes], str],
) -> str | bytes:
    """Render final output payload and write it unless dry-run is enabled."""
    rendered = ""
    if output_format != "json":
        rendered = render_readme(
            str(out_path),
            role_name,
            description,
            display_variables,
            requirements_display,
            undocumented_default_filters,
            template,
            metadata,
            write=False,
        )

    final_content = render_final_output(
        rendered,
        output_format,
        role_name,
        payload=build_final_output_payload(
            role_name=role_name,
            description=description,
            variables=display_variables,
            requirements=requirements_display,
            default_filters=undocumented_default_filters,
            metadata=metadata,
        ),
    )
    if dry_run:
        return final_content
    return write_output(out_path, final_content)


def render_primary_scan_output(
    *,
    out_path: Path,
    output_format: str,
    template: str | None,
    dry_run: bool,
    output_payload: RunScanOutputPayload,
    render_and_write_scan_output: Callable[..., str | bytes],
) -> str | bytes:
    """Render and optionally write the primary scan output."""
    return render_and_write_scan_output(
        out_path=out_path,
        output_format=output_format,
        role_name=output_payload["role_name"],
        description=output_payload["description"],
        display_variables=output_payload["display_variables"],
        requirements_display=output_payload["requirements_display"],
        undocumented_default_filters=output_payload["undocumented_default_filters"],
        metadata=output_payload["metadata"],
        template=template,
        dry_run=dry_run,
    )
