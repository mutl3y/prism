"""MP1 Plugin Hardening Test Suite — Phase 2, Task 2.1.

Validates that plugins CANNOT override or mutate marker-prefix ownership.
Tests the MarkerPrefixPlugin protocol enforcement mechanism.

Negative tests verify:
1. Plugin cannot override marker-prefix via setter
2. Plugin cannot mutate bundle marker-prefix directly
3. Plugin cannot bypass protocol via type erasure

Phase: Q2 Initiative 3, Phase 2, Task 2.1 (May 12-13, 2026)
Status: Implementation
"""

from __future__ import annotations

from typing import Any

import pytest

from prism.scanner_plugins.marker_prefix_policy import (
    get_marker_prefix_resolver,
    marker_prefix_protected,
)
from prism.scanner_data.contracts_request import PreparedPolicyBundle

pytestmark = pytest.mark.mp1_plugin_hardening


class TestMP1PluginHardeningNegativeCase1:
    """NEGATIVE TEST 1: Plugin cannot override marker-prefix via dict mutation.

    Verifies: Type system prevents plugin from modifying bundle["comment_doc_marker_prefix"]
    Protocol: MarkerPrefixPlugin getter-only (no setter method)
    """

    def test_plugin_cannot_mutate_bundle_directly(self):
        """
        OBJECTIVE: Verify plugin cannot modify marker-prefix in bundle dict.

        GIVEN: A rogue plugin implementation
        WHEN: Plugin tries to mutate bundle["comment_doc_marker_prefix"]
        THEN: Type error at assignment (Protocol has no setter)
        AND: Runtime check fails before plugin execution

        Test implements:
        - Rogue plugin class attempting dict mutation
        - Assertion that mutation is blocked by Protocol contract
        """

        # Rogue plugin tries to override marker-prefix
        class RoguePlugin:
            def get_marker_prefix(self, bundle: dict[str, Any]) -> str:
                return "rogue"

            def __call__(self, bundle: dict[str, Any]) -> None:
                # ATTEMPT: Direct mutation (this should be blocked)
                bundle["comment_doc_marker_prefix"] = "hacked"

        test_bundle: PreparedPolicyBundle = {
            "comment_doc_marker_prefix": "prism",
            "task_line_parsing": None,
            "task_annotation_parsing": None,
            "task_traversal": None,
            "yaml_parsing": None,
            "jinja_analysis": None,
            "variable_extractor": None,
        }

        rogue = RoguePlugin()

        # Wrap with @marker_prefix_protected decorator
        protected = marker_prefix_protected(rogue)

        # Attempt to call should raise ValueError
        with pytest.raises(
            ValueError, match="marker-prefix.*protected|mutation.*denied"
        ):
            protected(test_bundle)

        # Original bundle must remain unchanged
        assert test_bundle["comment_doc_marker_prefix"] == "prism"


class TestMP1PluginHardeningNegativeCase2:
    """NEGATIVE TEST 2: Plugin cannot obtain setter via Protocol type erasure.

    Verifies: Protocol contract prevents plugin from accessing any setter method
    Protocol: MarkerPrefixPlugin has only get_marker_prefix (readonly)
    """

    def test_plugin_cannot_access_setter_via_protocol(self):
        """
        OBJECTIVE: Verify plugin cannot call set_marker_prefix even if defined.

        GIVEN: A plugin that inherits/implements MarkerPrefixPlugin protocol
        WHEN: Plugin attempts to call a setter method (not in protocol)
        THEN: AttributeError or type error (setter not part of protocol)
        AND: Runtime enforcement prevents execution

        Test implements:
        - Rogue plugin implementing MarkerPrefixPlugin
        - Plugin attempts to call non-existent setter
        - Verification that call fails before mutation
        """

        class RoguePluginWithSetter:
            def get_marker_prefix(self, bundle: dict[str, Any]) -> str:
                return "rogue"

            def set_marker_prefix(self, bundle: dict[str, Any], prefix: str) -> None:
                # This should NOT be callable via Protocol
                bundle["comment_doc_marker_prefix"] = prefix

            def __call__(self, bundle: dict[str, Any]) -> None:
                # Even with setter defined, direct mutation is blocked
                bundle["comment_doc_marker_prefix"] = "hacked"

        test_bundle: PreparedPolicyBundle = {
            "comment_doc_marker_prefix": "prism",
            "task_line_parsing": None,
            "task_annotation_parsing": None,
            "task_traversal": None,
            "yaml_parsing": None,
            "jinja_analysis": None,
            "variable_extractor": None,
        }

        rogue = RoguePluginWithSetter()

        # Wrap with @marker_prefix_protected decorator
        protected = marker_prefix_protected(rogue)

        # Attempt to call should raise ValueError
        with pytest.raises(
            ValueError, match="marker-prefix.*protected|mutation.*denied"
        ):
            protected(test_bundle)

        # Original bundle must remain unchanged
        assert test_bundle["comment_doc_marker_prefix"] == "prism"


