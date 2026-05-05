"""T3-05: Structured scan telemetry.

Provides :class:`ScanTelemetry` (a TypedDict for machine-readable scan
metrics) and :class:`TelemetryCollector` (an :mod:`event bus
<prism.scanner_core.events>` listener that captures per-phase durations
and aggregate counters).

The collector is opt-in. Use :func:`telemetry_session` as a context
manager to record one scan, or instantiate :class:`TelemetryCollector`
and register it manually for finer control.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from typing import IO, Iterator, TypedDict

from prism.scanner_core.events import (
    ScanPhaseEvent,
    register_default_listener,
    unregister_default_listener,
)


class PhaseTelemetry(TypedDict):
    """Per-phase timing record."""

    phase_name: str
    duration_ms: int


class ScanTelemetry(TypedDict, total=False):
    """Aggregate telemetry block for a single scan."""

    scan_duration_ms: int
    phases: list[PhaseTelemetry]
    plugin_key: str
    errors: list[str]


_TELEMETRY_LOG_ENV = "PRISM_TELEMETRY_JSON_LOG"
_logger = logging.getLogger(__name__)


class TelemetryCollector:
    """Collects phase timings via :class:`ScanPhaseEvent` subscription.

    When the ``PRISM_TELEMETRY_JSON_LOG`` env var is set, each phase
    boundary is also written as a JSON record to the configured stream
    (stderr by default), one record per line.
    """

    def __init__(self, log_stream: IO[str] | None = None) -> None:
        self._lock = threading.Lock()
        self._phase_starts: dict[str, float] = {}
        self._phases: list[PhaseTelemetry] = []
        self._scan_started: float = time.monotonic()
        self._log_stream = log_stream if log_stream is not None else sys.stderr
        self._json_log_enabled = bool(os.environ.get(_TELEMETRY_LOG_ENV))

    def __call__(self, event: ScanPhaseEvent) -> None:
        if event.kind == "pre":
            with self._lock:
                self._phase_starts[event.phase_name] = time.monotonic()
            if self._json_log_enabled:
                self._emit_json({"phase": event.phase_name, "kind": "pre"})
            return
        with self._lock:
            start = self._phase_starts.pop(event.phase_name, None)
        duration_ms = int((time.monotonic() - start) * 1000) if start is not None else 0
        with self._lock:
            self._phases.append(
                PhaseTelemetry(phase_name=event.phase_name, duration_ms=duration_ms)
            )
        if self._json_log_enabled:
            self._emit_json(
                {
                    "phase": event.phase_name,
                    "kind": "post",
                    "duration_ms": duration_ms,
                }
            )

    def _emit_json(self, record: dict[str, object]) -> None:
        try:
            self._log_stream.write(json.dumps(record) + "\n")
            self._log_stream.flush()
        except Exception as exc:  # pragma: no cover - caller-provided IO boundary
            _logger.exception(
                "telemetry json log write failed for %s (%s)",
                type(self._log_stream).__name__,
                type(exc).__name__,
            )

    def snapshot(self, *, plugin_key: str | None = None) -> ScanTelemetry:
        """Return the aggregated :class:`ScanTelemetry` so far."""
        scan_duration_ms = int((time.monotonic() - self._scan_started) * 1000)
        result: ScanTelemetry = {
            "scan_duration_ms": scan_duration_ms,
            "phases": list(self._phases),
            "errors": [],
        }
        if plugin_key is not None:
            result["plugin_key"] = plugin_key
        return result


@contextmanager
def telemetry_session(
    *, log_stream: IO[str] | None = None
) -> Iterator[TelemetryCollector]:
    """Register a :class:`TelemetryCollector` for the duration of a scan."""
    collector = TelemetryCollector(log_stream=log_stream)
    register_default_listener(collector)
    try:
        yield collector
    finally:
        unregister_default_listener(collector)


__all__ = [
    "PhaseTelemetry",
    "ScanTelemetry",
    "TelemetryCollector",
    "telemetry_session",
]
