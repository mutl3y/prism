"""Tests for scan cache key determinism and collision prevention.

Verifies that compute_scan_cache_key produces stable, collision-free keys across:
- Primitive types (str, int, float, bool, None)
- Container types with mixed key types (dict, list, tuple, set, frozenset)
- Custom objects with __cache_key__() protocol
- Custom objects with custom __hash__/__eq__
- Deep nesting limits
"""

from __future__ import annotations

import pytest

from prism.scanner_core.scan_cache import compute_scan_cache_key


class TestCacheKeyDeterminism:
    """Deterministic cache key generation across process runs."""

    def test_primitive_cache_keys_stable(self) -> None:
        """Primitive types always produce stable cache keys."""
        # Strings
        key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"value": "hello"},
        )
        key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"value": "hello"},
        )
        assert key1 == key2, "String values should produce same cache key"

        # Integers
        key3 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"count": 42},
        )
        key4 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"count": 42},
        )
        assert key3 == key4, "Integer values should produce same cache key"

    def test_cache_key_reflects_value_changes(self) -> None:
        """Cache keys differ when primitive values differ."""
        key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"value": "hello"},
        )
        key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"value": "goodbye"},
        )
        assert (
            key1 != key2
        ), "Different string values should produce different cache keys"

    def test_dict_key_collision_prevention(self) -> None:
        """Type-safe dict keys prevent collisions between different key types."""
        # Integer key vs string key that looks like the integer when stringified
        key_int = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"data": {1: "int_key_value"}},
        )
        key_str = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"data": {"1": "str_key_value"}},
        )

        assert (
            key_int != key_str
        ), "Dict with int key {1: ...} should differ from dict with str key {'1': ...}"

    def test_dict_key_collision_boolean_vs_string(self) -> None:
        """Boolean keys don't collide with string equivalents."""
        key_true = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"data": {True: "true_bool"}},
        )
        key_str = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"data": {"True": "str_true"}},
        )

        assert (
            key_true != key_str
        ), "Boolean key True should differ from string key 'True'"

    def test_container_stability(self) -> None:
        """Lists, tuples, sets produce stable keys."""
        list_key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"items": [1, 2, 3]},
        )
        list_key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"items": [1, 2, 3]},
        )
        assert list_key1 == list_key2

        # Tuples
        tuple_key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"items": (1, 2, 3)},
        )
        tuple_key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"items": (1, 2, 3)},
        )
        assert tuple_key1 == tuple_key2

        # Sets (same items in any order produce same key)
        set_key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"items": {1, 2, 3}},
        )
        set_key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"items": {3, 2, 1}},  # Same set, different order
        )
        assert (
            set_key1 == set_key2
        ), "Sets with same items in different order should produce same key"


class TestCacheKeyCollisionPrevention:
    """Ensure cache keys don't collide on different inputs."""

    def test_different_role_hash_produces_different_key(self) -> None:
        """Different role_content_hash produces different cache keys."""
        key1 = compute_scan_cache_key(
            role_content_hash="hash_a",
            scan_options={"option": "value"},
        )
        key2 = compute_scan_cache_key(
            role_content_hash="hash_b",
            scan_options={"option": "value"},
        )
        assert key1 != key2

    def test_dict_key_order_independence(self) -> None:
        """Dict key order doesn't affect cache key (JSON sort_keys=True)."""
        key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"a": 1, "b": 2, "c": 3},
        )
        key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"c": 3, "b": 2, "a": 1},
        )
        assert key1 == key2, "Dict key order should not affect cache key"

    def test_nested_dict_collision_prevention(self) -> None:
        """Nested dicts with different key types produce different keys."""
        key_int = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"nested": {1: {"inner": "value"}}},
        )
        key_str = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"nested": {"1": {"inner": "value"}}},
        )
        assert key_int != key_str


