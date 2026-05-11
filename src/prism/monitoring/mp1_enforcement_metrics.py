"""MP1 Enforcement Metrics Collection and Export.

Provides Prometheus-compatible metrics for MP1 marker-prefix enforcement:
- Bundle violations tracking
- Marker-prefix error detection
- Plugin override attempts
- Consumer access patterns
- Canary stage duration monitoring

Alert Thresholds:
- CRITICAL: 5+ violations per 60 minutes
- WARNING: 2+ violations per 60 minutes
- OK: < 2 violations per 60 minutes

Format: Prometheus text format + JSON export

Phase: Q2 Initiative 3, Phase 2, Task 2.5 (May 15, 2026)
Builder: Builder-MetricsLead
Status: Implementation
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class AlertLevel(Enum):
    """Alert severity levels."""

    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class AlertStatus:
    """Alert status with level and message."""

    level: AlertLevel
    message: str
    timestamp: float | None = None


class Counter:
    """Simple counter metric (monotonically increasing)."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.value: int = 0

    def increment(self, amount: int = 1) -> None:
        """Increment counter by amount."""
        self.value += amount

    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0

    def to_prometheus(self) -> str:
        """Export to Prometheus format."""
        return f"# HELP {self.name} {self.description}\n# TYPE {self.name} counter\n{self.name} {self.value}\n"


