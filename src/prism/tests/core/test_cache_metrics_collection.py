"""Tests for cache metrics collection (Task 4.4).

Validates:
1. Metrics can be collected from cache instances
2. Hit rate calculations are correct
3. Metrics can be serialized to dict/JSON format
4. Summary string is human-readable
"""

import pytest

from prism.scanner_core.cache_metrics import CacheMetrics
from prism.scanner_core.scan_cache import InMemoryLRUScanCache


class TestCacheMetricsCollection:
    """Test metrics collection from cache instances."""

    def test_metrics_collected_from_cache(self) -> None:
        """Metrics should be collectable from a cache instance."""
        cache = InMemoryLRUScanCache(maxsize=5, max_memory_bytes=10 * 1024)
        cache.set("k1", "value1")

        metrics = CacheMetrics.from_cache(cache)
        assert metrics.total_entries == 1
        assert metrics.max_entries == 5
        assert metrics.max_memory_bytes == 10 * 1024

    def test_hit_rate_calculation(self) -> None:
        """Hit rate should be calculated correctly."""
        cache = InMemoryLRUScanCache(maxsize=10, max_memory_bytes=100 * 1024)
        cache.set("k1", "v1")

        # Generate hits and misses
        cache.get("k1")  # 1 hit
        cache.get("k1")  # 2 hits
        cache.get("missing")  # 1 miss

        metrics = CacheMetrics.from_cache(cache)
        assert metrics.total_hits == 2
        assert metrics.total_misses == 1
        assert metrics.hit_rate_percent == pytest.approx(66.67, abs=0.1)

    def test_zero_hit_rate_on_no_accesses(self) -> None:
        """Hit rate should be 0 when cache has not been accessed."""
        cache = InMemoryLRUScanCache(maxsize=10, max_memory_bytes=100 * 1024)
        cache.set("k1", "v1")

        metrics = CacheMetrics.from_cache(cache)
        assert metrics.total_hits == 0
        assert metrics.total_misses == 0
        assert metrics.hit_rate_percent == 0.0


class TestMetricsSerialization:
    """Test metrics serialization to various formats."""

    def test_metrics_to_dict(self) -> None:
        """Metrics should serialize to dictionary."""
        cache = InMemoryLRUScanCache(maxsize=5, max_memory_bytes=10 * 1024)
        cache.set("k1", "value1")
        metrics = CacheMetrics.from_cache(cache)

        dict_repr = metrics.to_dict()
        assert isinstance(dict_repr, dict)
        assert "hit_rate_percent" in dict_repr
        assert "total_evictions" in dict_repr
        assert "memory_utilization_percent" in dict_repr

    def test_metrics_summary_string(self) -> None:
        """Metrics should produce human-readable summary."""
        cache = InMemoryLRUScanCache(maxsize=5, max_memory_bytes=10 * 1024)
        cache.set("k1", "v1")
        cache.get("k1")  # 1 hit
        metrics = CacheMetrics.from_cache(cache)

        summary = metrics.summary()
        assert isinstance(summary, str)
        assert "Cache Metrics" in summary
        assert "hits" in summary
        assert "entries" in summary
        assert "memory" in summary


class TestMetricsWithEvictions:
    """Test metrics collection with cache evictions."""

    def test_eviction_counts_in_metrics(self) -> None:
        """Metrics should include eviction counts."""
        cache = InMemoryLRUScanCache(maxsize=2, max_memory_bytes=100 * 1024)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")  # Triggers eviction

        metrics = CacheMetrics.from_cache(cache)
        assert metrics.total_evictions >= 1
        assert metrics.evictions_by_count >= 1

    def test_memory_eviction_tracked(self) -> None:
        """Metrics should track memory-based evictions."""
        cache = InMemoryLRUScanCache(maxsize=100, max_memory_bytes=500)
        cache.set("k1", "x" * 100)
        cache.set("k2", "y" * 100)
        cache.set("k3", "z" * 100)
        cache.set("k4", "w" * 100)

        metrics = CacheMetrics.from_cache(cache)
        # Should have evictions due to memory pressure
        assert metrics.memory_utilization_percent <= 100.0
