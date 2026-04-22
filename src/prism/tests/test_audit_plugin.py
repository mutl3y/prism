"""Tests for the Policy-as-Code audit plugin (T1-01 Wave 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prism.scanner_config.audit_rules import AuditReport, AuditRule, AuditViolation
from prism.scanner_plugins.audit.loader import (
    AuditRuleLoadError,
    load_audit_rules_from_file,
)
from prism.scanner_plugins.audit.runner import BuiltinAuditPlugin, run_audit


# ---------- loader ----------------------------------------------------------


def test_loader_reads_yaml_policy_rules(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yml"
    rules_file.write_text(
        "policy_rules:\n"
        "  - id: r1\n"
        "    description: 'first'\n"
        "  - id: r2\n"
        "    description: 'second'\n"
        "    severity: warning\n"
        "    enabled: false\n"
        "    params:\n"
        "      threshold: 0.9\n",
        encoding="utf-8",
    )
    rules = load_audit_rules_from_file(rules_file)
    assert [r.id for r in rules] == ["r1", "r2"]
    assert rules[0].severity == "error"
    assert rules[0].enabled is True
    assert rules[1].severity == "warning"
    assert rules[1].enabled is False
    assert rules[1].params == {"threshold": 0.9}


def test_loader_reads_json(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(
        json.dumps({"audit_rules": [{"id": "r1", "description": "x"}]}),
        encoding="utf-8",
    )
    rules = load_audit_rules_from_file(rules_file)
    assert len(rules) == 1 and rules[0].id == "r1"


def test_loader_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AuditRuleLoadError, match="not found"):
        load_audit_rules_from_file(tmp_path / "does-not-exist.yml")


def test_loader_no_rules_section_returns_empty(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yml"
    rules_file.write_text("other_key: 1\n", encoding="utf-8")
    assert load_audit_rules_from_file(rules_file) == []


def test_loader_rejects_invalid_severity(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yml"
    rules_file.write_text(
        "policy_rules:\n  - id: r1\n    severity: catastrophic\n",
        encoding="utf-8",
    )
    with pytest.raises(AuditRuleLoadError, match="invalid severity"):
        load_audit_rules_from_file(rules_file)


def test_loader_rejects_missing_id(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yml"
    rules_file.write_text("policy_rules:\n  - description: x\n", encoding="utf-8")
    with pytest.raises(AuditRuleLoadError, match="missing required string field 'id'"):
        load_audit_rules_from_file(rules_file)


# ---------- runner ----------------------------------------------------------


class _AlwaysFailRule:
    RULE_ID = "always-fail"

    def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]:
        return [
            AuditViolation(
                rule_id=rule.id,
                severity=rule.severity,
                message="boom",
                role_path=scan_payload.get("role_path", ""),
            )
        ]


class _ParamAwareRule:
    RULE_ID = "param-aware"

    def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]:
        return [
            AuditViolation(
                rule_id=rule.id,
                severity="warning",
                message=f"param={rule.params.get('value')}",
                role_path="",
            )
        ]


def _plugin_with(*evaluators: object) -> BuiltinAuditPlugin:
    return BuiltinAuditPlugin(
        rule_registry={ev.RULE_ID: ev for ev in evaluators}  # type: ignore[attr-defined]
    )


def test_runner_dispatches_to_registered_evaluator() -> None:
    plugin = _plugin_with(_AlwaysFailRule())
    rules = [AuditRule(id="always-fail", description="x", severity="error")]
    report = run_audit({"role_path": "/r"}, rules, plugin=plugin)
    assert report.passed is False
    assert len(report.violations) == 1
    assert report.violations[0].role_path == "/r"


def test_runner_passes_params_to_rule() -> None:
    plugin = _plugin_with(_ParamAwareRule())
    rules = [
        AuditRule(
            id="param-aware",
            description="x",
            severity="warning",
            params={"value": 42},
        )
    ]
    report = run_audit({}, rules, plugin=plugin)
    assert "param=42" in report.violations[0].message


def test_runner_skips_disabled_rules() -> None:
    plugin = _plugin_with(_AlwaysFailRule())
    rules = [
        AuditRule(id="always-fail", description="x", severity="error", enabled=False)
    ]
    report = run_audit({}, rules, plugin=plugin)
    assert report.violations == []
    assert report.passed is True


def test_runner_warns_on_unknown_rule_id() -> None:
    plugin = _plugin_with()
    rules = [AuditRule(id="nope", description="x")]
    report = run_audit({}, rules, plugin=plugin)
    assert len(report.violations) == 1
    assert report.violations[0].severity == "warning"
    assert "No evaluator registered" in report.violations[0].message
    assert report.passed is True


def test_runner_reports_notimplemented_as_warning() -> None:
    class _Stub:
        RULE_ID = "stub"

        def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]:
            raise NotImplementedError("not done")

    plugin = _plugin_with(_Stub())
    rules = [AuditRule(id="stub", description="x")]
    report = run_audit({}, rules, plugin=plugin)
    assert report.passed is True
    assert "not yet implemented" in report.violations[0].message


def test_audit_report_summary_default() -> None:
    report = AuditReport(
        violations=[
            AuditViolation(rule_id="r", severity="error", message="m", role_path=""),
            AuditViolation(rule_id="r", severity="warning", message="m", role_path=""),
        ]
    )
    assert "1 error" in report.summary and "1 warning" in report.summary
    assert report.passed is False