class Gauge:
    """Simple gauge metric (can increase or decrease)."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.value: float = 0

    def set(self, value: float) -> None:
        """Set gauge to specific value."""
        self.value = value

    def increment(self, amount: float = 1) -> None:
        """Increment gauge by amount."""
        self.value += amount

    def decrement(self, amount: float = 1) -> None:
        """Decrement gauge by amount."""
        self.value -= amount

    def reset(self) -> None:
        """Reset gauge to zero."""
        self.value = 0

    def to_prometheus(self) -> str:
        """Export to Prometheus format."""
        return f"# HELP {self.name} {self.description}\n# TYPE {self.name} gauge\n{self.name} {self.value}\n"


class MP1EnforcementMetrics:
    """MP1 Enforcement Metrics Collection.

    Tracks 5 key metrics for MP1 marker-prefix enforcement:
    1. mp1_bundle_violations_total: Total ValueError raises
    2. mp1_marker_prefix_missing_errors: Missing bundle/key errors
    3. mp1_plugin_override_attempts: Blocked override attempts
    4. mp1_consumer_access_total: Valid accesses
    5. mp1_canary_stage_duration: Stage execution time

    Prometheus-compatible export + JSON export support.
    Alert thresholds: CRITICAL (5+/hour), WARNING (2+/hour)
    """

    CRITICAL_THRESHOLD = 5  # 5+ violations per hour triggers CRITICAL
    WARNING_THRESHOLD = 2  # 2+ violations per hour triggers WARNING

    def __init__(self) -> None:
        """Initialize all 5 MP1 enforcement metrics."""
        self.bundle_violations_total = Counter(
            "mp1_bundle_violations_total",
            "Total ValueError raises for marker-prefix bundle enforcement",
        )
        self.marker_prefix_missing_errors = Counter(
            "mp1_marker_prefix_missing_errors",
            "Errors when marker-prefix missing or bundle malformed",
        )
        self.plugin_override_attempts = Counter(
            "mp1_plugin_override_attempts",
            "Blocked override attempts on marker-prefix",
        )
        self.consumer_access_total = Counter(
            "mp1_consumer_access_total",
            "Valid consumer accesses to marker-prefix via bundle",
        )
        self.canary_stage_duration = Gauge(
            "mp1_canary_stage_duration",
            "Canary rollout stage execution time in seconds",
        )

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.bundle_violations_total.reset()
        self.marker_prefix_missing_errors.reset()
        self.plugin_override_attempts.reset()
        self.consumer_access_total.reset()
        self.canary_stage_duration.reset()

    def snapshot(self) -> Dict[str, Any]:
        """Return current state of all metrics as dict."""
        return {
            "bundle_violations_total": self.bundle_violations_total.value,
            "marker_prefix_missing_errors": self.marker_prefix_missing_errors.value,
            "plugin_override_attempts": self.plugin_override_attempts.value,
            "consumer_access_total": self.consumer_access_total.value,
            "canary_stage_duration": self.canary_stage_duration.value,
        }

    def to_prometheus_text(self) -> str:
        """Export all metrics in Prometheus text format.

        Format:
            # HELP [metric] [description]
            # TYPE [metric] [type]
            [metric] [value]
        """
        output = []
        output.append(self.bundle_violations_total.to_prometheus())
        output.append(self.marker_prefix_missing_errors.to_prometheus())
        output.append(self.plugin_override_attempts.to_prometheus())
        output.append(self.consumer_access_total.to_prometheus())
        output.append(self.canary_stage_duration.to_prometheus())
        return "".join(output)

    def to_json(self) -> str:
        """Export all metrics in JSON format."""
        return json.dumps(self.snapshot(), indent=2)

    def check_alert_threshold(self) -> AlertStatus:
        """Check if metrics exceed alert thresholds.

        Returns:
            AlertStatus with level (OK, WARNING, CRITICAL) and message.

        Thresholds:
            - CRITICAL: bundle_violations_total >= 5
            - WARNING: bundle_violations_total >= 2 and < 5
            - OK: bundle_violations_total < 2
        """
        violations = self.bundle_violations_total.value

        if violations >= self.CRITICAL_THRESHOLD:
            return AlertStatus(
                level=AlertLevel.CRITICAL,
                message=f"CRITICAL: {violations} MP1 bundle violations detected (threshold: {self.CRITICAL_THRESHOLD}). Canary deployment paused. Check rollback procedures.",
            )

        if violations >= self.WARNING_THRESHOLD:
            return AlertStatus(
                level=AlertLevel.WARNING,
                message=f"WARNING: {violations} MP1 bundle violations detected (threshold: {self.WARNING_THRESHOLD}). Monitor closely. Prepare rollback if violations increase.",
            )

        return AlertStatus(
            level=AlertLevel.OK,
            message=f"OK: {violations} MP1 bundle violations (within threshold)",
        )

    def get_metrics_dashboard_config(self) -> Dict[str, Any]:
        """Return dashboard configuration for monitoring UI.

        Includes:
        - 5 key metrics definitions
        - 2 alert thresholds (WARNING, CRITICAL)
        - Dashboard layout
        - Refresh intervals
        """
        return {
            "dashboard": {
                "title": "MP1 Enforcement Monitoring",
                "refresh_interval_seconds": 60,
                "alerts_enabled": True,
            },
            "metrics": [
                {
                    "name": "mp1_bundle_violations_total",
                    "type": "counter",
                    "unit": "violations",
                    "description": "Total ValueError raises for marker-prefix bundle",
                    "alert_thresholds": {
                        "warning": self.WARNING_THRESHOLD,
                        "critical": self.CRITICAL_THRESHOLD,
                    },
                },
                {
                    "name": "mp1_marker_prefix_missing_errors",
                    "type": "counter",
                    "unit": "errors",
                    "description": "Missing bundle or key errors",
                },
                {
                    "name": "mp1_plugin_override_attempts",
                    "type": "counter",
                    "unit": "attempts",
                    "description": "Blocked override attempts",
                },
                {
                    "name": "mp1_consumer_access_total",
                    "type": "counter",
                    "unit": "accesses",
                    "description": "Valid consumer accesses",
                },
                {
                    "name": "mp1_canary_stage_duration",
                    "type": "gauge",
                    "unit": "seconds",
                    "description": "Canary stage execution time",
                },
            ],
            "alerts": [
                {
                    "name": "MP1CriticalViolations",
                    "metric": "mp1_bundle_violations_total",
                    "condition": f">= {self.CRITICAL_THRESHOLD}",
                    "severity": "CRITICAL",
                    "action": "Pause canary stage and execute rollback",
                },
                {
                    "name": "MP1WarningViolations",
                    "metric": "mp1_bundle_violations_total",
                    "condition": f">= {self.WARNING_THRESHOLD}",
                    "severity": "WARNING",
                    "action": "Monitor closely, prepare rollback procedures",
                },
            ],
        }
