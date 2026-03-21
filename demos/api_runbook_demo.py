#!/usr/bin/env python3
"""API demo that renders runbook markdown and CSV from a role scan."""

from __future__ import annotations

from pathlib import Path

from prism.api import render_runbook, render_runbook_csv, scan_role


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    role_path = root / "demos" / "fixtures" / "role_demo"
    output_dir = root / "demos" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = scan_role(
        str(role_path), detailed_catalog=True, include_task_runbooks=True
    )
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    role_name = (
        payload.get("role_name", "role_demo")
        if isinstance(payload, dict)
        else "role_demo"
    )

    runbook_markdown = render_runbook(role_name, metadata)
    runbook_csv = render_runbook_csv(metadata)

    (output_dir / "api_role_demo_RUNBOOK.md").write_text(
        runbook_markdown, encoding="utf-8"
    )
    (output_dir / "api_role_demo_RUNBOOK.csv").write_text(runbook_csv, encoding="utf-8")

    print("Wrote demos/output/api_role_demo_RUNBOOK.md")
    print("Wrote demos/output/api_role_demo_RUNBOOK.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
