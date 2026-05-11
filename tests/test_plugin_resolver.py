"""Unit tests for PluginResolver class."""

import pytest
from unittest.mock import Mock
from prism.scanner_core.plugin_resolver import PluginResolver
from prism.scanner_core.di import DIContainer
from prism.scanner_plugins.registry import PluginRegistry


@pytest.fixture
def mock_di_container():
    """Fixture for creating a mock DIContainer."""
    di = Mock(spec=DIContainer)
    di.plugin_registry = Mock(spec=PluginRegistry)
    di.platform_key = "test_platform"
    return di


def test_factory_variable_discovery_plugin(mock_di_container):
    """Test variable discovery plugin resolution."""
    resolver = PluginResolver(mock_di_container)
    mock_di_container.plugin_registry.get_variable_discovery_plugin.return_value = Mock()

    plugin = resolver.factory_variable_discovery_plugin()

    assert plugin is not None
    mock_di_container.plugin_registry.get_variable_discovery_plugin.assert_called_once_with(
        "test_platform"
    )


def test_factory_feature_detection_plugin(mock_di_container):
    """Test feature detection plugin resolution."""
    resolver = PluginResolver(mock_di_container)
    mock_di_container.plugin_registry.get_feature_detection_plugin.return_value = Mock()

    plugin = resolver.factory_feature_detection_plugin()

    assert plugin is not None
    mock_di_container.plugin_registry.get_feature_detection_plugin.assert_called_once_with(
        "test_platform"
    )


def test_factory_comment_driven_doc_plugin(mock_di_container):
    """Test optional comment-driven documentation plugin resolution."""
    resolver = PluginResolver(mock_di_container)

    plugin = resolver.factory_comment_driven_doc_plugin()

    assert plugin is None


def test_thread_safety(mock_di_container):
    """Test thread safety of PluginResolver methods."""
    import threading

    resolver = PluginResolver(mock_di_container)
    mock_di_container.plugin_registry.get_variable_discovery_plugin.return_value = Mock()

    def resolve_plugin():
        resolver.factory_variable_discovery_plugin()

    threads = [threading.Thread(target=resolve_plugin) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    mock_di_container.plugin_registry.get_variable_discovery_plugin.assert_called_with(
        "test_platform"
    )
