import pytest
from unittest.mock import MagicMock
from prism.scanner_core.di import DIContainer
from prism.scanner_core.plugin_resolver import PluginResolver
from prism.scanner_core.service_locator import ServiceLocator

def test_plugin_resolver_delegation():
    """Test that DIContainer delegates plugin resolution to PluginResolver."""
    mock_resolver = MagicMock(spec=PluginResolver)
    di = DIContainer("role_path", {}, registry=None)
    di._plugin_resolver = mock_resolver

    di.factory_variable_discovery_plugin()
    mock_resolver.factory_variable_discovery_plugin.assert_called_once()

def test_service_locator_delegation():
    """Test that DIContainer delegates service factories to ServiceLocator."""
    mock_locator = MagicMock(spec=ServiceLocator)
    di = DIContainer("role_path", {}, registry=None)
    di._service_locator = mock_locator

    di.factory_event_bus()
    mock_locator.factory_event_bus.assert_called_once()

def test_backward_compatibility():
    """Test that DIContainer retains backward compatibility."""
    scan_options = {
        "scan_pipeline_plugin": "test_plugin",
        "policy_context": {
            "selection": {"plugin": "test_plugin"}
        },
        "platform": "test_platform",
    }
    mock_registry = MagicMock()
    mock_registry.get_variable_discovery_plugin.return_value = MagicMock()
    di = DIContainer("role_path", scan_options, registry=mock_registry)
    assert di.factory_event_bus() is not None
    assert di.factory_variable_discovery_plugin() is not None