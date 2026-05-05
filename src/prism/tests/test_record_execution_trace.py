from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "record_execution_trace.py"


def _load_script() -> dict[str, object]:
    return runpy.run_path(str(SCRIPT_PATH))


def _read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_record_execution_trace_creates_new_trace_checkpoint(tmp_path: Path) -> None:
    script = _load_script()
    assert callable(script["main"])

    plan_dir = tmp_path / "mutl3y-plan"
    plan_dir.mkdir()

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--plan-dir",
            str(plan_dir),
            "--plan-id",
            "mutl3y-plan",
            "--cycle",
            "mutl3y-test-1",
            "--phase",
            "P5",
            "--wave",
            "1",
            "--status",
            "OK",
            "--status-line",
            "[mutl3y-test-1 | P5 wave 1 barrier | OK — builder complete]",
            "--next-action",
            "Run Gatekeeper.",
            "--event",
            "wave_barrier",
            "--summary",
            "Wave barrier cleared.",
            "--source-summary-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--plan-pointer-synced",
            "true",
            "--receipt-proof",
            "Builder returned in this turn",
            "--artifact-proof",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--source-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    trace_path = plan_dir / "mutl3y-artifacts" / "execution-trace.yaml"
    payload = _read_yaml(trace_path)

    assert isinstance(payload, dict)
    assert payload["plan_id"] == "mutl3y-plan"
    assert payload["cycle"] == "mutl3y-test-1"
    latest_checkpoint = payload["latest_checkpoint"]
    assert latest_checkpoint["phase"] == "P5"
    assert latest_checkpoint["wave"] == 1
    assert latest_checkpoint["status"] == "OK"
    assert latest_checkpoint["failure_debug"] is None
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert len(timeline) == 1
    assert timeline[0]["event"] == "wave_barrier"


def test_record_execution_trace_records_recovery_attempts_in_failure_debug(
    tmp_path: Path,
) -> None:
    plan_dir = tmp_path / "mutl3y-plan"
    plan_dir.mkdir()

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--plan-dir",
            str(plan_dir),
            "--plan-id",
            "mutl3y-plan",
            "--cycle",
            "mutl3y-test-1",
            "--phase",
            "P5",
            "--wave",
            "1",
            "--status",
            "STALL",
            "--status-line",
            "[mutl3y-test-1 | P5 wave 1 barrier | STALL — missing artifact]",
            "--next-action",
            "Re-dispatch Builder-Typing.",
            "--event",
            "wave_barrier",
            "--summary",
            "Barrier stalled on missing summary artifact.",
            "--source-summary-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--plan-pointer-synced",
            "false",
            "--source-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--failure-class",
            "missing_artifact",
            "--failing-worker",
            "Builder-Typing",
            "--expected-worker",
            "Builder-Typing",
            "--missing-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/Builder-Typing-summary.md",
            "--relevant-log",
            ".mutl3y-gate/example.log",
            "--recovery-attempt",
            "checked owned file set",
            "--recovery-attempt",
            "re-dispatched on next healthy model",
            "--last-successful-status-line",
            "[mutl3y-test-1 | P5 start | OK — audit written]",
            "--suspected-slice",
            "Phase 5 wave-1 barrier",
            "--debug-hypothesis",
            "Builder returned without writing the summary artifact.",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    trace_path = plan_dir / "mutl3y-artifacts" / "execution-trace.yaml"
    payload = _read_yaml(trace_path)

    assert isinstance(payload, dict)
    latest_checkpoint = payload["latest_checkpoint"]
    failure_debug = latest_checkpoint["failure_debug"]
    assert isinstance(failure_debug, dict)
    assert failure_debug["failure_class"] == "missing_artifact"
    assert failure_debug["recovery_attempted"] == [
        "checked owned file set",
        "re-dispatched on next healthy model",
    ]
    assert failure_debug["missing_artifacts"] == [
        "docs/plan/example/mutl3y-artifacts/phase5/Builder-Typing-summary.md"
    ]
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1]["failure_debug"] == failure_debug


def test_record_execution_trace_writes_validation_log_for_valid_plan(
    tmp_path: Path,
) -> None:
    plan_dir = tmp_path / "mutl3y-plan"
    plan_dir.mkdir()
    trace_path = plan_dir / "mutl3y-artifacts" / "execution-trace.yaml"
    plan_path = plan_dir / "plan.yaml"
    validate_log = plan_dir / ".mutl3y-gate" / "trace-write.log"
    _write_yaml(
        plan_path,
        {
            "plan_id": "mutl3y-plan",
            "cycle": "mutl3y-test-1",
            "status": "in_progress",
            "resumption_pointer": {
                "current_phase": "P5",
                "next_action": "Wait at barrier.",
                "blocking_issues": [],
            },
            "artifacts": {
                "execution_trace": str(trace_path),
            },
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--plan-dir",
            str(plan_dir),
            "--plan-id",
            "mutl3y-plan",
            "--cycle",
            "mutl3y-test-1",
            "--phase",
            "P5",
            "--wave",
            "1",
            "--status",
            "OK",
            "--status-line",
            "[mutl3y-test-1 | P5 wave 1 barrier | OK — builder complete]",
            "--next-action",
            "Run Gatekeeper.",
            "--event",
            "wave_barrier",
            "--summary",
            "Wave barrier cleared.",
            "--source-summary-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--plan-pointer-synced",
            "true",
            "--source-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--validate-log",
            str(validate_log),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    log_output = validate_log.read_text(encoding="utf-8")
    assert f"PASS {trace_path.as_posix()}" in log_output
    assert f"PASS {plan_path.as_posix()}" in log_output
    assert "OVERALL PASS" in log_output


def test_record_execution_trace_validation_log_fails_for_invalid_plan(
    tmp_path: Path,
) -> None:
    plan_dir = tmp_path / "mutl3y-plan"
    plan_dir.mkdir()
    plan_path = plan_dir / "plan.yaml"
    validate_log = plan_dir / ".mutl3y-gate" / "trace-write.log"
    _write_yaml(
        plan_path,
        {
            "plan_id": "mutl3y-plan",
            "cycle": "mutl3y-test-1",
            "status": "in_progress",
            "resumption_pointer": {
                "current_phase": "P5",
                "next_action": "Wait at barrier.",
                "blocking_issues": [],
            },
            "artifacts": {
                "execution_trace": str(
                    plan_dir / "mutl3y-artifacts" / "execution-trace.yaml"
                ),
                "wave_plan": str(
                    plan_dir / "mutl3y-artifacts" / "phase5" / "wave-1-plan.yaml"
                ),
            },
        },
    )
    _write_yaml(
        plan_dir / "mutl3y-artifacts" / "phase5" / "wave-1-plan.yaml", {"wave": 1}
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--plan-dir",
            str(plan_dir),
            "--plan-id",
            "mutl3y-plan",
            "--cycle",
            "mutl3y-test-1",
            "--phase",
            "P5",
            "--wave",
            "1",
            "--status",
            "OK",
            "--status-line",
            "[mutl3y-test-1 | P5 wave 1 barrier | OK — builder complete]",
            "--next-action",
            "Run Gatekeeper.",
            "--event",
            "wave_barrier",
            "--summary",
            "Wave barrier cleared.",
            "--source-summary-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--plan-pointer-synced",
            "true",
            "--source-artifact",
            "docs/plan/example/mutl3y-artifacts/phase5/wave-1-barrier-summary.yaml",
            "--validate-log",
            str(validate_log),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    log_output = validate_log.read_text(encoding="utf-8")
    assert "wave_plan requires artifacts.wave_start_audit" in log_output
    assert "OVERALL FAIL" in log_output
