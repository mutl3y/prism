"""Output rendering and writing helpers.

This module isolates output-format concerns from scan/discovery logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


class FinalOutputPayload(TypedDict):
    """Typed payload passed into final output rendering."""

    role_name: str
    description: str
    variables: dict[str, Any]
    requirements: list[Any]
    default_filters: list[dict[str, Any]]
    metadata: dict[str, Any]


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
    return {
        "role_name": role_name,
        "description": description,
        "variables": variables,
        "requirements": requirements,
        "default_filters": default_filters,
        "metadata": metadata,
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
    try:
        import markdown as _md

        html_body = _md.markdown(markdown_content, extensions=["extra", "toc"])
    except Exception:
        import html as _html

        html_body = f"<pre>{_html.escape(markdown_content)}</pre>"

    return f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{title}</title></head><body>\n{html_body}\n</body></html>'


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
