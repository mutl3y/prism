"""Scan phase event system (T3-01).

Provides a lightweight pub/sub bus for emitting :class:`ScanPhaseEvent`
instances at the boundaries of each scanner pipeline phase. The bus is
opt-in: when no listeners are registered, ``emit`` is effectively free
and no behaviour changes.

Subscribers are plain callables ``(ScanPhaseEvent) -> None``. Listener
exceptions are caught and logged so that observability never breaks the
scan; this matches the constitutional rule that telemetry must not change
production semantics.
"""

from __future__ import annotations

import copy
from collections import deque
from contextvars import ContextVar
import logging
import threading
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping

logger = logging.getLogger(__name__)


EventListener = Callable[["ScanPhaseEvent"], None]


# Canonical phase names emitted by the built-in pipeline. External
# consumers may emit additional phases without registering them here.
PHASE_FEATURE_DETECTION = "feature_detection"
PHASE_VARIABLE_DISCOVERY = "variable_discovery"
PHASE_OUTPUT_RENDER = "output_render"


@dataclass(frozen=True)
class ScanPhaseEvent:
    """A single pre/post boundary event for a named pipeline phase."""

    phase_name: str
    kind: str  # "pre" or "post"
    context: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in ("pre", "post"):
            raise ValueError(
                f"ScanPhaseEvent.kind must be 'pre' or 'post', got {self.kind!r}"
            )
        if not self.phase_name:
            raise ValueError("ScanPhaseEvent.phase_name must not be empty")


@dataclass(frozen=True)
class EventBusError:
    """Error event recorded when a listener fails.

    Stores only the exception metadata (type, message, traceback string),
    not the Exception object itself. This prevents memory leaks by not retaining
    exception frames and local variables that could keep large objects alive.

    This event is recorded directly by the EventBus without going through
    the listener loop, ensuring observability without infinite loops.
    """

    listener_name: str
    exception_type: str
    exception_message: str
    traceback_str: str
    timestamp: float
    event: ScanPhaseEvent | None = None


