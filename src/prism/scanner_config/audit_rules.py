"""Policy-as-Code audit rule type definitions."""

from __future__ import annotations

from typing import Any


class AuditRule:
    """Represents a single policy rule that can be evaluated against a scan payload."""

    def __init__(
        self,
        *,
        id: str,
        description: str,
        severity: str = "error",
        enabled: bool = True,
        params: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.description = description
        self.severity = severity
        self.enabled = enabled
        self.params: dict[str, Any] = params or {}


class AuditViolation:
    """A single rule violation found in a scan payload."""

    def __init__(
        self,
        *,
        rule_id: str,
        severity: str,
        message: str,
        role_path: str,
        evidence: list[str] | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.role_path = role_path
        self.evidence: list[str] = evidence or []


class AuditReport:
    """Aggregate audit result for a single role scan."""

    def __init__(
        self,
        *,
        violations: list[AuditViolation] | None = None,
        summary: str = "",
    ) -> None:
        self.violations: list[AuditViolation] = violations or []
        self.passed = not any(v.severity == "error" for v in self.violations)
        self.summary = summary or self._default_summary()

    def _default_summary(self) -> str:
        if not self.violations:
            return "All policy checks passed."
        error_count = sum(1 for v in self.violations if v.severity == "error")
        warn_count = sum(1 for v in self.violations if v.severity == "warning")
        return (
            f"{len(self.violations)} violation(s): "
            f"{error_count} error(s), {warn_count} warning(s)."
        )


def load_audit_rules_from_policy(policy_dict: dict[str, Any]) -> list[AuditRule]:
    """Load audit rules from a parsed .prism.yml policy dict.

    Stub implementation — returns empty list until scanner_config policy
    loading (MG-02/08) is wired in. The policy_rules: section in .prism.yml
    will be parsed here once the full policy stack is available.
    """
    return []
