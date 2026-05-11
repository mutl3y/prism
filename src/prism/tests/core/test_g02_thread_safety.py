"""Thread-safety tests for DIContainer and EventBus (G-02)."""

import threading

from prism.scanner_core.di import DIContainer
from prism.scanner_core.events import EventBus, ScanPhaseEvent


def test_di_container_concurrent_factory_calls_no_duplicates():
    """Concurrent factory_variable_row_builder calls must return the same cached instance."""
    container = DIContainer(role_path="/tmp/fake_role", scan_options={})

    results = []
    errors = []

    def worker():
        try:
            results.append(container.factory_variable_row_builder())
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 10
    assert (
        len(set(id(r) for r in results)) == 1
    ), "All threads must get the same cached instance"


def test_eventbus_concurrent_subscribe_emit_no_crash():
    """Concurrent subscribe/emit/unsubscribe must not raise."""
    bus = EventBus()
    errors = []

    def subscriber(event):
        pass

    def emitter():
        for _ in range(50):
            try:
                bus.emit(ScanPhaseEvent(phase_name="test", kind="pre"))
            except Exception as e:
                errors.append(e)

    def subscriber_thread():
        for _ in range(50):
            try:
                bus.subscribe(subscriber)
                bus.unsubscribe(subscriber)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=emitter)] + [
        threading.Thread(target=subscriber_thread) for _ in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"