class EventBus:
    """In-process event bus.

    Listeners registered via :meth:`subscribe` receive every event
    dispatched through :meth:`emit`. Use :meth:`phase` as a context
    manager to emit a matched ``pre``/``post`` pair around a block of
    work.

    Listener list is append-only after module load.
    No runtime registration supported; lock protects against
    concurrent test fixture modifications only.

    When a listener raises an exception, an :class:`EventBusError` is
    recorded for observability. Error events are emitted directly without
    triggering the listener loop to avoid recursion.
    """

    def __init__(
        self, listeners: list[EventListener] | None = None, *, strict: bool = False
    ) -> None:
        self._listeners: list[EventListener] = list(listeners or [])
        self._listeners_lock = threading.RLock()
        self._strict = strict
        self._error_events: deque[EventBusError] = deque(maxlen=1000)
        self._error_lock = threading.RLock()

    def subscribe(self, listener: EventListener) -> None:
        if not callable(listener):
            raise TypeError("EventBus listener must be callable")
        with self._listeners_lock:
            self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        with self._listeners_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    @property
    def listener_count(self) -> int:
        with self._listeners_lock:
            return len(self._listeners)

    @property
    def error_count(self) -> int:
        """Return the number of errors recorded from listener failures."""
        with self._error_lock:
            return len(self._error_events)

    def get_error_events(self) -> list[EventBusError]:
        """Return a snapshot of recorded error events.

        Note: The returned list is a snapshot only; the bounded deque may evict
        older errors if the event bus receives many listener failures. This is
        by design to prevent memory leaks in long-running processes.
        """
        with self._error_lock:
            return list(self._error_events)

    def _record_listener_error(
        self, listener: EventListener, exception: Exception, event: ScanPhaseEvent
    ) -> None:
        """Record a listener error event for observability.

        Stores exception metadata (type, message, traceback string) only,
        not the Exception object itself. This prevents memory leaks by not
        retaining exception frames and local variables.

        Note: Error events are retained in a bounded deque (max 1000) to prevent
        unbounded memory growth if listeners fail frequently. Older errors are
        automatically evicted when the deque reaches capacity.
        """
        error_event = EventBusError(
            listener_name=getattr(listener, "__name__", repr(listener)),
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback_str=traceback.format_exc(),
            timestamp=time.time(),
            event=event,
        )
        with self._error_lock:
            self._error_events.append(error_event)

    def emit(self, event: ScanPhaseEvent) -> None:
        with self._listeners_lock:
            listeners_snapshot = list(self._listeners)
        if not listeners_snapshot:
            return

        # In strict mode, collect all exceptions and raise an aggregate after invoking all listeners
        # This preserves pub/sub isolation: all listeners are invoked, then failures are reported
        strict_mode_exceptions: list[tuple[EventListener, Exception]] = (
            [] if self._strict else []
        )

        for listener in listeners_snapshot:
            try:
                listener(event)
            except Exception as exc:  # pragma: no cover - defensive
                # Defensive: catch all exceptions from external listeners to prevent
                # one failing listener from breaking the entire event bus.
                # Listener authors should document their exception contracts,
                # but we do not enforce narrow types here to maximize robustness.
                self._record_listener_error(listener, exc, event)
                try:
                    logger.error(
                        "EventBus listener exception: phase=%s kind=%s listener=%r exc_type=%s exc=%r",
                        event.phase_name,
                        event.kind,
                        listener,
                        type(exc).__name__,
                        exc,
                    )
                except Exception as log_exc:
                    # If logging itself fails, emit to stderr to preserve diagnostic info
                    import sys

                    sys.stderr.write(
                        f"EventBus listener exception (logging failed): "
                        f"phase={event.phase_name} kind={event.kind} listener={listener!r} "
                        f"exc_type={type(exc).__name__} exc={exc!r} "
                        f"log_failure={type(log_exc).__name__}: {log_exc}\n"
                    )
                if self._strict:
                    # In strict mode, collect exceptions to raise after all listeners
                    strict_mode_exceptions.append((listener, exc))

        # In strict mode, raise an aggregate error after all listeners have been invoked
        if self._strict and strict_mode_exceptions:
            if len(strict_mode_exceptions) == 1:
                _, single_exc = strict_mode_exceptions[0]
                raise single_exc
            else:
                # Multiple failures: raise the first with others chained as context
                _, first_exc = strict_mode_exceptions[0]
                error_msg = (
                    f"EventBus: {len(strict_mode_exceptions)} listener(s) failed "
                    f"(phase={event.phase_name}, kind={event.kind}). "
                    f"First exception: {type(first_exc).__name__}: {first_exc}"
                )
                raise ValueError(error_msg) from first_exc

    @contextmanager
    def phase(
        self,
        phase_name: str,
        *,
        context: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Iterator[None]:
        """Emit ``pre``/``post`` events around the wrapped block.

        Deep-copies context and metadata to prevent mutations in one phase
        from affecting pre/post event consistency. This ensures events snapshot
        the state at emit time, not after caller modifications.
        """
        ctx = copy.deepcopy(dict(context or {}))
        meta = copy.deepcopy(dict(metadata or {}))
        self.emit(
            ScanPhaseEvent(
                phase_name=phase_name, kind="pre", context=ctx, metadata=meta
            )
        )
        try:
            yield
        finally:
            self.emit(
                ScanPhaseEvent(
                    phase_name=phase_name, kind="post", context=ctx, metadata=meta
                )
            )


__all__ = [
    "EventBus",
    "EventBusError",
    "EventListener",
    "PHASE_FEATURE_DETECTION",
    "PHASE_OUTPUT_RENDER",
    "PHASE_VARIABLE_DISCOVERY",
    "ScanPhaseEvent",
    "register_default_listener",
    "unregister_default_listener",
    "get_default_listeners",
    "clear_default_listeners",
]


# Ambient defaults are scoped to the current execution context so opt-in DI
# containers do not inherit listener state from unrelated threads.
_DEFAULT_LISTENERS: ContextVar[tuple[EventListener, ...]] = ContextVar(
    "prism_default_event_listeners",
    default=(),
)


def register_default_listener(listener: EventListener) -> None:
    """Register an ambient listener that opted-in EventBus instances inherit.

    Used by the CLI progress reporter and integration tests. Prefer passing
    ``event_listeners=`` directly, or ``inherit_default_event_listeners=True``
    when constructing :class:`~prism.scanner_core.di.DIContainer` if you want
    an explicit opt-in to the current default-listener snapshot.
    """
    if not callable(listener):
        raise TypeError("default listener must be callable")
    _DEFAULT_LISTENERS.set(get_default_listeners() + (listener,))


def unregister_default_listener(listener: EventListener) -> bool:
    """Unregister an ambient listener.

    Args:
        listener: The listener callable to unregister.

    Returns:
        True if listener was found and removed, False if listener was not registered.
    """
    listeners = list(get_default_listeners())
    try:
        listeners.remove(listener)
    except ValueError:
        return False
    _DEFAULT_LISTENERS.set(tuple(listeners))
    return True


def get_default_listeners() -> tuple[EventListener, ...]:
    return _DEFAULT_LISTENERS.get()


def clear_default_listeners() -> None:
    _DEFAULT_LISTENERS.set(())
