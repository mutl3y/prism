"""MP1 Enforcement Metrics Collection Test Suite.

Tests for monitoring, alerting, and metrics export for MP1 enforcement.

Metrics:
- mp1_bundle_violations_total: Counter of total ValueError raises
- mp1_marker_prefix_missing_errors: Counter of missing bundle/key errors
- mp1_plugin_override_attempts: Counter of blocked override attempts
- mp1_consumer_access_total: Counter of valid accesses
- mp1_canary_stage_duration: Gauge of stage execution time

Phase: Q2 Initiative 3, Phase 2, Task 2.5 (May 15, 2026)
Status: ✅ TDD Implementation
"""

from __future__ import annotations


class TestMP1MetricsCollection:
    """Test metrics collection for MP1 enforcement.

    Validates that all metrics are properly tracked and exported
    in Prometheus format.
    """

    def test_metrics_module_exists(self):
        """Verify mp1_enforcement_metrics module exists and exports metrics."""
        from prism.monitoring import mp1_enforcement_metrics

        assert hasattr(mp1_enforcement_metrics, "MP1EnforcementMetrics")
        assert callable(mp1_enforcement_metrics.MP1EnforcementMetrics)

    def test_metrics_initialization(self):
        """Verify MP1EnforcementMetrics initializes with all 5 metrics."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()

        # Verify all 5 metrics are initialized
        assert hasattr(metrics, "bundle_violations_total")
        assert hasattr(metrics, "marker_prefix_missing_errors")
        assert hasattr(metrics, "plugin_override_attempts")
        assert hasattr(metrics, "consumer_access_total")
        assert hasattr(metrics, "canary_stage_duration")

    def test_bundle_violations_counter(self):
        """Test bundle_violations_total counter increments correctly."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        assert metrics.bundle_violations_total.value == 0

        metrics.bundle_violations_total.increment()
        assert metrics.bundle_violations_total.value == 1

        metrics.bundle_violations_total.increment(5)
        assert metrics.bundle_violations_total.value == 6

    def test_marker_prefix_missing_errors_counter(self):
        """Test marker_prefix_missing_errors counter increments correctly."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        assert metrics.marker_prefix_missing_errors.value == 0

        metrics.marker_prefix_missing_errors.increment()
        assert metrics.marker_prefix_missing_errors.value == 1

    def test_plugin_override_attempts_counter(self):
        """Test plugin_override_attempts counter increments correctly."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        assert metrics.plugin_override_attempts.value == 0

        metrics.plugin_override_attempts.increment()
        assert metrics.plugin_override_attempts.value == 1

    def test_consumer_access_total_counter(self):
        """Test consumer_access_total counter increments correctly."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        assert metrics.consumer_access_total.value == 0

        metrics.consumer_access_total.increment()
        assert metrics.consumer_access_total.value == 1

    def test_canary_stage_duration_gauge(self):
        """Test canary_stage_duration gauge sets and retrieves values."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        assert metrics.canary_stage_duration.value == 0

        metrics.canary_stage_duration.set(45.5)
        assert metrics.canary_stage_duration.value == 45.5

        metrics.canary_stage_duration.set(120.3)
        assert metrics.canary_stage_duration.value == 120.3

    def test_prometheus_export_format(self):
        """Test Prometheus-compatible export format."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        metrics.bundle_violations_total.increment(3)
        metrics.marker_prefix_missing_errors.increment(1)
        metrics.plugin_override_attempts.increment(2)
        metrics.consumer_access_total.increment(10)
        metrics.canary_stage_duration.set(60.0)

        export = metrics.to_prometheus_text()

        # Verify Prometheus format
        assert "# HELP mp1_bundle_violations_total" in export
        assert "# TYPE mp1_bundle_violations_total counter" in export
        assert "mp1_bundle_violations_total 3" in export

        assert "# HELP mp1_marker_prefix_missing_errors" in export
        assert "# TYPE mp1_marker_prefix_missing_errors counter" in export
        assert "mp1_marker_prefix_missing_errors 1" in export

        assert "# HELP mp1_plugin_override_attempts" in export
        assert "# TYPE mp1_plugin_override_attempts counter" in export
        assert "mp1_plugin_override_attempts 2" in export

        assert "# HELP mp1_consumer_access_total" in export
        assert "# TYPE mp1_consumer_access_total counter" in export
        assert "mp1_consumer_access_total 10" in export

        assert "# HELP mp1_canary_stage_duration" in export
        assert "# TYPE mp1_canary_stage_duration gauge" in export
        assert "mp1_canary_stage_duration 60" in export

    def test_alert_threshold_check_critical(self):
        """Test alert threshold check for CRITICAL (5+ violations/hour)."""
        from prism.monitoring.mp1_enforcement_metrics import (
            MP1EnforcementMetrics,
            AlertLevel,
        )

        metrics = MP1EnforcementMetrics()
        # Add violations below critical threshold (1 violation = OK)
        metrics.bundle_violations_total.increment(1)
        alert = metrics.check_alert_threshold()
        assert alert.level == AlertLevel.OK

        # Add violations to critical threshold (5 total = CRITICAL)
        metrics.bundle_violations_total.increment(4)  # Now 5
        alert = metrics.check_alert_threshold()
        assert alert.level == AlertLevel.CRITICAL
        assert "5" in alert.message

    def test_alert_threshold_check_warning(self):
        """Test alert threshold check for WARNING (2+ violations/hour)."""
        from prism.monitoring.mp1_enforcement_metrics import (
            MP1EnforcementMetrics,
            AlertLevel,
        )

        metrics = MP1EnforcementMetrics()
        # Add violations below warning threshold
        metrics.bundle_violations_total.increment(1)
        alert = metrics.check_alert_threshold()
        assert alert.level == AlertLevel.OK

        # Add violations to warning threshold
        metrics.bundle_violations_total.increment(1)  # Now 2
        alert = metrics.check_alert_threshold()
        assert alert.level == AlertLevel.WARNING
        assert "2" in alert.message

    def test_metrics_reset(self):
        """Test metrics reset clears all counters and gauges."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        metrics.bundle_violations_total.increment(5)
        metrics.marker_prefix_missing_errors.increment(3)
        metrics.consumer_access_total.increment(10)
        metrics.canary_stage_duration.set(45.0)

        metrics.reset()

        assert metrics.bundle_violations_total.value == 0
        assert metrics.marker_prefix_missing_errors.value == 0
        assert metrics.plugin_override_attempts.value == 0
        assert metrics.consumer_access_total.value == 0
        assert metrics.canary_stage_duration.value == 0

    def test_metrics_snapshot(self):
        """Test metrics snapshot captures current state."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics

        metrics = MP1EnforcementMetrics()
        metrics.bundle_violations_total.increment(7)
        metrics.marker_prefix_missing_errors.increment(2)
        metrics.consumer_access_total.increment(15)
        metrics.canary_stage_duration.set(55.5)

        snapshot = metrics.snapshot()

        assert snapshot["bundle_violations_total"] == 7
        assert snapshot["marker_prefix_missing_errors"] == 2
        assert snapshot["plugin_override_attempts"] == 0
        assert snapshot["consumer_access_total"] == 15
        assert snapshot["canary_stage_duration"] == 55.5

    def test_metrics_json_export(self):
        """Test JSON export of metrics."""
        from prism.monitoring.mp1_enforcement_metrics import MP1EnforcementMetrics
        import json

        metrics = MP1EnforcementMetrics()
        metrics.bundle_violations_total.increment(4)
        metrics.marker_prefix_missing_errors.increment(1)
        metrics.consumer_access_total.increment(8)

        json_export = metrics.to_json()
        parsed = json.loads(json_export)

        assert parsed["bundle_violations_total"] == 4
        assert parsed["marker_prefix_missing_errors"] == 1
        assert parsed["consumer_access_total"] == 8
