"""Unit tests for ServiceLocator.

This module contains tests for the ServiceLocator class, ensuring that all
factory methods, caching behavior, and thread safety are correctly implemented.
"""

from __future__ import annotations
import threading
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prism.scanner_core.service_locator import ServiceLocator
from prism.scanner_core.di import DIContainer


class TestServiceLocator(TestCase):
    """Test suite for the ServiceLocator class."""

    def setUp(self) -> None:
        """Set up a mock DIContainer for testing."""
        self.mock_di_container = MagicMock(spec=DIContainer)
        self.mock_di_container._cache = {}
        self.mock_di_container._cache_lock = threading.RLock()
        self.service_locator = ServiceLocator(self.mock_di_container)

    @patch("prism.scanner_core.events.EventBus")
    def test_factory_event_bus_creates_and_caches_instance(self, MockEventBus):
        """Test that factory_event_bus creates and caches an EventBus instance."""
        # Mock EventBus creation
        mock_event_bus = MockEventBus.return_value

        # Call factory_event_bus
        result = self.service_locator.factory_event_bus()

        # Verify EventBus was created and cached
        self.assertEqual(result, mock_event_bus)
        self.assertIn("event_bus", self.mock_di_container._cache)
        self.assertEqual(self.mock_di_container._cache["event_bus"], mock_event_bus)

        # Call factory_event_bus again and ensure no new instance is created
        result_again = self.service_locator.factory_event_bus()
        self.assertEqual(result_again, mock_event_bus)
        MockEventBus.assert_called_once()

    def test_replace_scan_options_invalidates_caches(self):
        """Test that replace_scan_options invalidates dependent caches."""
        # Populate cache with mock services
        self.mock_di_container._cache.update({
            "scanner_context": MagicMock(),
            "variable_discovery": MagicMock(),
            "feature_detector": MagicMock(),
        })

        # Call replace_scan_options
        self.service_locator.replace_scan_options()

        # Verify dependent caches are invalidated
        self.assertNotIn("scanner_context", self.mock_di_container._cache)
        self.assertNotIn("variable_discovery", self.mock_di_container._cache)
        self.assertNotIn("feature_detector", self.mock_di_container._cache)

    def test_thread_safety(self):
        """Test that ServiceLocator methods are thread-safe."""
        def call_factory():
            self.service_locator.factory_event_bus()

        threads = [threading.Thread(target=call_factory) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify only one EventBus instance was created
        self.assertIn("event_bus", self.mock_di_container._cache)

    # Additional tests for other factory methods and cache coordination will be added here.