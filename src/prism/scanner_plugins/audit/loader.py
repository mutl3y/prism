"""Audit rule loader for Policy-as-Code (T1-01 Wave 1).

Loads ``AuditRule`` definitions from a local YAML or JSON file. Remote
(HTTP/HTTPS) loading is intentionally deferred — see plan T1-01 work_items.

Expected file shape (top-level may include other keys; only ``policy_rules``
or ``audit_rules`` is consumed)::

    policy_rules:
      - id: no-shell-without-runbook
        description: "Shell tasks must have an approved runbook entry"
        severity: error            # optional, defaults to "error"
        enabled: true              # optional, defaults to true
        params:
          allowed_runbook_ids: ["RB-1234"]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from prism.scanner_config.audit_rules import AuditRule


class AuditRuleLoadError(ValueError):
    """Raised when an audit rule file cannot be parsed into AuditRule objects."""


def load_audit_rules_from_file(path: str | Path) -> list[AuditRule]:
    """Load audit rules from a local YAML or JSON file."""
    rules_path = Path(path)
    if not rules_path.is_file():
        raise AuditRuleLoadError(f"Audit rules file not found: {rules_path}")

    raw_text = rules_path.read_text(encoding="utf-8")
    suffix = rules_path.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(raw_text)
        else:
            data = yaml.safe_load(raw_text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise AuditRuleLoadError(
            f"Failed to parse audit rules file {rules_path}: {exc}"
        ) from exc

    if data is None:
        return []
    if not isinstance(data, dict):
        raise AuditRuleLoadError(
            f"Audit rules file {rules_path} must contain a mapping at the top level"
        )

    rules_section = data.get("policy_rules")
    if rules_section is None:
        rules_section = data.get("audit_rules")
    if rules_section is None:
        return []
    if not isinstance(rules_section, list):
        raise AuditRuleLoadError(
            f"'policy_rules' in {rules_path} must be a list of rule mappings"
        )

    return [_build_rule(entry, rules_path) for entry in rules_section]


def _build_rule(entry: Any, source_path: Path) -> AuditRule:
    if not isinstance(entry, dict):
        raise AuditRuleLoadError(
            f"Each rule entry in {source_path} must be a mapping, got {type(entry).__name__}"
        )
    rule_id = entry.get("id")
    description = entry.get("description", "")
    if not rule_id or not isinstance(rule_id, str):
        raise AuditRuleLoadError(
            f"Rule in {source_path} is missing required string field 'id'"
        )
    severity = entry.get("severity", "error")
    if severity not in ("error", "warning", "info"):
        raise AuditRuleLoadError(
            f"Rule '{rule_id}' in {source_path} has invalid severity '{severity}'"
        )
    enabled = bool(entry.get("enabled", True))
    params = entry.get("params") or {}
    if not isinstance(params, dict):
        raise AuditRuleLoadError(
            f"Rule '{rule_id}' params in {source_path} must be a mapping"
        )

    return AuditRule(
        id=rule_id,
        description=str(description),
        severity=severity,
        enabled=enabled,
        params=params,
    )
