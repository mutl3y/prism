"""Runbook rendering helpers.

This module isolates runbook-specific formatting from scanner orchestration.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from prism.scanner_data.rendering_seams import build_render_jinja_environment


def render_runbook(
    role_name: str,
    metadata: dict | None = None,
    template: str | None = None,
) -> str:
    """Render a standalone runbook markdown document for a role."""
    metadata = metadata or {}
    if template:
        tpl_file = Path(template)
    else:
        tpl_file = (
            Path(__file__).resolve().parent.parent / "templates" / "RUNBOOK.md.j2"
        )

    env = build_render_jinja_environment(
        template_dir=tpl_file.parent,
        metadata=metadata,
    )
    template_obj = env.get_template(tpl_file.name)
    return template_obj.render(role_name=role_name, metadata=metadata)


def build_runbook_rows(metadata: dict[str, Any] | None) -> list[tuple[str, str, str]]:
    """Build normalized runbook rows: (file, task_name, step)."""
    metadata = metadata or {}
    task_catalog = metadata.get("task_catalog") or []
    rows: list[tuple[str, str, str]] = []
    for task in task_catalog:
        if not isinstance(task, dict):
            continue
        file_name = str(task.get("file") or "")
        task_name = str(task.get("name") or "")
        annotations = task.get("annotations") or []
        if not isinstance(annotations, list):
            annotations = []

        for note in annotations:
            if not isinstance(note, dict):
                continue
            text = str(note.get("text") or "").strip()
            if not text:
                continue
            kind = str(note.get("kind") or "note").strip().lower()
            step = text if kind == "runbook" else f"{kind.capitalize()}: {text}"
            rows.append((file_name, task_name, step))
    return rows


def render_runbook_csv(metadata: dict | None = None) -> str:
    """Render runbook rows to CSV with columns: file, task_name, step."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["file", "task_name", "step"])
    for file_name, task_name, step in build_runbook_rows(metadata):
        writer.writerow([file_name, task_name, step])
    return output.getvalue()