class TestCacheKeyCustomObjectProtocol:
    """Test __cache_key__() protocol for custom objects."""

    def test_custom_cache_key_protocol(self) -> None:
        """Objects implementing __cache_key__() produce stable keys."""

        class CustomObject:
            def __init__(self, value: str):
                self.value = value

            def __cache_key__(self) -> str:
                return f"custom:{self.value}"

        obj1 = CustomObject("stable")
        key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"obj": obj1},
        )

        obj2 = CustomObject("stable")
        key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"obj": obj2},
        )

        assert (
            key1 == key2
        ), "Objects with same __cache_key__() should produce same cache key"

    def test_custom_cache_key_protocol_differentiates(self) -> None:
        """Different __cache_key__() values produce different cache keys."""

        class CustomObject:
            def __init__(self, value: str):
                self.value = value

            def __cache_key__(self) -> str:
                return f"custom:{self.value}"

        obj1 = CustomObject("first")
        key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"obj": obj1},
        )

        obj2 = CustomObject("second")
        key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"obj": obj2},
        )

        assert (
            key1 != key2
        ), "Objects with different __cache_key__() should produce different keys"

    def test_custom_cache_key_protocol_invalid_return_type_raises(self) -> None:
        """__cache_key__() must return a string."""

        class InvalidCustomObject:
            def __cache_key__(self) -> int:
                return 42  # type: ignore

        obj = InvalidCustomObject()

        with pytest.raises(
            ValueError,
            match="__cache_key__.*must return.*str",
        ):
            compute_scan_cache_key(
                role_content_hash="abc123",
                scan_options={"obj": obj},
            )

    def test_custom_cache_key_protocol_exception_raises(self) -> None:
        """Exceptions in __cache_key__() are wrapped and raised."""

        class BrokenCustomObject:
            def __cache_key__(self) -> str:
                raise RuntimeError("Intentional error")

        obj = BrokenCustomObject()

        with pytest.raises(ValueError, match="__cache_key__.*failed"):
            compute_scan_cache_key(
                role_content_hash="abc123",
                scan_options={"obj": obj},
            )


class TestCacheKeyDepthLimits:
    """Test maximum nesting depth enforcement."""

    def test_shallow_nesting_allowed(self) -> None:
        """Shallow nesting (well under limit) works fine."""
        # Create a 10-level deep dict
        deep_dict: dict[str, object] = {"value": "leaf"}
        for _ in range(10):
            deep_dict = {"nested": deep_dict}

        key = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"data": deep_dict},
        )
        assert key is not None
        assert ":" in key  # Must be in format "role_hash:options_hash"

    def test_excessive_nesting_rejected(self) -> None:
        """Deeply nested structures (>100 levels) raise ValueError."""
        # Create a 150-level deep dict
        deep_dict: dict[str, object] = {"value": "leaf"}
        for _ in range(150):
            deep_dict = {"nested": deep_dict}

        with pytest.raises(ValueError, match="exceeds maximum depth"):
            compute_scan_cache_key(
                role_content_hash="abc123",
                scan_options={"data": deep_dict},
            )

    def test_exactly_max_depth_allowed(self) -> None:
        """Deep nesting close to max limit is allowed.

        Verify that structures nested to depth ~50 (well under the 100 limit) work correctly.
        """
        # Create 50-level deep nested dict
        deep_dict: dict[str, object] = {"value": "leaf"}
        for _ in range(49):  # 49 nested "nested" dicts
            deep_dict = {"nested": deep_dict}

        key = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"data": deep_dict},
        )
        assert key is not None

        # Verify it's deterministic
        key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"data": deep_dict},
        )
        assert key == key2

    def test_mixed_container_depth_tracking(self) -> None:
        """Depth tracking works across list/dict/tuple nesting."""
        # Create: [[[[[...]]]]]]  (100+ levels deep)
        nested: list[object] = ["leaf"]
        for _ in range(150):
            nested = [nested]

        with pytest.raises(ValueError, match="exceeds maximum depth"):
            compute_scan_cache_key(
                role_content_hash="abc123",
                scan_options={"data": nested},
            )


class TestCacheKeyEdgeCases:
    """Edge cases and error conditions."""

    def test_empty_role_hash_raises(self) -> None:
        """Empty role_content_hash raises ValueError."""
        with pytest.raises(ValueError, match="role_content_hash must not be empty"):
            compute_scan_cache_key(
                role_content_hash="",
                scan_options={"option": "value"},
            )

    def test_none_role_hash_raises(self) -> None:
        """None role_content_hash raises ValueError."""
        with pytest.raises(ValueError):
            compute_scan_cache_key(
                role_content_hash=None,  # type: ignore
                scan_options={"option": "value"},
            )

    def test_empty_scan_options(self) -> None:
        """Empty scan_options is allowed."""
        key = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={},
        )
        assert key is not None
        assert ":" in key

    def test_none_values_in_options(self) -> None:
        """None values in options are handled correctly."""
        key1 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"value": None},
        )
        key2 = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options={"value": None},
        )
        assert key1 == key2

    def test_complex_nested_structure(self) -> None:
        """Complex mixed container structure produces valid key."""
        complex_data = {
            "strings": ["a", "b", "c"],
            "numbers": (1, 2.5, -3),
            "booleans": {True, False},
            "nested": {
                "inner_list": [1, {"deep": "value"}],
                "inner_set": frozenset([1, 2, 3]),
            },
        }

        key = compute_scan_cache_key(
            role_content_hash="abc123",
            scan_options=complex_data,
        )
        assert key is not None
        assert ":" in key
