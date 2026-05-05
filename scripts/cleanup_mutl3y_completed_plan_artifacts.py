#!/usr/bin/env python3
"""Prune non-canonical Mutl3y workflow artifacts from completed plans.

This helper removes pure wave scaffolding after Phase 7 closure when the plan
already has a retained closure summary and execution trace. It intentionally
keeps canonical evidence surfaces such as findings, barrier summaries, builder
summaries, gate logs, model ledgers, execution traces, and closure summaries.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
PRUNABLE_ARTIFACT_KEYS = (
    "wave_start_audit",
    "wave_plan",
    "phase5_wave_start_audit",
    "phase5_wave_plan",
)
CLOSURE_SUMMARY_KEYS = ("closure_summary", "phase7_closure_summary")


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected mapping-shaped YAML: {path}")
    return data


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, width=100),
        encoding="utf-8",
    )


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def _plan_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_dir():
        path = path / "plan.yaml"
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def _cleanup_actions(
    plan: dict[str, Any], plan_path: Path
) -> tuple[list[str], list[Path]]:
    artifacts = plan.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit(f"expected artifacts mapping in {plan_path}")

    status = str(plan.get("status") or "").strip().lower()
    if status != "completed":
        return [], []
    if "execution_trace" not in artifacts:
        return [], []
    if not any(key in artifacts for key in CLOSURE_SUMMARY_KEYS):
        return [], []

    removed_keys: list[str] = []
    removed_paths: list[Path] = []
    for key in PRUNABLE_ARTIFACT_KEYS:
        raw_path = artifacts.pop(key, None)
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        artifact_path = _resolve_path(raw_path)
        if artifact_path.exists():
            artifact_path.unlink()
        removed_keys.append(key)
        removed_paths.append(artifact_path)
    return removed_keys, removed_paths


def _update_closure_summary(
    plan: dict[str, Any], removed_keys: list[str], removed_paths: list[Path]
) -> None:
    if not removed_keys:
        return
    artifacts = plan["artifacts"]
    closure_raw = next(
        artifacts[key] for key in CLOSURE_SUMMARY_KEYS if key in artifacts
    )
    closure_path = _resolve_path(closure_raw)
    closure = _load_yaml(closure_path)
    assessment = closure.get("artifact_cleanup_assessment")
    if not isinstance(assessment, dict):
        assessment = {}
        closure["artifact_cleanup_assessment"] = assessment
    cleanup_actions = assessment.get("cleanup_actions")
    if not isinstance(cleanup_actions, list):
        cleanup_actions = []
        assessment["cleanup_actions"] = cleanup_actions
    for key, path in zip(removed_keys, removed_paths, strict=True):
        action = f"Removed stale {key} scaffolding artifact: {path.relative_to(REPO_ROOT).as_posix()}"
        if action not in cleanup_actions:
            cleanup_actions.append(action)
    _write_yaml(closure_path, closure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+", help="Plan directories or plan.yaml paths")
    args = parser.parse_args()

    for raw in args.plans:
        plan_path = _plan_path(raw)
        plan = _load_yaml(plan_path)
        removed_keys, removed_paths = _cleanup_actions(plan, plan_path)
        if not removed_keys:
            print(f"SKIP {plan_path.relative_to(REPO_ROOT).as_posix()}")
            continue
        _write_yaml(plan_path, plan)
        _update_closure_summary(plan, removed_keys, removed_paths)
        print(f"CLEANED {plan_path.relative_to(REPO_ROOT).as_posix()}")
        for key, path in zip(removed_keys, removed_paths, strict=True):
            print(f"  - {key}: {path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
