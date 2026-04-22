"""Built-in audit plugin orchestrator (T1-01 Wave 1).

Implements the ``AuditPlugin`` Protocol by dispatching each enabled
``AuditRule`` to a registered rule-class based on ``rule.id``. Per-rule
classes follow the convention::

    class SomeRule:
        RULE_ID = "some-id"
        def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]: ...

Unknown rule IDs are surfaced as a single ``warning``-severity violation so
operators can see typos without failing the build. Unimplemented stub rules
that raise ``NotImplementedError`` are likewise reported as warnings.
"""

from __future__ import annotations

from typing import Any, Protocol

from prism.scanner_config.audit_rules import (
    AuditReport,
    AuditRule,
    AuditViolation,
)


class _RuleEvaluator(Protocol):
    RULE_ID: str

    def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]: ...


class BuiltinAuditPlugin:
    """Default audit plugin that dispatches by rule.id to registered evaluators."""

    AUDIT_PLUGIN_NAME = "builtin"

    def __init__(self, rule_registry: dict[str, _RuleEvaluator] | None = None) -> None:
        self._registry: dict[str, _RuleEvaluator] = (
            dict(rule_registry) if rule_registry is not None else _default_registry()
        )

    def register_rule(self, evaluator: _RuleEvaluator) -> None:
        self._registry[evaluator.RULE_ID] = evaluator

    def evaluate(
        self,
        scan_payload: dict,
        rules: list[AuditRule],
    ) -> list[AuditViolation]:
        violations: list[AuditViolation] = []
        role_path = _role_path_from_payload(scan_payload)
        for rule in rules:
            if not rule.enabled:
                continue
            evaluator = self._registry.get(rule.id)
            if evaluator is None:
                violations.append(
                    AuditViolation(
                        rule_id=rule.id,
                        severity="warning",
                        message=(
                            f"No evaluator registered for rule '{rule.id}'. "
                            "Skipping; check rule id or register a custom evaluator."
                        ),
                        role_path=role_path,
                    )
                )
                continue
            try:
                rule_violations = evaluator.evaluate(scan_payload, rule)
            except NotImplementedError as exc:
                violations.append(
                    AuditViolation(
                        rule_id=rule.id,
                        severity="warning",
                        message=f"Rule '{rule.id}' evaluator is not yet implemented: {exc}",
                        role_path=role_path,
                    )
                )
                continue
            violations.extend(rule_violations)
        return violations


def run_audit(
    scan_payload: dict,
    rules: list[AuditRule],
    plugin: Any | None = None,
) -> AuditReport:
    """Run an audit and assemble a report."""
    audit_plugin = plugin if plugin is not None else BuiltinAuditPlugin()
    violations = audit_plugin.evaluate(scan_payload, rules)
    return AuditReport(violations=violations)


def _role_path_from_payload(scan_payload: dict) -> str:
    for key in ("role_path", "path", "name", "role_name"):
        value = scan_payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _default_registry() -> dict[str, _RuleEvaluator]:
    """Return a registry with built-in rule evaluators.

    Note: the three stub rules in ``builtin_rules.py`` still raise
    ``NotImplementedError`` because they require payload schema additions
    (task_catalog, runbook coverage facts, requirements list). They are
    registered so that ``--audit-rules`` callers receive an explanatory
    warning rather than a silent skip.
    """
    from prism.scanner_plugins.audit.builtin_rules import (
        DependencyComplianceRule,
        NoShellWithoutRunbookRule,
        RunbookCoverageRule,
    )

    rules: list[_RuleEvaluator] = [
        NoShellWithoutRunbookRule(),
        RunbookCoverageRule(),
        DependencyComplianceRule(),
    ]
    return {evaluator.RULE_ID: evaluator for evaluator in rules}
