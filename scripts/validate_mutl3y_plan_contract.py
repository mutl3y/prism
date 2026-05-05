#!/usr/bin/env python3
"""Validate Mutl3y workflow plan.yaml files against the repo-local contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_PLAN_KEYS = (
    "plan_id",
    "cycle",
    "status",
    "resumption_pointer",
    "artifacts",
)
REQUIRED_RESUMPTION_KEYS = (
    "current_phase",
    "next_action",
    "blocking_issues",
)
REQUIRED_TRACE_KEYS = (
    "version",
    "plan_id",
    "cycle",
    "latest_checkpoint",
    "timeline",
)
REQUIRED_TRACE_CHECKPOINT_KEYS = (
    "phase",
    "status",
    "next_action",
    "blocking_issues",
    "plan_pointer_synced",
)
REQUIRED_AUDIT_KEYS = (
    "status",
    "phase",
    "cycle",
    "expected_artifacts",
    "present_artifacts",
    "missing_artifacts",
)
REQUIRED_BARRIER_KEYS = (
    "status",
    "phase",
    "cycle",
    "present_artifacts",
    "missing_artifacts",
)
REQUIRED_WAVE_START_AUDIT_KEYS = (
    "status",
    "phase",
    "expected_artifacts",
)
REQUIRED_STALL_SUMMARY_KEYS = (
    "status",
    "phase",
    "reason",
    "next_action",
)
REQUIRED_SCORECARD_KEYS = (
    "cycle",
    "phase",
    "models",
)
REQUIRED_LEDGER_ENTRY_KEYS = (
    "timestamp",
    "cycle",
    "phase",
    "worker",
    "requested_model",
    "actual_model",
    "result",
    "artifact_path",
    "quality_score",
    "needed_reedit",
    "recovery_action",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        help="Mutl3y plan.yaml paths or plan directories.",
    )
    return parser.parse_args()


def _resolve_plan_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_dir():
        return path / "plan.yaml"
    return path


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing file"
    except yaml.YAMLError as exc:
        return None, str(exc)
    if not isinstance(loaded, dict):
        return None, "expected top-level YAML mapping"
    return loaded, None


def _validate_required_keys(
    payload: dict[str, Any],
    *,
    required_keys: tuple[str, ...],
    label: str,
    failures: list[str],
) -> None:
    for key in required_keys:
        if key not in payload:
            failures.append(f"missing {label}.{key}")


def _validate_string_field(
    payload: dict[str, Any],
    *,
    key: str,
    label: str,
    failures: list[str],
) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        failures.append(f"expected non-empty string for {label}.{key}")


def _validate_artifacts(
    plan_path: Path,
    artifacts: dict[str, Any],
    failures: list[str],
) -> None:
    if not artifacts:
        failures.append("artifacts mapping is empty")
        return
    for key, value in artifacts.items():
        if not isinstance(value, str) or not value.strip():
            failures.append(f"expected non-empty string for artifacts.{key}")
            continue
        artifact_path = Path(value)
        if not artifact_path.is_absolute():
            artifact_path = REPO_ROOT / artifact_path
        if not artifact_path.exists():
            failures.append(f"missing artifact path for artifacts.{key}: {value}")
            continue
        if plan_path.name == "plan.yaml" and artifact_path == plan_path:
            failures.append("artifacts mapping must not reference plan.yaml itself")


def _validate_list_field(
    payload: dict[str, Any],
    *,
    key: str,
    label: str,
    failures: list[str],
) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        failures.append(f"expected list for {label}.{key}")


def _validate_bool_field(
    payload: dict[str, Any],
    *,
    key: str,
    label: str,
    failures: list[str],
) -> None:
    value = payload.get(key)
    if not isinstance(value, bool):
        failures.append(f"expected bool for {label}.{key}")


def _load_artifact_yaml(path: Path) -> tuple[Any | None, str | None]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except yaml.YAMLError as exc:
        return None, str(exc)


def _validate_trace_artifact(path: Path, failures: list[str]) -> None:
    payload, error = _load_artifact_yaml(path)
    if error is not None:
        failures.append(f"invalid execution_trace YAML: {error}")
        return
    if not isinstance(payload, dict):
        failures.append("expected mapping for execution_trace")
        return
    _validate_required_keys(
        payload,
        required_keys=REQUIRED_TRACE_KEYS,
        label="execution_trace",
        failures=failures,
    )
    latest_checkpoint = payload.get("latest_checkpoint")
    if not isinstance(latest_checkpoint, dict):
        failures.append("expected mapping for execution_trace.latest_checkpoint")
        return
    _validate_required_keys(
        latest_checkpoint,
        required_keys=REQUIRED_TRACE_CHECKPOINT_KEYS,
        label="execution_trace.latest_checkpoint",
        failures=failures,
    )
    _validate_list_field(
        latest_checkpoint,
        key="blocking_issues",
        label="execution_trace.latest_checkpoint",
        failures=failures,
    )
    _validate_bool_field(
        latest_checkpoint,
        key="plan_pointer_synced",
        label="execution_trace.latest_checkpoint",
        failures=failures,
    )
    _validate_list_field(
        payload,
        key="timeline",
        label="execution_trace",
        failures=failures,
    )


def _validate_audit_artifact(path: Path, label: str, failures: list[str]) -> None:
    payload, error = _load_artifact_yaml(path)
    if error is not None:
        failures.append(f"invalid {label} YAML: {error}")
        return
    if not isinstance(payload, dict):
        failures.append(f"expected mapping for {label}")
        return
    _validate_required_keys(
        payload,
        required_keys=REQUIRED_AUDIT_KEYS,
        label=label,
        failures=failures,
    )
    _validate_list_field(
        payload, key="expected_artifacts", label=label, failures=failures
    )
    _validate_list_field(
        payload, key="present_artifacts", label=label, failures=failures
    )
    _validate_list_field(
        payload, key="missing_artifacts", label=label, failures=failures
    )


def _validate_barrier_artifact(path: Path, label: str, failures: list[str]) -> None:
    payload, error = _load_artifact_yaml(path)
    if error is not None:
        failures.append(f"invalid {label} YAML: {error}")
        return
    if not isinstance(payload, dict):
        failures.append(f"expected mapping for {label}")
        return
    _validate_required_keys(
        payload,
        required_keys=REQUIRED_BARRIER_KEYS,
        label=label,
        failures=failures,
    )
    _validate_list_field(
        payload, key="present_artifacts", label=label, failures=failures
    )
    _validate_list_field(
        payload, key="missing_artifacts", label=label, failures=failures
    )


def _validate_wave_start_audit_artifact(
    path: Path,
    label: str,
    failures: list[str],
) -> None:
    payload, error = _load_artifact_yaml(path)
    if error is not None:
        failures.append(f"invalid {label} YAML: {error}")
        return
    if not isinstance(payload, dict):
        failures.append(f"expected mapping for {label}")
        return
    _validate_required_keys(
        payload,
        required_keys=REQUIRED_WAVE_START_AUDIT_KEYS,
        label=label,
        failures=failures,
    )
    _validate_list_field(
        payload, key="expected_artifacts", label=label, failures=failures
    )


def _validate_stall_summary_artifact(
    path: Path,
    label: str,
    failures: list[str],
) -> None:
    payload, error = _load_artifact_yaml(path)
    if error is not None:
        failures.append(f"invalid {label} YAML: {error}")
        return
    if not isinstance(payload, dict):
        failures.append(f"expected mapping for {label}")
        return
    _validate_required_keys(
        payload,
        required_keys=REQUIRED_STALL_SUMMARY_KEYS,
        label=label,
        failures=failures,
    )


def _validate_scorecard_artifact(path: Path, failures: list[str]) -> None:
    payload, error = _load_artifact_yaml(path)
    if error is not None:
        failures.append(f"invalid model_scorecard YAML: {error}")
        return
    if not isinstance(payload, dict):
        failures.append("expected mapping for model_scorecard")
        return
    _validate_required_keys(
        payload,
        required_keys=REQUIRED_SCORECARD_KEYS,
        label="model_scorecard",
        failures=failures,
    )
    models = payload.get("models")
    if not isinstance(models, dict):
        failures.append("expected mapping for model_scorecard.models")


def _validate_ledger_artifact(path: Path, failures: list[str]) -> None:
    payload, error = _load_artifact_yaml(path)
    if error is not None:
        failures.append(f"invalid model_usage_ledger YAML: {error}")
        return
    if not isinstance(payload, list):
        failures.append("expected list for model_usage_ledger")
        return
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            failures.append(f"expected mapping for model_usage_ledger[{index}]")
            continue
        _validate_required_keys(
            entry,
            required_keys=REQUIRED_LEDGER_ENTRY_KEYS,
            label=f"model_usage_ledger[{index}]",
            failures=failures,
        )


def _validate_artifact_shapes(artifacts: dict[str, Any], failures: list[str]) -> None:
    for key, value in artifacts.items():
        if not isinstance(value, str) or not value.strip():
            continue
        artifact_path = Path(value)
        if not artifact_path.is_absolute():
            artifact_path = REPO_ROOT / artifact_path
        if not artifact_path.exists():
            continue
        if key == "execution_trace":
            _validate_trace_artifact(artifact_path, failures)
        elif key == "phase0_start_audit":
            _validate_audit_artifact(artifact_path, key, failures)
        elif key in {"phase5_wave_start_audit", "wave_start_audit"}:
            _validate_wave_start_audit_artifact(artifact_path, key, failures)
        elif key in {"barrier_summary", "phase5_barrier_summary"}:
            _validate_barrier_artifact(artifact_path, key, failures)
        elif key == "stall_summary":
            _validate_stall_summary_artifact(artifact_path, key, failures)
        elif key == "model_scorecard":
            _validate_scorecard_artifact(artifact_path, failures)
        elif key == "model_usage_ledger":
            _validate_ledger_artifact(artifact_path, failures)


def _validate_phase_artifact_dependencies(
    payload: dict[str, Any],
    artifacts: dict[str, Any],
    failures: list[str],
) -> None:
    current_phase = payload.get("resumption_pointer", {}).get("current_phase")
    status = payload.get("status")
    artifact_keys = set(artifacts)

    if "execution_trace" not in artifact_keys:
        failures.append("missing artifacts.execution_trace")

    if "wave_plan" in artifact_keys and "wave_start_audit" not in artifact_keys:
        failures.append("wave_plan requires artifacts.wave_start_audit")

    if (
        current_phase in {"P6", "P7", "CLOSED"}
        and "wave_plan" in artifact_keys
        and not (
            {"barrier_summary", "phase5_barrier_summary", "stall_summary"}
            & artifact_keys
        )
    ):
        failures.append(
            "phases P6/P7/CLOSED with wave_plan require a barrier summary artifact"
        )

    if (
        status == "completed"
        and ({"gatekeeper_summary", "auditor_summary"} & artifact_keys)
        and "closure_summary" not in artifact_keys
        and "recovery_summary" not in artifact_keys
    ):
        failures.append(
            "completed plans with gatekeeper/auditor summaries require closure_summary or recovery_summary"
        )


def validate_plan(path: Path) -> list[str]:
    payload, error = _load_yaml(path)
    if error is not None or payload is None:
        return [error or "unknown YAML load failure"]

    failures: list[str] = []
    _validate_required_keys(
        payload,
        required_keys=REQUIRED_PLAN_KEYS,
        label="plan",
        failures=failures,
    )
    _validate_string_field(payload, key="plan_id", label="plan", failures=failures)
    _validate_string_field(payload, key="cycle", label="plan", failures=failures)
    _validate_string_field(payload, key="status", label="plan", failures=failures)

    resumption_pointer = payload.get("resumption_pointer")
    if not isinstance(resumption_pointer, dict):
        failures.append("expected mapping for plan.resumption_pointer")
    else:
        _validate_required_keys(
            resumption_pointer,
            required_keys=REQUIRED_RESUMPTION_KEYS,
            label="resumption_pointer",
            failures=failures,
        )
        _validate_string_field(
            resumption_pointer,
            key="current_phase",
            label="resumption_pointer",
            failures=failures,
        )
        _validate_string_field(
            resumption_pointer,
            key="next_action",
            label="resumption_pointer",
            failures=failures,
        )
        if not isinstance(resumption_pointer.get("blocking_issues"), list):
            failures.append("expected list for resumption_pointer.blocking_issues")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        failures.append("expected mapping for plan.artifacts")
    else:
        _validate_artifacts(path, artifacts, failures)
        _validate_phase_artifact_dependencies(payload, artifacts, failures)
        _validate_artifact_shapes(artifacts, failures)

    return failures


def main() -> int:
    args = _parse_args()
    had_failures = False
    for raw_path in args.paths:
        plan_path = _resolve_plan_path(raw_path)
        failures = validate_plan(plan_path)
        display_path = plan_path.as_posix()
        if failures:
            had_failures = True
            print(f"FAIL {display_path}", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            continue
        print(f"PASS {display_path}")
    if had_failures:
        print("OVERALL FAIL", file=sys.stderr)
        return 1
    print("OVERALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
