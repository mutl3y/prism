"""Runbook rendering owned by the comment-driven documentation parser layer.

Renders a standalone runbook markdown document or CSV from comment-driven
annotations attached to a task catalog. The runbook template lives in
``parsers/comment_doc/templates/RUNBOOK.md.j2``.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NamedTuple

from prism.scanner_plugins.parsers.comment_doc.jinja_utils import (
    build_render_jinja_environment,
)


class RunbookRow(NamedTuple):
    """Normalized runbook row exposed by build_runbook_rows / render_runbook_csv."""

    file: str
    task_name: str
    step: str


def render_runbook(
    role_name: str,
    metadata: Mapping[str, Any] | None = None,
    template: str | None = None,
) -> str:
    """Render a standalone runbook markdown document for a role."""
    metadata = metadata or {}
    if template:
        tpl_file = Path(template)
    else:
        tpl_file = Path(__file__).resolve().parent / "templates" / "RUNBOOK.md.j2"

    env = build_render_jinja_environment(
        template_dir=tpl_file.parent,
        metadata=metadata,
    )
    template_obj = env.get_template(tpl_file.name)
    return template_obj.render(role_name=role_name, metadata=metadata)


def build_runbook_rows(metadata: Mapping[str, Any] | None) -> list[RunbookRow]:
    """Build normalized runbook rows: (file, task_name, step)."""
    metadata = metadata or {}
    task_catalog = metadata.get("task_catalog") or []
    rows: list[RunbookRow] = []
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
            rows.append(RunbookRow(file_name, task_name, step))
    return rows


def render_runbook_csv(metadata: Mapping[str, Any] | None = None) -> str:
    """Render runbook rows to CSV with columns: file, task_name, step."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["file", "task_name", "step"])
    for row in build_runbook_rows(metadata):
        writer.writerow([row.file, row.task_name, row.step])
    return output.getvalue()


__all__ = [
    "RunbookRow",
    "build_runbook_rows",
    "render_runbook",
    "render_runbook_csv",
]
