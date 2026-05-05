from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_mutl3y_plan_contract.py"


def _load_validator() -> dict[str, object]:
    return runpy.run_path(str(SCRIPT_PATH))


def _write_yaml(path: Path, payload: object) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _write_minimal_trace(path: Path, *, plan_id: str, cycle: str) -> None:
    _write_yaml(
        path,
        {
            "version": 1,
            "plan_id": plan_id,
            "cycle": cycle,
            "latest_checkpoint": {
                "phase": "P5",
                "status": "OK",
                "next_action": "Wait at barrier.",
                "blocking_issues": [],
                "plan_pointer_synced": True,
            },
            "timeline": [],
        },
    )


def _write_minimal_audit(path: Path, *, phase: str, cycle: str) -> None:
    _write_yaml(
        path,
        {
            "status": "started",
            "phase": phase,
            "cycle": cycle,
            "expected_artifacts": [],
            "present_artifacts": [],
            "missing_artifacts": [],
        },
    )


def _write_minimal_barrier(path: Path, *, phase: str, cycle: str) -> None:
    _write_yaml(
        path,
        {
            "status": "pass",
            "phase": phase,
            "cycle": cycle,
            "present_artifacts": [],
            "missing_artifacts": [],
        },
    )


def _write_minimal_scorecard(path: Path, *, cycle: str) -> None:
    _write_yaml(
        path,
        {
            "cycle": cycle,
            "phase": "P7",
            "models": {},
        },
    )


def _write_minimal_ledger(path: Path, *, cycle: str) -> None:
    _write_yaml(
        path,
        [
            {
                "timestamp": "2026-05-02T00:00:00Z",
                "cycle": cycle,
                "phase": "P5",
                "worker": "Builder-Typing",
                "requested_model": "GPT-5.4 mini",
                "actual_model": "GPT-5.4 mini",
                "result": "success",
                "artifact_path": "docs/plan/example/artifact.md",
                "quality_score": 4,
                "needed_reedit": False,
                "recovery_action": "none",
            }
        ],
    )


def _write_narrow_wave_start_audit(path: Path) -> None:
    _write_yaml(
        path,
        {
            "cycle": "mutl3y-test-1",
            "plan_id": "mutl3y-review-workflow-test",
            "phase": "P5",
            "wave": 1,
            "status": "started",
            "finding_ids": ["FIND-01"],
            "target_path": "src/prism/example.py",
            "implementation_mode": "named_builder_wave",
            "dispatch_decision": "Dispatch builder.",
            "owned_files": ["src/prism/example.py"],
            "expected_workers": ["Builder-Typing"],
            "expected_artifacts": ["docs/plan/example/Builder-Typing-summary.md"],
            "pre_barrier_checks": [".mutl3y-gate/example.log"],
        },
    )


def _write_stall_summary(path: Path) -> None:
    _write_yaml(
        path,
        {
            "cycle": "mutl3y-test-1",
            "plan_id": "mutl3y-review-workflow-test",
            "phase": "P7",
            "status": "stall",
            "reason": "validator failed",
            "next_action": "Repair the artifact and rerun validation.",
            "log": ".mutl3y-gate/example.log",
        },
    )


def _build_plan_payload(
    *,
    plan_id: str,
    cycle: str,
    status: str,
    current_phase: str,
    artifacts: dict[str, str],
) -> dict[str, object]:
    return {
        "plan_id": plan_id,
        "cycle": cycle,
        "status": status,
        "resumption_pointer": {
            "current_phase": current_phase,
            "next_action": "Continue.",
            "blocking_issues": [],
        },
        "artifacts": artifacts,
    }


def test_validate_mutl3y_plan_contract_accepts_live_realrun_plan() -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_path = (
        REPO_ROOT / "docs/plan/mutl3y-review-workflow-realrun-20260502/plan.yaml"
    )
    failures = validate_plan(plan_path)

    assert failures == []


