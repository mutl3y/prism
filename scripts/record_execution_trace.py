#!/usr/bin/env python3
"""Deterministically record execution-trace checkpoints for Mutl3y workflow runs."""

from __future__ import annotations

import argparse
import runpy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


OUTPUT_DIR_NAME = "mutl3y-artifacts"
LEGACY_OUTPUT_DIR_NAME = "artifacts"


def _output_dir(plan_dir: Path) -> Path:
    preferred = plan_dir / OUTPUT_DIR_NAME
    if preferred.exists():
        return preferred
    legacy = plan_dir / LEGACY_OUTPUT_DIR_NAME
    if legacy.exists():
        return legacy
    return preferred


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_arg(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value!r}")


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False, width=100),
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append one execution-trace checkpoint and update latest_checkpoint.",
    )
    parser.add_argument("--plan-dir", required=True)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--cycle", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--status-line", required=True)
    parser.add_argument("--next-action", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--source-summary-artifact", required=True)
    parser.add_argument("--plan-pointer-synced", required=True, type=_bool_arg)
    parser.add_argument("--wave", type=int, default=None)
    parser.add_argument("--updated-at", default=None)
    parser.add_argument("--timestamp", default=None)
    parser.add_argument("--authoritative-resume-anchor", default=None)
    parser.add_argument("--blocking-issue", action="append", default=[])
    parser.add_argument("--receipt-proof", action="append", default=[])
    parser.add_argument("--artifact-proof", action="append", default=[])
    parser.add_argument("--source-artifact", action="append", default=[])
    parser.add_argument("--failure-class", default=None)
    parser.add_argument("--failing-worker", action="append", default=[])
    parser.add_argument("--expected-worker", action="append", default=[])
    parser.add_argument("--returned-worker", action="append", default=[])
    parser.add_argument("--missing-artifact", action="append", default=[])
    parser.add_argument("--relevant-log", action="append", default=[])
    parser.add_argument("--route-failure", action="append", default=[])
    parser.add_argument("--last-successful-status-line", default=None)
    parser.add_argument("--suspected-slice", default=None)
    parser.add_argument("--recovery-attempt", action="append", default=[])
    parser.add_argument("--debug-hypothesis", default=None)
    parser.add_argument("--validate-log", default=None)
    return parser.parse_args()


def _load_trace(
    trace_path: Path,
    *,
    plan_id: str,
    cycle: str,
    authoritative_resume_anchor: str,
) -> dict[str, Any]:
    if not trace_path.exists():
        return {
            "version": 1,
            "plan_id": plan_id,
            "cycle": cycle,
            "updated_at": _utc_now(),
            "authoritative_resume_anchor": authoritative_resume_anchor,
            "latest_checkpoint": {},
            "timeline": [],
        }
    loaded = _read_yaml(trace_path)
    if not isinstance(loaded, dict):
        raise SystemExit(f"Expected mapping-shaped trace at {trace_path.as_posix()}")
    loaded.setdefault("version", 1)
    loaded["plan_id"] = plan_id
    loaded["cycle"] = cycle
    loaded["authoritative_resume_anchor"] = authoritative_resume_anchor
    if not isinstance(loaded.get("timeline"), list):
        loaded["timeline"] = []
    return loaded


def _failure_debug(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.failure_class is None:
        return None
    failure_debug = {
        "failure_class": args.failure_class,
        "failing_workers": args.failing_worker,
        "expected_workers": args.expected_worker,
        "returned_workers": args.returned_worker,
        "missing_artifacts": args.missing_artifact,
        "relevant_logs": args.relevant_log,
        "route_failures": args.route_failure,
        "recovery_attempted": args.recovery_attempt,
    }
    if args.last_successful_status_line is not None:
        failure_debug["last_successful_status_line"] = args.last_successful_status_line
    if args.suspected_slice is not None:
        failure_debug["suspected_slice"] = args.suspected_slice
    if args.debug_hypothesis is not None:
        failure_debug["debug_hypothesis"] = args.debug_hypothesis
    return failure_debug


def _latest_checkpoint(
    args: argparse.Namespace,
    *,
    failure_debug: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "phase": args.phase,
        "wave": args.wave,
        "status": args.status,
        "status_line": args.status_line,
        "next_action": args.next_action,
        "blocking_issues": args.blocking_issue,
        "plan_pointer_synced": args.plan_pointer_synced,
        "receipt_proof": args.receipt_proof,
        "artifact_proof": args.artifact_proof,
        "source_summary_artifact": args.source_summary_artifact,
        "failure_debug": failure_debug,
    }


def _timeline_entry(
    args: argparse.Namespace,
    *,
    failure_debug: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "timestamp": args.timestamp or _utc_now(),
        "phase": args.phase,
        "wave": args.wave,
        "status": args.status,
        "event": args.event,
        "summary": args.summary,
        "source_artifacts": args.source_artifact,
        "plan_pointer_synced": args.plan_pointer_synced,
        "failure_debug": failure_debug,
    }


def _load_plan_validator() -> Any:
    validator_path = (
        Path(__file__).resolve().parent / "validate_mutl3y_plan_contract.py"
    )
    validator_globals = runpy.run_path(str(validator_path))
    validate_plan = validator_globals.get("validate_plan")
    if not callable(validate_plan):
        raise SystemExit(
            "validate_mutl3y_plan_contract.py did not expose validate_plan"
        )
    return validate_plan


def _validate_and_log(trace_path: Path, plan_path: Path, log_path: Path) -> int:
    lines: list[str] = []
    failures: list[str] = []

    try:
        yaml.safe_load(trace_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"FAIL {trace_path.as_posix()}: missing file")
    except yaml.YAMLError as exc:
        failures.append(f"FAIL {trace_path.as_posix()}: {exc}")
    else:
        lines.append(f"PASS {trace_path.as_posix()}")

    if plan_path.exists():
        validate_plan = _load_plan_validator()
        plan_failures = validate_plan(plan_path)
        if plan_failures:
            failures.append(f"FAIL {plan_path.as_posix()}")
            failures.extend(f"  - {failure}" for failure in plan_failures)
        else:
            lines.append(f"PASS {plan_path.as_posix()}")
    else:
        lines.append(f"SKIP {plan_path.as_posix()}: missing file")

    if failures:
        lines.extend(failures)
        lines.append("OVERALL FAIL")
    else:
        lines.append("OVERALL PASS")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failures else 0


def main() -> int:
    args = _parse_args()
    plan_dir = Path(args.plan_dir)
    output_dir = _output_dir(plan_dir)
    trace_path = output_dir / "execution-trace.yaml"
    authoritative_resume_anchor = (
        args.authoritative_resume_anchor or (plan_dir / "plan.yaml").as_posix()
    )
    trace = _load_trace(
        trace_path,
        plan_id=args.plan_id,
        cycle=args.cycle,
        authoritative_resume_anchor=authoritative_resume_anchor,
    )

    failure_debug = _failure_debug(args)
    trace["updated_at"] = args.updated_at or _utc_now()
    trace["latest_checkpoint"] = _latest_checkpoint(args, failure_debug=failure_debug)
    timeline = trace.setdefault("timeline", [])
    if not isinstance(timeline, list):
        raise SystemExit("Expected list-shaped timeline in execution trace")
    timeline.append(_timeline_entry(args, failure_debug=failure_debug))
    _write_yaml(trace_path, trace)
    if args.validate_log is not None:
        return _validate_and_log(
            trace_path,
            plan_dir / "plan.yaml",
            Path(args.validate_log),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
