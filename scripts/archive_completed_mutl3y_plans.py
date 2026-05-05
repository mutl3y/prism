#!/usr/bin/env python3
"""Archive completed Mutl3y workflow plan directories out of docs/plan root.

This helper is intentionally conservative: it only moves plan directories whose
name starts with ``mutl3y-review-workflow-`` and whose ``plan.yaml`` status is
``completed``. Paused or in-progress runs stay in the active plan root.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_ROOT = REPO_ROOT / "docs" / "plan"
ARCHIVE_ROOT = PLAN_ROOT / "archive"
PREFIX = "mutl3y-review-workflow-"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected mapping-shaped YAML: {path}")
    return data


def _plan_dir(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if path.name == "plan.yaml":
        path = path.parent
    return path


def _eligible(plan_dir: Path) -> bool:
    if plan_dir.parent != PLAN_ROOT:
        return False
    if not plan_dir.name.startswith(PREFIX):
        return False
    plan_path = plan_dir / "plan.yaml"
    if not plan_path.exists():
        return False
    payload = _load_yaml(plan_path)
    return str(payload.get("status") or "").strip().lower() == "completed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+", help="Plan directories or plan.yaml paths")
    args = parser.parse_args()

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)

    for raw in args.plans:
        plan_dir = _plan_dir(raw)
        if not _eligible(plan_dir):
            print(f"SKIP {plan_dir.relative_to(REPO_ROOT).as_posix()}")
            continue
        destination = ARCHIVE_ROOT / plan_dir.name
        if destination.exists():
            print(
                f"SKIP {plan_dir.relative_to(REPO_ROOT).as_posix()} -> archive/{plan_dir.name} (already exists)"
            )
            continue
        shutil.move(str(plan_dir), str(destination))
        print(
            f"ARCHIVED {plan_dir.relative_to(REPO_ROOT).as_posix()} -> "
            f"{destination.relative_to(REPO_ROOT).as_posix()}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
