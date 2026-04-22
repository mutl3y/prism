"""Tests for Policy as Code Wave 0 stubs.

Validates that all architecture stubs are importable, correctly typed,
and behave as specified (loader returns empty list, builtins raise NotImplementedError).
"""

from __future__ import annotations

import pytest


class TestAuditRulesImportable:
    def test_audit_rule_importable(self) -> None:
        from prism.scanner_config.audit_rules import AuditRule

        assert AuditRule is not None

    def test_audit_violation_importable(self) -> None:
        from prism.scanner_config.audit_rules import AuditViolation

        assert AuditViolation is not None

    def test_audit_report_importable(self) -> None:
        from prism.scanner_config.audit_rules import AuditReport

        assert AuditReport is not None

    def test_audit_rule_instantiable(self) -> None:
        from prism.scanner_config.audit_rules import AuditRule

        rule = AuditRule(id="test-rule", description="A test rule")
        assert rule.id == "test-rule"
        assert rule.description == "A test rule"
        assert rule.severity == "error"
        assert rule.enabled is True
        assert rule.params == {}

    def test_audit_violation_instantiable(self) -> None:
        from prism.scanner_config.audit_rules import AuditViolation

        violation = AuditViolation(
            rule_id="test-rule",
            severity="error",
            message="Test violation",
            role_path="/some/role",
        )
        assert violation.rule_id == "test-rule"
        assert violation.severity == "error"
        assert violation.message == "Test violation"
        assert violation.role_path == "/some/role"
        assert violation.evidence == []

    def test_audit_report_instantiable_with_no_violations(self) -> None:
        from prism.scanner_config.audit_rules import AuditReport

        report = AuditReport()
        assert report.violations == []
        assert report.passed is True

    def test_audit_report_passed_false_on_error_violation(self) -> None:
        from prism.scanner_config.audit_rules import AuditReport, AuditViolation

        violation = AuditViolation(
            rule_id="r1", severity="error", message="fail", role_path="/"
        )
        report = AuditReport(violations=[violation])
        assert report.passed is False


class TestLoadAuditRulesFromPolicy:
    def test_returns_empty_list_for_empty_dict(self) -> None:
        from prism.scanner_config.audit_rules import load_audit_rules_from_policy

        result = load_audit_rules_from_policy({})
        assert result == []

    def test_returns_empty_list_for_dict_with_policy_rules(self) -> None:
        from prism.scanner_config.audit_rules import load_audit_rules_from_policy

        result = load_audit_rules_from_policy({"policy_rules": [{"id": "r1"}]})
        assert result == []

    def test_returns_list_type(self) -> None:
        from prism.scanner_config.audit_rules import load_audit_rules_from_policy

        result = load_audit_rules_from_policy({})
        assert isinstance(result, list)


class TestAuditPluginProtocol:
    def test_audit_plugin_importable(self) -> None:
        from prism.scanner_plugins.audit import AuditPlugin

        assert AuditPlugin is not None

    def test_audit_plugin_is_runtime_checkable(self) -> None:
        from prism.scanner_plugins.audit import AuditPlugin

        class ConcretePlugin:
            AUDIT_PLUGIN_NAME = "test-plugin"

            def evaluate(self, scan_payload: dict, rules: list) -> list:
                return []

        assert isinstance(ConcretePlugin(), AuditPlugin)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        from prism.scanner_plugins.audit import AuditPlugin

        class NotAPlugin:
            pass

        assert not isinstance(NotAPlugin(), AuditPlugin)


class TestBuiltinRulesImportable:
    def test_no_shell_without_runbook_importable(self) -> None:
        from prism.scanner_plugins.audit.builtin_rules import NoShellWithoutRunbookRule

        assert NoShellWithoutRunbookRule is not None

    def test_runbook_coverage_rule_importable(self) -> None:
        from prism.scanner_plugins.audit.builtin_rules import RunbookCoverageRule

        assert RunbookCoverageRule is not None

    def test_dependency_compliance_rule_importable(self) -> None:
        from prism.scanner_plugins.audit.builtin_rules import DependencyComplianceRule

        assert DependencyComplianceRule is not None

    def test_no_shell_without_runbook_evaluate_raises_not_implemented(self) -> None:
        from prism.scanner_config.audit_rules import AuditRule
        from prism.scanner_plugins.audit.builtin_rules import NoShellWithoutRunbookRule

        rule = AuditRule(id="no-shell", description="stub")
        with pytest.raises(NotImplementedError):
            NoShellWithoutRunbookRule().evaluate({}, rule)

    def test_runbook_coverage_evaluate_raises_not_implemented(self) -> None:
        from prism.scanner_config.audit_rules import AuditRule
        from prism.scanner_plugins.audit.builtin_rules import RunbookCoverageRule

        rule = AuditRule(id="coverage", description="stub")
        with pytest.raises(NotImplementedError):
            RunbookCoverageRule().evaluate({}, rule)

    def test_dependency_compliance_evaluate_raises_not_implemented(self) -> None:
        from prism.scanner_config.audit_rules import AuditRule
        from prism.scanner_plugins.audit.builtin_rules import DependencyComplianceRule

        rule = AuditRule(id="dep-compliance", description="stub")
        with pytest.raises(NotImplementedError):
            DependencyComplianceRule().evaluate({}, rule)


class TestDIAuditSlot:
    def _make_di(self):
        from prism.scanner_core.di import DIContainer

        return DIContainer(role_path="/some/role", scan_options={})

    def test_factory_audit_plugin_returns_none_by_default(self) -> None:
        di = self._make_di()
        assert di.factory_audit_plugin() is None

    def test_inject_mock_audit_plugin_allows_mock_retrieval(self) -> None:
        di = self._make_di()
        mock_plugin = object()
        di.inject_mock_audit_plugin(mock_plugin)
        assert di.factory_audit_plugin() is mock_plugin

    def test_inject_mock_audit_plugin_cleared_by_clear_mocks(self) -> None:
        di = self._make_di()
        di.inject_mock_audit_plugin(object())
        di.clear_mocks()
        assert di.factory_audit_plugin() is None


class TestScannerConfigPackageExports:
    def test_audit_rule_importable_from_package(self) -> None:
        from prism.scanner_config import AuditRule

        assert AuditRule is not None

    def test_audit_violation_importable_from_package(self) -> None:
        from prism.scanner_config import AuditViolation

        assert AuditViolation is not None

    def test_audit_report_importable_from_package(self) -> None:
        from prism.scanner_config import AuditReport

        assert AuditReport is not None

    def test_load_audit_rules_importable_from_package(self) -> None:
        from prism.scanner_config import load_audit_rules_from_policy

        assert load_audit_rules_from_policy is not None


class TestCLIAuditFlags:
    def test_audit_rules_flag_accepted(self) -> None:
        from prism.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["role", "/some/role", "--audit-rules", "/path/to/rules.yml"]
        )
        assert args.audit_rules == "/path/to/rules.yml"

    def test_fail_on_audit_violations_flag_accepted(self) -> None:
        from prism.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["role", "/some/role", "--fail-on-audit-violations"])
        assert args.fail_on_audit_violations is True

    def test_fail_on_audit_violations_defaults_false(self) -> None:
        from prism.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["role", "/some/role"])
        assert args.fail_on_audit_violations is False

    def test_exit_code_audit_violations_constant(self) -> None:
        from prism.cli import EXIT_CODE_AUDIT_VIOLATIONS

        assert isinstance(EXIT_CODE_AUDIT_VIOLATIONS, int)
