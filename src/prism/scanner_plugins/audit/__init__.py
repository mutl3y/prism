"""Audit plugin package for scanner_plugins."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from prism.scanner_config.audit_rules import AuditRule, AuditViolation
from prism.scanner_plugins.audit.loader import load_audit_rules_from_file
from prism.scanner_plugins.audit.runner import run_audit


@runtime_checkable
class AuditPlugin(Protocol):
    """Protocol for audit plugins that evaluate scan payloads against policy rules."""

    AUDIT_PLUGIN_NAME: str

    def evaluate(
        self,
        scan_payload: dict,
        rules: list[AuditRule],
    ) -> list[AuditViolation]:
        """Evaluate scan_payload against rules, returning violations found."""
        ...


__all__ = [
    "AuditPlugin",
    "load_audit_rules_from_file",
    "run_audit",
]
