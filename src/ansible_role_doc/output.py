"""Output rendering and writing helpers.

This module isolates output-format concerns from scan/discovery logic.
"""

from __future__ import annotations

import json
from pathlib import Path


def resolve_output_path(output: str, output_format: str) -> Path:
    """Return normalized output path for the requested format."""
    out_path = Path(output)
    if output_format == "html" and out_path.suffix.lower() not in (".html", ".htm"):
        return out_path.with_suffix(".html")
    if output_format == "json" and out_path.suffix.lower() != ".json":
        return out_path.with_suffix(".json")
    return out_path


def render_final_output(
    markdown_content: str,
    output_format: str,
    title: str,
    payload: dict | None = None,
) -> str:
    """Return output payload in the requested format."""
    if output_format == "md":
        return markdown_content

    if output_format == "json":
        return json.dumps(payload or {}, indent=2, sort_keys=True, default=str) + "\n"

    try:
        import markdown as _md

        html_body = _md.markdown(markdown_content, extensions=["extra", "toc"])
    except Exception:
        import html as _html

        html_body = f"<pre>{_html.escape(markdown_content)}</pre>"

    return f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{title}</title></head><body>\n{html_body}\n</body></html>'


def write_output(path: Path, content: str) -> str:
    """Write content to disk and return absolute path as string."""
    path.write_text(content, encoding="utf-8")
    return str(path.resolve())
