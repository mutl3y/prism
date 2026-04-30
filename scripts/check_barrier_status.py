#!/usr/bin/env python3
"""Deterministic barrier checker for Gilfoyle wave/phase dispatches.

Given an expected-workers YAML file, validates that:
- each expected worker has either a success or an explicit failed/cancelled status
- expected artifacts exist on disk for successful workers
- model ledger has entries for all expected workers

Writes a machine-readable barrier status YAML and exits non-zero on STALL/BLOCKED.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


RESULT_SUCCESS = {"success"}
RESULT_FAILED = {"route_failure", "quality_failure"}
FAILURE_TYPES_CANCEL = {"cancelled", "empty_response", "timeout", "startup"}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _latest_entry_for_worker(
    entries: list[dict[str, Any]], worker: str
) -> dict[str, Any] | None:
    for entry in reversed(entries):
        if str(entry.get("worker")) == worker:
            return entry
    return None


def _rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected", required=True, help="Expected workers YAML")
    parser.add_argument("--ledger", required=True, help="Model usage ledger YAML")
    parser.add_argument("--output", required=True, help="Barrier status output YAML")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    expected_path = Path(args.expected).resolve()
    ledger_path = Path(args.ledger).resolve()
    output_path = Path(args.output).resolve()

    expected = _load_yaml(expected_path)
    ledger = _load_yaml(ledger_path)

    workers = expected.get("workers", [])
    if not isinstance(workers, list) or not workers:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "BLOCKED",
            "reason": "expected_workers_missing",
            "expected_file": _rel(expected_path, repo_root),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
        return 2

    entries = ledger.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    checks: list[dict[str, Any]] = []
    missing_workers: list[str] = []
    missing_artifacts: list[str] = []
    failed_workers: list[str] = []

    for worker_spec in workers:
        if not isinstance(worker_spec, dict):
            continue
        worker = str(worker_spec.get("worker") or "")
        artifact = str(worker_spec.get("artifact") or "")
        if not worker:
            continue

        latest = _latest_entry_for_worker(entries, worker)
        if latest is None:
            missing_workers.append(worker)
            checks.append({"worker": worker, "status": "MISSING_LEDGER_ENTRY"})
            continue

        result = str(latest.get("result") or "")
        failure_type = str(latest.get("failure_type") or "")

        worker_check: dict[str, Any] = {
            "worker": worker,
            "result": result,
            "failure_type": failure_type,
        }

        if result in RESULT_SUCCESS:
            artifact_path = (repo_root / artifact).resolve() if artifact else None
            artifact_ok = bool(artifact_path and artifact_path.exists())
            worker_check["artifact_expected"] = artifact
            worker_check["artifact_exists"] = artifact_ok
            if not artifact_ok:
                missing_artifacts.append(worker)
            checks.append(worker_check)
            continue

        if result in RESULT_FAILED or failure_type in FAILURE_TYPES_CANCEL:
            failed_workers.append(worker)
            checks.append(worker_check)
            continue

        # Unknown/unfinished state
        failed_workers.append(worker)
        worker_check["status"] = "UNRESOLVED"
        checks.append(worker_check)

    if missing_workers:
        status = "BLOCKED"
        reason = "ledger_missing_workers"
        exit_code = 2
    elif missing_artifacts or failed_workers:
        status = "STALL"
        reason = "workers_failed_or_missing_artifacts"
        exit_code = 1
    else:
        status = "OK"
        reason = "all_workers_verified"
        exit_code = 0

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "reason": reason,
        "expected_file": _rel(expected_path, repo_root),
        "ledger_file": _rel(ledger_path, repo_root),
        "summary": {
            "expected_workers": len([w for w in workers if isinstance(w, dict)]),
            "missing_workers": missing_workers,
            "failed_workers": failed_workers,
            "missing_artifacts": missing_artifacts,
        },
        "checks": checks,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
