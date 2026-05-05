"""T4-03: CLI streaming progress reporter.

Consumes :class:`~prism.scanner_core.events.ScanPhaseEvent` instances and
writes human-readable phase boundaries to a stream (stderr by default) so
long scans give visible feedback. stdout stays JSON-clean.
"""

from __future__ import annotations

import sys
import threading
import time
from contextlib import contextmanager
from typing import IO, Iterator

from prism.scanner_core.events import (
    ScanPhaseEvent,
    register_default_listener,
    unregister_default_listener,
)


class ProgressReporter:
    """Write pre/post phase events to a stream."""

    def __init__(self, stream: IO[str] | None = None) -> None:
        self._stream = stream if stream is not None else sys.stderr
        self._lock = threading.Lock()
        self._phase_starts: dict[str, float] = {}

    def __call__(self, event: ScanPhaseEvent) -> None:
        if event.kind == "pre":
            with self._lock:
                self._phase_starts[event.phase_name] = time.monotonic()
            self._stream.write(f"[prism] {event.phase_name}: start\n")
        else:
            with self._lock:
                start = self._phase_starts.pop(event.phase_name, None)
            elapsed_ms = (
                int((time.monotonic() - start) * 1000) if start is not None else 0
            )
            self._stream.write(f"[prism] {event.phase_name}: done ({elapsed_ms} ms)\n")
        self._stream.flush()


@contextmanager
def progress_reporter_enabled(
    stream: IO[str] | None = None,
) -> Iterator[ProgressReporter]:
    """Register a :class:`ProgressReporter` for the duration of the block."""
    reporter = ProgressReporter(stream=stream)
    register_default_listener(reporter)
    try:
        yield reporter
    finally:
        unregister_default_listener(reporter)
