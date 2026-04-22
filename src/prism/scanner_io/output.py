"""Output rendering and writing helpers for the fsrc lane."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prism.scanner_data.contracts_output import FinalOutputPayload


def build_final_output_payload(
    *,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> FinalOutputPayload:
    """Build the typed final-output payload contract."""
    warnings = metadata.get("warnings")
    normalized_warnings = warnings if isinstance(warnings, list) else []
    return {
        "role_name": role_name,
        "description": description,
        "variables": variables,
        "requirements": requirements,
        "default_filters": default_filters,
        "metadata": metadata,
        "warnings": normalized_warnings,
    }


def resolve_output_path(output: str, output_format: str) -> Path:
    """Return normalized output path for the requested format."""
    out_path = Path(output)
    if output_format == "html" and out_path.suffix.lower() not in (".html", ".htm"):
        return out_path.with_suffix(".html")
    if output_format == "json" and out_path.suffix.lower() != ".json":
        return out_path.with_suffix(".json")
    if output_format == "pdf" and out_path.suffix.lower() != ".pdf":
        return out_path.with_suffix(".pdf")
    return out_path


def _render_html_document(markdown_content: str, title: str) -> str:
    import html as _html

    try:
        import markdown as _md
    except ImportError:
        html_body = f"<pre>{_html.escape(markdown_content)}</pre>"
    else:
        try:
            html_body = _md.markdown(markdown_content, extensions=["extra", "toc"])
        except (ImportError, AttributeError, TypeError, ValueError):
            html_body = f"<pre>{_html.escape(markdown_content)}</pre>"

    escaped_title = _html.escape(title, quote=True)
    return f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{escaped_title}</title></head><body>\n{html_body}\n</body></html>'


def render_final_output(
    markdown_content: str,
    output_format: str,
    title: str,
    payload: FinalOutputPayload | None = None,
) -> str | bytes:
    """Return output payload in the requested format."""
    if output_format == "md":
        return markdown_content

    if output_format == "json":
        return json.dumps(payload or {}, indent=2, sort_keys=True, default=str) + "\n"

    html_doc = _render_html_document(markdown_content, title)
    if output_format == "html":
        return html_doc

    if output_format == "pdf":
        try:
            from weasyprint import HTML
        except Exception as exc:
            raise RuntimeError(
                "PDF output requires optional dependency 'weasyprint'"
            ) from exc
        return HTML(string=html_doc).write_pdf()

    return html_doc


def write_output(path: Path, content: str | bytes) -> str:
    """Write content to disk and return absolute path as string."""
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return str(path.resolve())


def render_role_scan_markdown(payload: dict[str, Any]) -> str:
    """Render a role scan payload dict to a markdown document.

    Accepts the flat dict returned by ``api.scan_role()`` and produces clean
    markdown without any Jinja template dependency.
    """
    role_name = str(payload.get("role_name") or "role")
    description = str(payload.get("description") or "").strip()
    variables: dict[str, Any] = payload.get("display_variables") or {}
    requirements: list[Any] = payload.get("requirements_display") or []
    default_filters: list[Any] = payload.get("undocumented_default_filters") or []
    metadata: dict[str, Any] = payload.get("metadata") or {}

    lines: list[str] = [f"# {role_name}", ""]

    if description:
        lines.extend([description, ""])

    if variables:
        lines.extend(["## Role Variables", ""])
        lines.extend(
            [
                "| Variable | Default | Type | Required | Source |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for var_name, var_info in variables.items():
            if not isinstance(var_info, dict):
                continue
            default = str(
                var_info.get("default") if var_info.get("default") is not None else ""
            )
            var_type = str(var_info.get("type") or "")
            required = "Yes" if var_info.get("required") else "No"
            source = str(var_info.get("source") or "")
            lines.append(
                f"| `{var_name}` | `{default}` | {var_type} | {required} | {source} |"
            )
        lines.append("")

    if requirements:
        lines.extend(["## Requirements", ""])
        for req in requirements:
            if isinstance(req, dict):
                req_name = req.get("name") or req.get("role") or str(req)
                lines.append(f"- {req_name}")
            else:
                lines.append(f"- {req}")
        lines.append("")

    if default_filters:
        lines.extend(["## Undocumented Variable Filters", ""])
        for item in default_filters:
            label = item.get("name", str(item)) if isinstance(item, dict) else str(item)
            lines.append(f"- `{label}`")
        lines.append("")

    variable_insights = (
        metadata.get("variable_insights") if isinstance(metadata, dict) else None
    )
    if isinstance(variable_insights, dict):
        unresolved = variable_insights.get("unresolved_count") or 0
        if unresolved:
            lines.extend(
                [
                    f"> **Scanner note:** {unresolved} unresolved variable reference(s) detected.",
                    "",
                ]
            )

    return "\n".join(lines)


def write_role_scan_output(
    payload: dict[str, Any],
    *,
    output: str,
    output_format: str,
    dry_run: bool = False,
) -> str | None:
    """Render and write a role scan payload to the requested output.

    For JSON format the raw payload dict (preserving ``display_variables``) is
    serialised directly.  For all other formats the payload is rendered to
    markdown via :func:`render_role_scan_markdown` before format conversion.

    Returns the written file path, or ``None`` when *dry_run* is ``True``
    (output is printed to stdout instead).
    """
    import sys

    if output_format == "json":
        rendered: str | bytes = (
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
        )
    else:
        md_content = render_role_scan_markdown(payload)
        rendered = render_final_output(
            md_content, output_format, str(payload.get("role_name") or "")
        )

    if dry_run:
        if isinstance(rendered, bytes):
            sys.stdout.buffer.write(rendered)
        else:
            print(rendered, end="")
        return None

    output_path = resolve_output_path(output, output_format)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return write_output(output_path, rendered)
