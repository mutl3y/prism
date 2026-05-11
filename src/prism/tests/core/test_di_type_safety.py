"""Type-safety tests for DI factory overloads (Phase 1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prism.scanner_core.di import DIContainer
from prism.scanner_data.contracts_request import ScanOptionsDict

if TYPE_CHECKING:
    from prism.scanner_core.events import EventBus
    from prism.scanner_data.builders import VariableRowBuilder


def test_factory_event_bus_type_inference() -> None:
    """Test that factory_event_bus returns properly typed EventBus."""
    scan_opts: ScanOptionsDict = {"platform": "ansible"}
    di = DIContainer(role_path="test", scan_options=scan_opts)

    # Type should be inferred as EventBus, not object
    bus: EventBus = di.factory_event_bus()
    assert bus is not None
    # EventBus has subscribe method (type check at static analysis time)
    assert callable(bus.subscribe)


def test_factory_variable_row_builder_type_inference() -> None:
    """Test that factory_variable_row_builder returns properly typed VariableRowBuilder."""
    scan_opts: ScanOptionsDict = {"platform": "ansible"}
    di = DIContainer(role_path="test", scan_options=scan_opts)

    # Type should be inferred as VariableRowBuilder, not object
    builder: VariableRowBuilder = di.factory_variable_row_builder()
    assert builder is not None


def test_factory_plugin_types_not_erased() -> None:
    """Test that plugin factory types are not erased to object."""
    # This test verifies that the overload signatures prevent type erasure
    # Mypy will catch type errors here if overloads are not working

    scan_opts: ScanOptionsDict = {"platform": "ansible"}
    di = DIContainer(role_path="test", scan_options=scan_opts)

    # These should not be typed as object|None implicitly
    # The overload signatures should preserve the explicit Optional types
    comment_plugin = di.factory_comment_driven_doc_plugin()
    assert comment_plugin is None or hasattr(comment_plugin, "__call__")
