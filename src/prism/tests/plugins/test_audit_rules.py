"""Unit tests for prism.scanner_config.audit_rules (FIND-13 closure)."""

from __future__ import annotations

from prism.scanner_config.audit_rules import (
    AuditReport,
    AuditRule,
    AuditViolation,
    load_audit_rules_from_policy,
)


def test_audit_rule_defaults() -> None:
    rule = AuditRule(id="R1", description="d")
    assert rule.id == "R1"
    assert rule.description == "d"
    assert rule.severity == "error"
    assert rule.enabled is True
    assert rule.params == {}


def test_audit_rule_custom_params() -> None:
    rule = AuditRule(
        id="R2", description="d", severity="warning", enabled=False, params={"k": 1}
    )
    assert rule.severity == "warning"
    assert rule.enabled is False
    assert rule.params == {"k": 1}


def test_audit_violation_defaults_evidence_to_empty() -> None:
    v = AuditViolation(rule_id="R", severity="error", message="m", role_path="/p")
    assert v.evidence == []


def test_audit_report_passed_when_no_errors() -> None:
    report = AuditReport(violations=[])
    assert report.passed is True
    assert "All policy checks passed." in report.summary


def test_audit_report_summary_counts_errors_and_warnings() -> None:
    violations = [
        AuditViolation(rule_id="R1", severity="error", message="m", role_path="/p"),
        AuditViolation(rule_id="R2", severity="warning", message="m", role_path="/p"),
        AuditViolation(rule_id="R3", severity="warning", message="m", role_path="/p"),
    ]
    report = AuditReport(violations=violations)
    assert report.passed is False
    assert "3 violation(s)" in report.summary
    assert "1 error(s)" in report.summary
    assert "2 warning(s)" in report.summary


def test_audit_report_custom_summary_overrides_default() -> None:
    report = AuditReport(violations=[], summary="custom")
    assert report.summary == "custom"


def test_load_audit_rules_from_policy_stub_returns_empty() -> None:
    assert load_audit_rules_from_policy({"policy_rules": [{"id": "R1"}]}) == []