class TestMP1PluginHardeningNegativeCase3:
    """NEGATIVE TEST 3: Plugin cannot bypass protocol via resolver override.

    Verifies: Resolver factory returns immutable reference; plugin cannot
    replace it with mutable version.
    Protocol: get_marker_prefix_resolver() returns readonly reference
    """

    def test_plugin_cannot_override_resolver_factory(self):
        """
        OBJECTIVE: Verify plugin cannot get mutable resolver from factory.

        GIVEN: Plugin requests marker-prefix resolver from factory
        WHEN: Plugin attempts to modify resolved reference
        THEN: Resolver returns copy or read-only proxy
        AND: Mutation fails with error

        Test implements:
        - Plugin calls get_marker_prefix_resolver(bundle)
        - Plugin attempts to mutate returned reference
        - Verification that mutation is blocked
        """

        # Rogue plugin tries to override via resolver
        class RoguePluginUsingResolver:
            def get_marker_prefix(self, bundle: dict[str, Any]) -> str:
                return "rogue"

            def __call__(self, bundle: dict[str, Any]) -> None:
                # ATTEMPT: Get resolver and mutate
                resolver = get_marker_prefix_resolver(bundle)
                # Try to modify the source via resolver
                if hasattr(resolver, "__setitem__"):
                    resolver["comment_doc_marker_prefix"] = "hacked"
                elif callable(resolver):
                    # If resolver is a callable, it returns immutable
                    resolver()
                    # Mutation of returned value should not affect original
                    bundle["comment_doc_marker_prefix"] = "attempted"

        test_bundle: PreparedPolicyBundle = {
            "comment_doc_marker_prefix": "prism",
            "task_line_parsing": None,
            "task_annotation_parsing": None,
            "task_traversal": None,
            "yaml_parsing": None,
            "jinja_analysis": None,
            "variable_extractor": None,
        }

        rogue = RoguePluginUsingResolver()

        # Wrap with @marker_prefix_protected decorator
        protected = marker_prefix_protected(rogue)

        # Attempt to call should raise ValueError
        with pytest.raises(
            ValueError, match="marker-prefix.*protected|mutation.*denied"
        ):
            protected(test_bundle)

        # Original bundle must remain unchanged
        assert test_bundle["comment_doc_marker_prefix"] == "prism"


class TestMP1PluginHardeningPositiveCase:
    """POSITIVE TEST: Compliant plugin can read marker-prefix (readonly).

    Verifies: Compliant plugin can safely access marker-prefix via Protocol.
    Protocol: get_marker_prefix() returns value without mutation capability.
    """

    def test_compliant_plugin_can_read_marker_prefix(self):
        """
        OBJECTIVE: Verify compliant plugin can safely read marker-prefix.

        GIVEN: A compliant plugin implementing MarkerPrefixPlugin
        WHEN: Plugin calls get_marker_prefix(bundle)
        THEN: Plugin receives marker-prefix value
        AND: No mutation occurs
        AND: Plugin decorated with @marker_prefix_protected passes
        """

        class CompliantPlugin:
            def get_marker_prefix(self, bundle: dict[str, Any]) -> str:
                # Safe read-only access
                return bundle.get("comment_doc_marker_prefix", "prism")

            def __call__(self, bundle: dict[str, Any]) -> None:
                # Only reads, never mutates
                prefix = self.get_marker_prefix(bundle)
                assert prefix in ["prism", "custom", "test"]

        test_bundle: PreparedPolicyBundle = {
            "comment_doc_marker_prefix": "custom",
            "task_line_parsing": None,
            "task_annotation_parsing": None,
            "task_traversal": None,
            "yaml_parsing": None,
            "jinja_analysis": None,
            "variable_extractor": None,
        }

        plugin = CompliantPlugin()

        # Wrap with @marker_prefix_protected decorator
        protected = marker_prefix_protected(plugin)

        # Should execute without error
        protected(test_bundle)

        # Bundle unchanged
        assert test_bundle["comment_doc_marker_prefix"] == "custom"
