#!/usr/bin/env python3
"""Roll up and rotate model-usage telemetry for review cycles.

This script reads per-cycle ledgers at:
    docs/plan/gilfoyle-review-*/artifacts/model-usage-ledger.yaml
    docs/plan/mutl3y-review-*/artifacts/model-usage-ledger.yaml

It writes a compact rollup to:
    docs/plan/.mutl3y-lessons/model-usage-rollup.yaml

It can also rotate the long-running lessons history file:
    docs/plan/.mutl3y-lessons/model-usage-history.yaml
keeping only the most recent N cycle snapshots and archiving dropped entries to:
    docs/plan/.mutl3y-lessons/archive/
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_GLOBS = (
    "docs/plan/gilfoyle-review-*/artifacts/model-usage-ledger.yaml",
    "docs/plan/mutl3y-review-*/artifacts/model-usage-ledger.yaml",
)
LESSONS_DIR = REPO_ROOT / "docs/plan/.mutl3y-lessons"
ROLLUP_PATH = LESSONS_DIR / "model-usage-rollup.yaml"
HISTORY_PATH = LESSONS_DIR / "model-usage-history.yaml"
ARCHIVE_DIR = LESSONS_DIR / "archive"


def _cycle_key(cycle: str) -> tuple[int, str]:
    if cycle.startswith("g") and cycle[1:].isdigit():
        return int(cycle[1:]), cycle
    return 0, cycle


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _collect_ledgers() -> list[dict[str, Any]]:
    ledgers: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for ledger_glob in LEDGER_GLOBS:
        for path in sorted(REPO_ROOT.glob(ledger_glob)):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            data = _load_yaml(path)
            cycle = str(data.get("cycle") or "")
            if not cycle:
                plan_part = path.parts[-4] if len(path.parts) >= 4 else ""
                if "-g" in plan_part:
                    cycle = f"g{plan_part.rsplit('-g', 1)[-1]}"
            ledgers.append({"path": path, "cycle": cycle, "data": data})
    ledgers.sort(key=lambda item: _cycle_key(item["cycle"]))
    return ledgers


def _new_model_stat() -> dict[str, Any]:
    return {
        "attempts": 0,
        "successes": 0,
        "route_failures": 0,
        "quality_failures": 0,
        "reedit_count": 0,
        "quality_total": 0.0,
        "quality_samples": 0,
        "quality_avg": 0.0,
        "route_failure_rate": 0.0,
        "quality_failure_rate": 0.0,
        "reedit_rate": 0.0,
        "status": "healthy",
    }


def _update_status(stat: dict[str, Any]) -> None:
    attempts = stat["attempts"]
    if attempts <= 0:
        stat["status"] = "healthy"
        return

    route_rate = stat["route_failures"] / attempts
    quality_rate = stat["quality_failures"] / attempts
    reedit_rate = stat["reedit_count"] / attempts

    stat["route_failure_rate"] = round(route_rate, 4)
    stat["quality_failure_rate"] = round(quality_rate, 4)
    stat["reedit_rate"] = round(reedit_rate, 4)
    stat["quality_avg"] = (
        round(stat["quality_total"] / stat["quality_samples"], 3)
        if stat["quality_samples"]
        else 0.0
    )

    if attempts >= 5 and route_rate >= 0.2:
        stat["status"] = "degraded"
        return
    if attempts >= 8 and quality_rate >= 0.25:
        stat["status"] = "degraded"
        return
    if attempts >= 1 and route_rate >= 1.0:
        stat["status"] = "watch"
        return
    if attempts >= 3 and reedit_rate >= 0.5:
        stat["status"] = "watch"
        return
    stat["status"] = "healthy"


def _aggregate_model_stats(ledgers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_model: dict[str, dict[str, Any]] = {}

    for ledger in ledgers:
        entries = ledger["data"].get("entries", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            model = str(
                entry.get("actual_model") or entry.get("requested_model") or "unknown"
            )
            stat = by_model.setdefault(model, _new_model_stat())
            stat["attempts"] += 1

            result = str(entry.get("result") or "")
            if result == "success":
                stat["successes"] += 1
            if result == "route_failure":
                stat["route_failures"] += 1

            quality_score = entry.get("quality_score")
            if isinstance(quality_score, (int, float)):
                stat["quality_total"] += float(quality_score)
                stat["quality_samples"] += 1
                if float(quality_score) <= 2:
                    stat["quality_failures"] += 1

            if bool(entry.get("needed_reedit")):
                stat["reedit_count"] += 1

    for stat in by_model.values():
        _update_status(stat)
        stat.pop("quality_total", None)
        stat.pop("quality_samples", None)

    return dict(sorted(by_model.items()))


def _aggregate_task_class_stats(
    ledgers: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    task_stats: dict[str, dict[str, Any]] = {}
    for ledger in ledgers:
        entries = ledger["data"].get("entries", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            worker = str(entry.get("worker") or "unknown")
            phase = str(entry.get("phase") or "unknown")
            key = f"{phase}:{worker}"
            stat = task_stats.setdefault(
                key,
                {
                    "attempts": 0,
                    "successes": 0,
                    "route_failures": 0,
                    "quality_failures": 0,
                    "reedit_count": 0,
                },
            )
            stat["attempts"] += 1
            result = str(entry.get("result") or "")
            if result == "success":
                stat["successes"] += 1
            if result == "route_failure":
                stat["route_failures"] += 1
            quality_score = entry.get("quality_score")
            if isinstance(quality_score, (int, float)) and float(quality_score) <= 2:
                stat["quality_failures"] += 1
            if bool(entry.get("needed_reedit")):
                stat["reedit_count"] += 1

    return dict(sorted(task_stats.items()))


def _build_rollup(window_cycles: int) -> dict[str, Any]:
    ledgers = _collect_ledgers()
    cycles = [item["cycle"] for item in ledgers if item["cycle"]]
    unique_cycles = sorted(set(cycles), key=_cycle_key)

    window = unique_cycles[-window_cycles:] if window_cycles > 0 else unique_cycles
    window_set = set(window)
    ledgers_window = [item for item in ledgers if item["cycle"] in window_set]

    all_time_model = _aggregate_model_stats(ledgers)
    all_time_tasks = _aggregate_task_class_stats(ledgers)
    window_model = _aggregate_model_stats(ledgers_window)
    window_tasks = _aggregate_task_class_stats(ledgers_window)

    degraded_models = [
        name
        for name, stat in all_time_model.items()
        if stat.get("status") == "degraded"
    ]
    watch_models = [
        name for name, stat in all_time_model.items() if stat.get("status") == "watch"
    ]

    return {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "ledger_globs": list(LEDGER_GLOBS),
            "ledger_count": len(ledgers),
            "cycles_seen": unique_cycles,
        },
        "windows": {
            "all_time": {
                "by_model": all_time_model,
                "by_task_class": all_time_tasks,
            },
            f"last_{window_cycles}_cycles": {
                "cycles": window,
                "by_model": window_model,
                "by_task_class": window_tasks,
            },
        },
        "routing_recommendations": {
            "degraded_models": degraded_models,
            "watch_models": watch_models,
            "notes": [
                "Prefer healthy models in the same tier before escalating.",
                "If degraded_models is non-empty, start ladders from next healthy candidate.",
            ],
        },
    }


def _rotate_history(history_keep: int) -> dict[str, Any]:
    if history_keep <= 0:
        return {"rotated": False, "reason": "history_keep<=0"}

    data = _load_yaml(HISTORY_PATH)
    cycles = data.get("cycles", [])
    if not isinstance(cycles, list):
        return {"rotated": False, "reason": "cycles_not_list"}

    if len(cycles) <= history_keep:
        return {
            "rotated": False,
            "reason": "within_limit",
            "kept": len(cycles),
            "dropped": 0,
        }

    sorted_cycles = sorted(
        cycles,
        key=lambda item: _cycle_key(str(item.get("cycle") or "")),
    )
    kept = sorted_cycles[-history_keep:]
    dropped = sorted_cycles[:-history_keep]

    archive_payload = {
        "version": 1,
        "archived_at": datetime.now(UTC).isoformat(),
        "source": str(HISTORY_PATH.relative_to(REPO_ROOT)),
        "dropped_cycles": dropped,
    }

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_name = f"model-usage-history-archive-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.yaml"
    archive_path = ARCHIVE_DIR / archive_name
    archive_path.write_text(
        yaml.safe_dump(archive_payload, sort_keys=False),
        encoding="utf-8",
    )

    data["cycles"] = kept
    data["updated_at"] = datetime.now(UTC).date().isoformat()
    HISTORY_PATH.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    return {
        "rotated": True,
        "kept": len(kept),
        "dropped": len(dropped),
        "archive_path": str(archive_path.relative_to(REPO_ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window-cycles",
        type=int,
        default=3,
        help="Window size for rolling model/task metrics (default: 3)",
    )
    parser.add_argument(
        "--history-keep",
        type=int,
        default=20,
        help="How many cycles to keep in model-usage-history.yaml before archiving",
    )
    parser.add_argument(
        "--no-rotate-history",
        action="store_true",
        help="Skip rotating model-usage-history.yaml",
    )
    args = parser.parse_args()

    LESSONS_DIR.mkdir(parents=True, exist_ok=True)

    rollup = _build_rollup(window_cycles=max(1, args.window_cycles))
    ROLLUP_PATH.write_text(yaml.safe_dump(rollup, sort_keys=False), encoding="utf-8")

    print(f"Wrote rollup: {ROLLUP_PATH.relative_to(REPO_ROOT)}")
    print(f"Ledgers scanned: {rollup['source']['ledger_count']}")

    if args.no_rotate_history:
        print("Skipped history rotation (--no-rotate-history).")
        return 0

    rotation = _rotate_history(history_keep=args.history_keep)
    if rotation.get("rotated"):
        print(
            "Rotated model history: "
            f"kept={rotation['kept']} dropped={rotation['dropped']} "
            f"archive={rotation['archive_path']}"
        )
    else:
        print(
            "No history rotation: "
            f"{rotation.get('reason', 'unknown')} "
            f"kept={rotation.get('kept', 0)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