def test_validate_mutl3y_plan_contract_cli_fails_on_missing_artifact(
    tmp_path: Path,
) -> None:
    missing_artifact = tmp_path / "missing-summary.yaml"
    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    plan_path = plan_dir / "plan.yaml"
    plan_path.write_text(
        yaml.safe_dump(
            {
                "plan_id": "mutl3y-review-workflow-test",
                "cycle": "mutl3y-test-1",
                "status": "in_progress",
                "resumption_pointer": {
                    "current_phase": "P5",
                    "next_action": "Wait at barrier",
                    "blocking_issues": [],
                },
                "artifacts": {
                    "barrier_summary": str(missing_artifact),
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(plan_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "missing artifact path for artifacts.barrier_summary" in completed.stderr
    assert "OVERALL FAIL" in completed.stderr


def test_validate_mutl3y_plan_contract_requires_wave_start_audit_with_wave_plan(
    tmp_path: Path,
) -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    trace_path = plan_dir / "execution-trace.yaml"
    wave_plan_path = plan_dir / "wave-1-plan.yaml"
    _write_minimal_trace(
        trace_path, plan_id="mutl3y-review-workflow-test", cycle="mutl3y-test-1"
    )
    _write_yaml(wave_plan_path, {"wave": 1})
    plan_path = plan_dir / "plan.yaml"
    _write_yaml(
        plan_path,
        _build_plan_payload(
            plan_id="mutl3y-review-workflow-test",
            cycle="mutl3y-test-1",
            status="in_progress",
            current_phase="P5",
            artifacts={
                "execution_trace": str(trace_path),
                "wave_plan": str(wave_plan_path),
            },
        ),
    )

    failures = validate_plan(plan_path)

    assert "wave_plan requires artifacts.wave_start_audit" in failures


def test_validate_mutl3y_plan_contract_requires_barrier_summary_after_wave_plan(
    tmp_path: Path,
) -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    trace_path = plan_dir / "execution-trace.yaml"
    wave_start_audit_path = plan_dir / "wave-1-start-audit.yaml"
    wave_plan_path = plan_dir / "wave-1-plan.yaml"
    _write_minimal_trace(
        trace_path, plan_id="mutl3y-review-workflow-test", cycle="mutl3y-test-1"
    )
    _write_minimal_audit(wave_start_audit_path, phase="P5", cycle="mutl3y-test-1")
    _write_yaml(wave_plan_path, {"wave": 1})
    plan_path = plan_dir / "plan.yaml"
    _write_yaml(
        plan_path,
        _build_plan_payload(
            plan_id="mutl3y-review-workflow-test",
            cycle="mutl3y-test-1",
            status="in_progress",
            current_phase="P6",
            artifacts={
                "execution_trace": str(trace_path),
                "wave_start_audit": str(wave_start_audit_path),
                "wave_plan": str(wave_plan_path),
            },
        ),
    )

    failures = validate_plan(plan_path)

    assert (
        "phases P6/P7/CLOSED with wave_plan require a barrier summary artifact"
        in failures
    )


def test_validate_mutl3y_plan_contract_rejects_invalid_trace_shape(
    tmp_path: Path,
) -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    trace_path = plan_dir / "execution-trace.yaml"
    _write_yaml(
        trace_path,
        {
            "version": 1,
            "plan_id": "mutl3y-review-workflow-test",
            "cycle": "mutl3y-test-1",
            "latest_checkpoint": {
                "phase": "P5",
                "status": "OK",
                "next_action": "Wait at barrier.",
                "blocking_issues": [],
            },
            "timeline": [],
        },
    )
    plan_path = plan_dir / "plan.yaml"
    _write_yaml(
        plan_path,
        _build_plan_payload(
            plan_id="mutl3y-review-workflow-test",
            cycle="mutl3y-test-1",
            status="in_progress",
            current_phase="P5",
            artifacts={"execution_trace": str(trace_path)},
        ),
    )

    failures = validate_plan(plan_path)

    assert "missing execution_trace.latest_checkpoint.plan_pointer_synced" in failures


def test_validate_mutl3y_plan_contract_rejects_invalid_ledger_shape(
    tmp_path: Path,
) -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    trace_path = plan_dir / "execution-trace.yaml"
    ledger_path = plan_dir / "model-usage-ledger.yaml"
    scorecard_path = plan_dir / "model-scorecard.yaml"
    _write_minimal_trace(
        trace_path, plan_id="mutl3y-review-workflow-test", cycle="mutl3y-test-1"
    )
    _write_yaml(
        ledger_path,
        [
            {
                "timestamp": "2026-05-02T00:00:00Z",
                "cycle": "mutl3y-test-1",
            }
        ],
    )
    _write_minimal_scorecard(scorecard_path, cycle="mutl3y-test-1")
    plan_path = plan_dir / "plan.yaml"
    _write_yaml(
        plan_path,
        _build_plan_payload(
            plan_id="mutl3y-review-workflow-test",
            cycle="mutl3y-test-1",
            status="in_progress",
            current_phase="P5",
            artifacts={
                "execution_trace": str(trace_path),
                "model_usage_ledger": str(ledger_path),
                "model_scorecard": str(scorecard_path),
            },
        ),
    )

    failures = validate_plan(plan_path)

    assert "missing model_usage_ledger[0].phase" in failures
    assert "missing model_usage_ledger[0].worker" in failures


def test_validate_mutl3y_plan_contract_accepts_completed_plan_with_phase_artifacts(
    tmp_path: Path,
) -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    trace_path = plan_dir / "execution-trace.yaml"
    wave_start_audit_path = plan_dir / "wave-1-start-audit.yaml"
    wave_plan_path = plan_dir / "wave-1-plan.yaml"
    barrier_summary_path = plan_dir / "wave-1-barrier-summary.yaml"
    gatekeeper_path = plan_dir / "Gatekeeper-summary.yaml"
    auditor_path = plan_dir / "Auditor-Regression-summary.yaml"
    closure_path = plan_dir / "closure-summary.yaml"
    ledger_path = plan_dir / "model-usage-ledger.yaml"
    scorecard_path = plan_dir / "model-scorecard.yaml"

    _write_minimal_trace(
        trace_path, plan_id="mutl3y-review-workflow-test", cycle="mutl3y-test-1"
    )
    _write_minimal_audit(wave_start_audit_path, phase="P5", cycle="mutl3y-test-1")
    _write_yaml(wave_plan_path, {"wave": 1})
    _write_minimal_barrier(barrier_summary_path, phase="P5", cycle="mutl3y-test-1")
    _write_yaml(gatekeeper_path, {"status": "pass"})
    _write_yaml(auditor_path, {"status": "pass"})
    _write_yaml(closure_path, {"status": "completed"})
    _write_minimal_ledger(ledger_path, cycle="mutl3y-test-1")
    _write_minimal_scorecard(scorecard_path, cycle="mutl3y-test-1")

    plan_path = plan_dir / "plan.yaml"
    _write_yaml(
        plan_path,
        _build_plan_payload(
            plan_id="mutl3y-review-workflow-test",
            cycle="mutl3y-test-1",
            status="completed",
            current_phase="P7",
            artifacts={
                "execution_trace": str(trace_path),
                "wave_start_audit": str(wave_start_audit_path),
                "wave_plan": str(wave_plan_path),
                "barrier_summary": str(barrier_summary_path),
                "gatekeeper_summary": str(gatekeeper_path),
                "auditor_summary": str(auditor_path),
                "closure_summary": str(closure_path),
                "model_usage_ledger": str(ledger_path),
                "model_scorecard": str(scorecard_path),
            },
        ),
    )

    failures = validate_plan(plan_path)

    assert failures == []


def test_validate_mutl3y_plan_contract_accepts_narrow_live_wave_start_audit(
    tmp_path: Path,
) -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    trace_path = plan_dir / "execution-trace.yaml"
    wave_start_audit_path = plan_dir / "wave-1-start-audit.yaml"
    wave_plan_path = plan_dir / "wave-1-plan.yaml"
    _write_minimal_trace(
        trace_path, plan_id="mutl3y-review-workflow-test", cycle="mutl3y-test-1"
    )
    _write_narrow_wave_start_audit(wave_start_audit_path)
    _write_yaml(wave_plan_path, {"wave": 1})

    plan_path = plan_dir / "plan.yaml"
    _write_yaml(
        plan_path,
        _build_plan_payload(
            plan_id="mutl3y-review-workflow-test",
            cycle="mutl3y-test-1",
            status="in_progress",
            current_phase="P5",
            artifacts={
                "execution_trace": str(trace_path),
                "wave_start_audit": str(wave_start_audit_path),
                "wave_plan": str(wave_plan_path),
            },
        ),
    )

    failures = validate_plan(plan_path)

    assert failures == []


def test_validate_mutl3y_plan_contract_accepts_stall_summary_shape(
    tmp_path: Path,
) -> None:
    validator = _load_validator()
    validate_plan = validator["validate_plan"]
    assert callable(validate_plan)

    plan_dir = tmp_path / "mutl3y-review-workflow-test"
    plan_dir.mkdir()
    trace_path = plan_dir / "execution-trace.yaml"
    stall_summary_path = plan_dir / "stall-summary.yaml"
    _write_minimal_trace(
        trace_path, plan_id="mutl3y-review-workflow-test", cycle="mutl3y-test-1"
    )
    _write_stall_summary(stall_summary_path)

    plan_path = plan_dir / "plan.yaml"
    _write_yaml(
        plan_path,
        _build_plan_payload(
            plan_id="mutl3y-review-workflow-test",
            cycle="mutl3y-test-1",
            status="completed",
            current_phase="CLOSED",
            artifacts={
                "execution_trace": str(trace_path),
                "stall_summary": str(stall_summary_path),
            },
        ),
    )

    failures = validate_plan(plan_path)

    assert failures == []
