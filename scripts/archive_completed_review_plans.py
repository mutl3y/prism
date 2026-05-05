#!/usr/bin/env python3
"""Archive completed review-plan directories out of docs/plan root.

This helper is conservative: it only moves directories directly under
``docs/plan`` whose ``plan.yaml`` status is ``completed``. Callers can keep the
latest completed plan per prefix family visible at the top level so the root
still exposes the most recent working history.
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


def _completed(plan_dir: Path) -> bool:
    if plan_dir.parent != PLAN_ROOT:
        return False
    plan_path = plan_dir / "plan.yaml"
    if not plan_path.exists():
        return False
    payload = _load_yaml(plan_path)
    return str(payload.get("status") or "").strip().lower() == "completed"


def _latest_by_prefix(plans: list[Path], prefixes: list[str]) -> set[Path]:
    keep: set[Path] = set()
    for prefix in prefixes:
        matches = sorted(plan for plan in plans if plan.name.startswith(prefix))
        if matches:
            keep.add(matches[-1])
    return keep


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+", help="Plan directories or plan.yaml paths")
    parser.add_argument(
        "--keep-latest-prefix",
        action="append",
        default=[],
        help="Prefix family for which the lexically latest completed plan should remain top-level.",
    )
    args = parser.parse_args()

    plan_dirs = [_plan_dir(raw) for raw in args.plans]
    completed = [plan for plan in plan_dirs if _completed(plan)]
    keep = _latest_by_prefix(completed, list(args.keep_latest_prefix))

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)

    for plan_dir in plan_dirs:
        rel = plan_dir.relative_to(REPO_ROOT).as_posix()
        if not _completed(plan_dir):
            print(f"SKIP {rel}")
            continue
        if plan_dir in keep:
            print(f"KEEP {rel}")
            continue
        destination = ARCHIVE_ROOT / plan_dir.name
        if destination.exists():
            print(
                f"SKIP {rel} -> {destination.relative_to(REPO_ROOT).as_posix()} (already exists)"
            )
            continue
        shutil.move(str(plan_dir), str(destination))
        print(f"ARCHIVED {rel} -> {destination.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
