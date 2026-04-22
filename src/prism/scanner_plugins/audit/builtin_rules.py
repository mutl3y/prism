"""Built-in Policy-as-Code audit rule implementations.

These are stub implementations. Each rule raises NotImplementedError
until the full scanner_config policy stack (MG-02/08) is wired in.
"""

from __future__ import annotations

from prism.scanner_config.audit_rules import AuditRule, AuditViolation


class NoShellWithoutRunbookRule:
    """Fail if any task uses the 'shell' module without an approved runbook entry.

    Policy example:
        FAIL build IF a role uses 'shell' without an approved runbook entry.

    Checks:
      - scan_payload["metadata"]["task_catalog"] for tasks with module=shell
      - Verifies each such task has a corresponding runbook entry
      - Reports violation for each shell task without runbook coverage
    """

    RULE_ID = "no-shell-without-runbook"

    def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]:
        raise NotImplementedError(
            "NoShellWithoutRunbookRule.evaluate is not yet implemented. "
            "Requires task_catalog in scan payload metadata and runbook entries. "
            "Blocked on scanner_config MG-02/08."
        )


class RunbookCoverageRule:
    """Fail/warn if runbook coverage percentage drops below a configured threshold.

    Policy example:
        ALERT team IF runbook coverage for a production role drops below 80%.

    Checks:
      - scan_payload["metadata"].get("task_catalog") for total task count
      - Counts tasks with prism~runbook annotations
      - Computes coverage = annotated / total
      - Violations if coverage < rule.params.get("threshold", 0.8)
    """

    RULE_ID = "runbook-coverage-min"

    def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]:
        raise NotImplementedError(
            "RunbookCoverageRule.evaluate is not yet implemented. "
            "Requires runbook annotation counts from task_catalog. "
            "Blocked on scanner_config MG-02/08."
        )


class DependencyComplianceRule:
    """Fail if a role's collection dependencies are not in an approved list.

    Policy example:
        CREATE ticket IF a role's dependencies are out of compliance.

    Checks:
      - scan_payload.get("requirements") for collection/role dependencies
      - Compares against rule.params.get("approved_collections", [])
      - Reports violation for each unapproved dependency
    """

    RULE_ID = "dependency-compliance"

    def evaluate(self, scan_payload: dict, rule: AuditRule) -> list[AuditViolation]:
        raise NotImplementedError(
            "DependencyComplianceRule.evaluate is not yet implemented. "
            "Requires requirements list from scan payload. "
            "Blocked on scanner_config MG-02/08."
        )
