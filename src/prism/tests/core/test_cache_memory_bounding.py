"""Tests for LRU cache memory bounding (Task 4.3).

Validates:
1. Memory usage tracking with sys.getsizeof
2. Entry-count eviction when maxsize exceeded
3. Memory-limit eviction when max_memory_bytes exceeded
4. Dual-limit enforcement (both limits respected)
5. Memory statistics exposure
"""

from prism.scanner_core.scan_cache import InMemoryLRUScanCache


class TestMemoryBoundingBasics:
    """Test memory bounding basics."""

    def test_cache_initializes_with_memory_limits(self) -> None:
        """Cache should accept both maxsize and max_memory_bytes parameters."""
        cache = InMemoryLRUScanCache(maxsize=10, max_memory_bytes=1024)
        assert cache._maxsize == 10
        assert cache._max_memory_bytes == 1024

    def test_memory_usage_tracked_on_set(self) -> None:
        """Cache should track memory usage when items are added."""
        cache = InMemoryLRUScanCache(maxsize=100, max_memory_bytes=10 * 1024 * 1024)
        cache.set("key1", "small_value")
        assert cache.total_memory_bytes > 0

    def test_entry_count_eviction_when_maxsize_exceeded(self) -> None:
        """Cache should evict oldest entry when maxsize is exceeded."""
        cache = InMemoryLRUScanCache(maxsize=2, max_memory_bytes=100 * 1024 * 1024)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # After adding 3rd item, oldest should be evicted
        assert len(cache) == 2
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None
        assert cache.evictions_by_count >= 1


class TestMemoryLimitEviction:
    """Test eviction triggered by memory limits."""

    def test_memory_limit_eviction_small_max_memory(self) -> None:
        """Cache should evict when total memory exceeds max_memory_bytes."""
        # Very small memory limit to force eviction
        cache = InMemoryLRUScanCache(maxsize=100, max_memory_bytes=500)
        cache.set("key1", "x" * 100)
        cache.set("key2", "y" * 100)
        cache.set("key3", "z" * 100)
        cache.set("key4", "w" * 100)

        # Some old entries should have been evicted due to memory pressure
        assert cache.total_memory_bytes <= cache._max_memory_bytes
        assert cache.evictions_by_memory > 0

    def test_memory_stats_exposed(self) -> None:
        """Cache should expose comprehensive memory statistics."""
        cache = InMemoryLRUScanCache(maxsize=5, max_memory_bytes=10 * 1024)
        cache.set("key1", "value1")

        stats = cache.memory_stats()
        assert "total_memory_bytes" in stats
        assert "max_memory_bytes" in stats
        assert "current_entries" in stats
        assert "max_entries" in stats
        assert "memory_utilization_percent" in stats
        assert "evictions_by_count" in stats
        assert "evictions_by_memory" in stats
        assert stats["max_memory_bytes"] == 10 * 1024
        assert stats["max_entries"] == 5


class TestDualLimitEnforcement:
    """Test enforcement of both count and memory limits together."""

    def test_both_limits_respected(self) -> None:
        """Cache should respect whichever limit is hit first."""
        cache = InMemoryLRUScanCache(maxsize=3, max_memory_bytes=2048)

        # Add entries up to count limit
        cache.set("k1", "x" * 50)
        cache.set("k2", "y" * 50)
        cache.set("k3", "z" * 50)

        # Fourth entry should trigger count-based eviction
        cache.set("k4", "w" * 50)
        assert len(cache) == 3

    def test_memory_stats_cleared_on_clear(self) -> None:
        """Cache should reset all memory stats on clear()."""
        cache = InMemoryLRUScanCache(maxsize=10, max_memory_bytes=10 * 1024)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.total_memory_bytes > 0

        cache.clear()
        assert cache.total_memory_bytes == 0
        assert len(cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0


class TestMemoryTrackingEdgeCases:
    """Test edge cases in memory tracking."""

    def test_zero_memory_limit_disables_caching(self) -> None:
        """Cache with maxsize=0 should disable caching."""
        cache = InMemoryLRUScanCache(maxsize=0, max_memory_bytes=100 * 1024 * 1024)
        cache.set("key1", "value1")
        assert len(cache) == 0
        assert cache.get("key1") is None

    def test_memory_updated_on_get_lru_reordering(self) -> None:
        """Memory tracking should be maintained correctly during LRU reordering on get()."""
        cache = InMemoryLRUScanCache(maxsize=10, max_memory_bytes=1024 * 1024)
        cache.set("key1", "value1")
        initial_memory = cache.total_memory_bytes

        # Get should move item to end (LRU reordering)
        result = cache.get("key1")
        assert result is not None
        assert cache.total_memory_bytes == initial_memory

    def test_invalidate_updates_memory_tracking(self) -> None:
        """Invalidating a key should update memory tracking."""
        cache = InMemoryLRUScanCache(maxsize=10, max_memory_bytes=1024 * 1024)
        cache.set("key1", "value" * 100)
        memory_before = cache.total_memory_bytes
        assert memory_before > 0

        cache.invalidate("key1")
        memory_after = cache.total_memory_bytes
        assert memory_after < memory_before
